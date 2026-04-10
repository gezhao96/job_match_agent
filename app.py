from __future__ import annotations

import argparse
from pathlib import Path

from agent.schemas import JobWithMatch
from core.llm_factory import build_llm
from core.profile_parser import UserProfileParser
from core.utils import dump_json, read_text
from tools.crawler import CrawlConfig, JobCrawler
from tools.extractor import JobExtractor
from tools.matcher import JobMatcher
from tools.reporter import ReportBuilder


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = OUTPUT_DIR / "reports"


def collect_user_input(args: argparse.Namespace) -> str:
    if args.input_file:
        return read_text(args.input_file)
    if args.input_text:
        return args.input_text

    print("请输入自然语言请求，输入完成后按 Ctrl+D (Linux/macOS) 或 Ctrl+Z 回车 (Windows)：")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="求职信息匹配 LangChain 初版")
    parser.add_argument("--input-file", type=str, default="", help="自然语言输入文件路径")
    parser.add_argument("--input-text", type=str, default="", help="直接传入自然语言输入")
    parser.add_argument("--max-jobs", type=int, default=10, help="最多分析岗位数")
    parser.add_argument("--max-pages", type=int, default=3, help="最多抓取列表页数")
    args = parser.parse_args()

    user_input = collect_user_input(args)
    if not user_input.strip():
        raise ValueError("未接收到有效输入。")

    llm = build_llm(temperature=0.0)
    profile_parser = UserProfileParser(llm)
    extractor = JobExtractor(llm)
    matcher = JobMatcher(llm)

    print("[1/5] 正在解析用户画像...")
    profile = profile_parser.parse(user_input)
    profile.max_jobs = args.max_jobs or profile.max_jobs
    profile.max_pages = args.max_pages or profile.max_pages
    dump_json(profile.model_dump(mode="json"), OUTPUT_DIR / "user_profile.json")

    print("[2/5] 正在抓取招聘信息...")
    crawler = JobCrawler(CrawlConfig(max_jobs=profile.max_jobs, max_pages=profile.max_pages))
    crawled_items = crawler.crawl(profile.url)
    dump_json([item.model_dump(mode="json") for item in crawled_items], OUTPUT_DIR / "crawled_jobs.json")

    print(f"    已抓取 {len(crawled_items)} 条详情页内容")

    print("[3/5] 正在提取岗位结构化信息...")
    extracted_infos = []
    structured = []
    for idx, item in enumerate(crawled_items, start=1):
        print(f"    提取 {idx}/{len(crawled_items)}: {item.title[:60]}")
        info = extractor.extract(item.title, item.content)
        extracted_infos.append(info)
        structured.append(
            {
                "title": item.title,
                "source_url": item.source_url,
                "publish_date": item.publish_date,
                "job_info": info.model_dump(mode="json"),
            }
        )
    dump_json(structured, OUTPUT_DIR / "structured_jobs.json")

    print("[4/5] 正在进行岗位匹配评分...")
    matched_items: list[JobWithMatch] = []
    for idx, (item, info) in enumerate(zip(crawled_items, extracted_infos), start=1):
        if not info.is_recruitment_related:
            continue
        match = matcher.match(profile, info)
        matched_items.append(
            JobWithMatch(
                title=item.title,
                source_url=item.source_url,
                publish_date=item.publish_date,
                extracted=info,
                match=match,
            )
        )
        print(f"    匹配 {idx}/{len(crawled_items)}: score={match.match_score} | {item.title[:50]}")

    dump_json([item.model_dump(mode="json") for item in matched_items], OUTPUT_DIR / "match_results.json")

    print("[5/5] 正在生成报告...")
    markdown = ReportBuilder.build_markdown(profile, matched_items)
    report_path = REPORT_DIR / "latest_report.md"
    ReportBuilder.save_markdown(markdown, report_path)

    print("\n处理完成。输出文件：")
    print(f"- {OUTPUT_DIR / 'user_profile.json'}")
    print(f"- {OUTPUT_DIR / 'crawled_jobs.json'}")
    print(f"- {OUTPUT_DIR / 'structured_jobs.json'}")
    print(f"- {OUTPUT_DIR / 'match_results.json'}")
    print(f"- {report_path}")

    print("\n报告预览：\n")
    print(markdown[:3000])


if __name__ == "__main__":
    main()
