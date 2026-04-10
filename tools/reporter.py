from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from agent.schemas import JobWithMatch, UserProfile


class ReportBuilder:
    @staticmethod
    def build_markdown(profile: UserProfile, jobs: list[JobWithMatch]) -> str:
        sorted_jobs = sorted(jobs, key=lambda x: x.match.match_score, reverse=True)
        counts = Counter(j.match.recommendation for j in sorted_jobs)

        lines: list[str] = []
        lines.append("# 求职岗位匹配报告")
        lines.append("")
        lines.append("## 用户画像")
        lines.append(f"- 招聘网址：{profile.url}")
        lines.append(f"- 求职方向：{', '.join(profile.target_directions) if profile.target_directions else '未填写'}")
        lines.append(f"- 工作地点偏好：{', '.join(profile.preferred_locations) if profile.preferred_locations else '未填写'}")
        lines.append(f"- 学历：{profile.degree or '未填写'}")
        lines.append(f"- 偏好单位：{', '.join(profile.preferred_org_types) if profile.preferred_org_types else '未填写'}")
        lines.append(f"- 排除岗位：{', '.join(profile.excluded_job_types) if profile.excluded_job_types else '未填写'}")
        lines.append("")
        lines.append("## 总览")
        lines.append(f"- 分析岗位总数：{len(sorted_jobs)}")
        lines.append(f"- 强推荐：{counts.get('强推荐', 0)}")
        lines.append(f"- 可关注：{counts.get('可关注', 0)}")
        lines.append(f"- 不推荐：{counts.get('不推荐', 0)}")
        lines.append("")

        for idx, item in enumerate(sorted_jobs, start=1):
            ext = item.extracted
            match = item.match
            lines.append(f"## {idx}. {ext.company_name or '未知单位'} - {ext.job_title or item.title}")
            lines.append(f"- 匹配度：{match.match_score}")
            lines.append(f"- 推荐等级：{match.recommendation}")
            lines.append(f"- 地点：{ext.location or '未说明'}")
            lines.append(f"- 学历要求：{ext.degree_required or '未说明'}")
            lines.append(f"- 发布时间：{item.publish_date or '未提取'}")
            lines.append(f"- 链接：{item.source_url}")
            lines.append(f"- 摘要：{ext.summary or '无'}")
            lines.append("- 维度评分：")
            lines.append(f"  - 方向匹配：{match.direction_match}")
            lines.append(f"  - 地点匹配：{match.location_match}")
            lines.append(f"  - 学历匹配：{match.degree_match}")
            lines.append(f"  - 单位匹配：{match.org_match}")
            lines.append("- 推荐理由：")
            for reason in match.reasons or ["无"]:
                lines.append(f"  - {reason}")
            lines.append("- 风险点：")
            for risk in match.risks or ["无"]:
                lines.append(f"  - {risk}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def save_markdown(markdown: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
