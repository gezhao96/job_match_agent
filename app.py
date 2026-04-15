from __future__ import annotations

import argparse
from pathlib import Path

from agent.critic import CriticAgent
from agent.specialists import (
    CrawlerAgent,
    ExtractorAgent,
    MatcherAgent,
    PlannerAgent,
    ReporterAgent,
)
from agent.supervisor import SupervisorAgent
from core.llm_factory import build_llm
from core.profile_parser import UserProfileParser
from core.utils import read_text
from orchestrator.workflow import MultiAgentWorkflow
from tools.extractor import JobExtractor
from tools.matcher import JobMatcher


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
    parser = argparse.ArgumentParser(description="求职信息匹配 Multi-Agent 版")
    parser.add_argument("--input-file", type=str, default="", help="自然语言输入文件路径")
    parser.add_argument("--input-text", type=str, default="", help="直接传入自然语言输入")
    parser.add_argument("--max-jobs", type=int, default=10, help="最多分析岗位数")
    parser.add_argument("--max-pages", type=int, default=3, help="最多抓取列表页数")
    args = parser.parse_args()

    user_input = collect_user_input(args)
    if not user_input.strip():
        raise ValueError("未接收到有效输入。")

    llm = build_llm(temperature=0.0)
    workflow = MultiAgentWorkflow(
        planner=PlannerAgent(UserProfileParser(llm)),
        crawler=CrawlerAgent(),
        extractor=ExtractorAgent(extractor=JobExtractor(llm)),
        matcher=MatcherAgent(matcher=JobMatcher(llm)),
        critic=CriticAgent(),
        reporter=ReporterAgent(),
        supervisor=SupervisorAgent(),
        output_dir=OUTPUT_DIR,
        report_dir=REPORT_DIR,
    )

    state = workflow.run(user_input=user_input, max_jobs=args.max_jobs, max_pages=args.max_pages)

    report_path = REPORT_DIR / "latest_report.md"
    print("\n处理完成。输出文件：")
    print(f"- {OUTPUT_DIR / 'user_profile.json'}")
    print(f"- {OUTPUT_DIR / 'crawled_jobs.json'}")
    print(f"- {OUTPUT_DIR / 'structured_jobs.json'}")
    print(f"- {OUTPUT_DIR / 'match_results.json'}")
    print(f"- {report_path}")

    print("\n报告预览：\n")
    print(state.report_markdown[:3000])


if __name__ == "__main__":
    main()
