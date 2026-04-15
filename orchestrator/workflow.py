from __future__ import annotations

from pathlib import Path

from agent.critic import CriticAgent
from agent.specialists import (
    CrawlerAgent,
    ExtractorAgent,
    MatcherAgent,
    PlannerAgent,
    ReporterAgent,
)
from agent.state import WorkflowState
from agent.supervisor import SupervisorAgent
from core.utils import dump_json
from tools.reporter import ReportBuilder


class MultiAgentWorkflow:
    """Supervisor + Specialists workflow runner."""

    def __init__(
        self,
        planner: PlannerAgent,
        crawler: CrawlerAgent,
        extractor: ExtractorAgent,
        matcher: MatcherAgent,
        critic: CriticAgent,
        reporter: ReporterAgent,
        supervisor: SupervisorAgent,
        output_dir: Path,
        report_dir: Path,
    ) -> None:
        self.planner = planner
        self.crawler = crawler
        self.extractor = extractor
        self.matcher = matcher
        self.critic = critic
        self.reporter = reporter
        self.supervisor = supervisor
        self.output_dir = output_dir
        self.report_dir = report_dir

    def run(self, user_input: str, max_jobs: int, max_pages: int) -> WorkflowState:
        state = WorkflowState(user_input=user_input)

        while state.next_action != "end":
            if state.next_action == "parse_profile":
                print("[Planner] 正在解析用户画像...")
                state = self.planner.run(state, max_jobs=max_jobs, max_pages=max_pages)
                dump_json(state.profile.model_dump(mode="json"), self.output_dir / "user_profile.json")

            elif state.next_action == "crawl":
                print("[Crawler] 正在抓取招聘信息...")
                state = self.crawler.run(state)
                dump_json(
                    [item.model_dump(mode="json") for item in state.crawl_items],
                    self.output_dir / "crawled_jobs.json",
                )
                print(f"    已抓取 {len(state.crawl_items)} 条详情页内容")

            elif state.next_action == "extract":
                print("[Extractor] 正在提取岗位结构化信息...")
                state = self.extractor.run(state)
                structured = []
                for item, info in zip(state.crawl_items, state.job_infos):
                    structured.append(
                        {
                            "title": item.title,
                            "source_url": item.source_url,
                            "publish_date": item.publish_date,
                            "job_info": info.model_dump(mode="json"),
                        }
                    )
                dump_json(structured, self.output_dir / "structured_jobs.json")

            elif state.next_action == "match":
                print("[Matcher] 正在进行岗位匹配评分...")
                state = self.matcher.run(state)
                dump_json(
                    [item.model_dump(mode="json") for item in state.matched_items],
                    self.output_dir / "match_results.json",
                )

            elif state.next_action == "critic":
                print("[Critic] 正在审查结果质量...")
                state = self.critic.review(state)
                if state.critic_feedback:
                    for message in state.critic_feedback:
                        print(f"    - {message}")
                else:
                    print("    - 质量检查通过")

            elif state.next_action == "report":
                print("[Reporter] 正在生成报告...")
                state = self.reporter.run(state)
                report_path = self.report_dir / "latest_report.md"
                ReportBuilder.save_markdown(state.report_markdown, report_path)

            state.next_action = self.supervisor.decide_next_action(state)

        return state
