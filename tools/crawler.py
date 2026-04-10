from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from agent.schemas import CrawlItem


JOB_TITLE_PATTERNS = [
    # 用于快速判断链接标题是否可能是招聘信息。
    r"招聘", r"校招", r"春招", r"秋招", r"岗位", r"职位", r"工程师", r"研究员",
    r"研究院", r"研究所", r"博士", r"博后", r"实习", r"引才", r"简章", r"双选会"
]


@dataclass
class CrawlConfig:
    """爬虫运行参数。

    timeout: 单次 HTTP 请求超时时间（秒）。
    max_pages: 最多抓取的列表页数量。
    max_jobs: 最多返回的岗位条目数量。
    user_agent: 请求头中的浏览器标识，降低被简单反爬拦截的概率。
    """

    timeout: int = 20
    max_pages: int = 3
    max_jobs: int = 10
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )


class JobCrawler:
    """岗位爬虫。

    支持两种入口：
    1) 列表页：提取详情链接后逐条抓取。
    2) 详情页：直接清洗正文并结构化输出。

    采用“标题关键词 + URL 规则”做启发式过滤，优先保证通用性与可用性。
    """

    def __init__(self, config: CrawlConfig | None = None) -> None:
        self.config = config or CrawlConfig()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

    def fetch_html(self, url: str) -> str:
        """下载页面 HTML，并尽量使用站点真实编码进行解码。"""

        resp = self.session.get(url, timeout=self.config.timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text

    @staticmethod
    def clean_text(html: str) -> str:
        """清洗 HTML，提取可读纯文本。

        会移除 script/style/noscript 等噪声标签，
        并把连续空行压缩为单行，便于后续提取。
        """

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()

    @staticmethod
    def extract_date(text: str) -> str | None:
        """从文本中提取日期并标准化为 YYYY-MM-DD。

        支持形如 2026-4-9、2026/4/9、2026年4月9日 的格式。
        若解析失败则返回 None。
        """

        m = re.search(r"(20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2})", text)
        if not m:
            return None
        raw = m.group(1)
        raw = raw.replace("年", "-").replace("月", "-").replace("日", "")
        raw = raw.replace("/", "-").replace(".", "-")
        parts = raw.split("-")
        if len(parts) >= 3:
            y, mo, d = parts[:3]
            try:
                return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            except ValueError:
                return None
        return None

    @staticmethod
    def looks_like_list_page(url: str, html: str) -> bool:
        """启发式判断页面是否为招聘列表页。"""

        # 许多高校/单位站点列表页都使用 index.htm/index_2.htm 命名。
        if re.search(r"/index(_\d+)?\.htm?$", url):
            return True
        # 文本中招聘关键词足够多，且链接数量较多时，通常是列表聚合页。
        title_count = len(re.findall(r"招聘|岗位|校招|春招|秋招", html))
        link_count = len(re.findall(r"<a\s+[^>]*href=", html, flags=re.I))
        return title_count >= 5 and link_count >= 10

    @staticmethod
    def is_detail_url(url: str) -> bool:
        """判断 URL 是否像岗位详情页，并过滤明显无效链接。"""

        if re.search(r"/index(_\d+)?\.htm?$", url):
            return False
        if url.startswith("javascript:"):
            return False
        if "/download/" in url:
            return False
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            return False
        return url.endswith(".htm") or url.endswith(".html") or "/info/" in url

    @staticmethod
    def title_match(title: str) -> bool:
        """判断标题是否命中岗位关键词。"""

        return any(re.search(p, title, flags=re.I) for p in JOB_TITLE_PATTERNS)

    @staticmethod
    def make_page_url(base_url: str, page: int) -> str:
        """按常见规则生成分页 URL，例如 index.htm -> index_2.htm。"""

        if page <= 1:
            return base_url
        if re.search(r"index\.htm?$", base_url):
            return re.sub(r"index\.htm?$", f"index_{page}.htm", base_url)
        return base_url

    @staticmethod
    def extract_max_page(html: str) -> int:
        """从 HTML 中推断最大分页号；推断失败时返回 1。"""

        nums = [int(x) for x in re.findall(r"index_(\d+)\.htm", html)]
        return max(nums) if nums else 1

    def extract_job_links(self, list_url: str, html: str) -> list[tuple[str, str, str | None]]:
        """从列表页提取候选岗位详情链接。

        返回三元组列表：(详情页 URL, 标题, 可能的发布日期)。
        发布日期优先从链接所在行文本中提取。
        """

        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        out: list[tuple[str, str, str | None]] = []

        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            title = a.get_text(" ", strip=True)
            if not href or not title:
                continue
            abs_url = urljoin(list_url, href)
            if abs_url in seen:
                continue
            # 双重筛选：标题像岗位 + URL 像详情页。
            if not self.title_match(title):
                continue
            if not self.is_detail_url(abs_url):
                continue
            seen.add(abs_url)
            # 某些站点日期放在同一行/同一父节点中，这里做一次就近提取。
            row_text = a.parent.get_text(" ", strip=True) if a.parent else title
            publish_date = self.extract_date(row_text)
            out.append((abs_url, title, publish_date))
        return out

    def crawl_detail(self, url: str, title: str = "", publish_date: str | None = None, list_page: int | None = None) -> CrawlItem:
        """抓取单个详情页并组装 CrawlItem。"""

        html = self.fetch_html(url)
        text = self.clean_text(html)
        if not title:
            soup = BeautifulSoup(html, "lxml")
            # 优先使用 <title>，兜底取正文首行。
            title = (soup.title.get_text(strip=True) if soup.title else "") or text.split("\n", 1)[0][:120]
        if not publish_date:
            publish_date = self.extract_date(text)
        return CrawlItem(
            title=title,
            source_url=url,
            page_type="detail_page",
            publish_date=publish_date,
            content=text,
            list_page=list_page,
        )

    def crawl(self, url: str) -> list[CrawlItem]:
        """爬取入口。

        若传入的是列表页，则分页提取详情并逐条抓取；
        若传入的是详情页，则直接返回单条结果。
        """

        first_html = self.fetch_html(url)

        # 非列表页直接当详情页处理。
        if not self.looks_like_list_page(url, first_html):
            return [self.crawl_detail(url)]

        total_pages = min(self.extract_max_page(first_html), self.config.max_pages)
        if total_pages <= 0:
            total_pages = 1

        items: list[CrawlItem] = []
        seen_urls: set[str] = set()

        for page in range(1, total_pages + 1):
            page_url = self.make_page_url(url, page)
            # 第 1 页复用已抓取内容，避免重复请求。
            html = first_html if page == 1 else self.fetch_html(page_url)
            links = self.extract_job_links(page_url, html)

            for detail_url, title, publish_date in links:
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                try:
                    item = self.crawl_detail(
                        detail_url,
                        title=title,
                        publish_date=publish_date,
                        list_page=page,
                    )
                    items.append(item)
                except Exception as exc:
                    # 单条失败不影响整体流程，记录失败信息供后续排查。
                    items.append(
                        CrawlItem(
                            title=title,
                            source_url=detail_url,
                            page_type="detail_page",
                            publish_date=publish_date,
                            content=f"抓取失败：{exc}",
                            list_page=page,
                        )
                    )
                # 达到上限后立即返回，避免不必要请求。
                if len(items) >= self.config.max_jobs:
                    return items
        return items
