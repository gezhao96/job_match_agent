from __future__ import annotations

from agent.schemas import JobWithMatch
from agent.state import WorkflowState
from core.profile_parser import UserProfileParser
from tools.crawler import CrawlConfig, JobCrawler
from tools.extractor import JobExtractor
from tools.matcher import JobMatcher
from tools.reporter import ReportBuilder


class PlannerAgent:
    def __init__(self, profile_parser: UserProfileParser) -> None:
        self.profile_parser = profile_parser

    def run(self, state: WorkflowState, max_jobs: int, max_pages: int) -> WorkflowState:
        profile = self.profile_parser.parse(state.user_input)
        profile.max_jobs = max_jobs or profile.max_jobs
        profile.max_pages = max_pages or profile.max_pages
        state.profile = profile
        return state


class CrawlerAgent:
    def run(self, state: WorkflowState) -> WorkflowState:
        assert state.profile is not None
        crawler = JobCrawler(
            CrawlConfig(max_jobs=state.profile.max_jobs, max_pages=state.profile.max_pages)
        )
        state.crawl_items = crawler.crawl(state.profile.url)
        return state


class ExtractorAgent:
    def __init__(self, extractor: JobExtractor) -> None:
        self.extractor = extractor

    def run(self, state: WorkflowState) -> WorkflowState:
        infos = []
        for item in state.crawl_items:
            infos.append(self.extractor.extract(item.title, item.content))
        state.job_infos = infos
        return state


class MatcherAgent:
    def __init__(self, matcher: JobMatcher) -> None:
        self.matcher = matcher

    def run(self, state: WorkflowState) -> WorkflowState:
        assert state.profile is not None
        matched_items: list[JobWithMatch] = []
        for item, info in zip(state.crawl_items, state.job_infos):
            if not info.is_recruitment_related:
                continue
            match = self.matcher.match(state.profile, info)
            matched_items.append(
                JobWithMatch(
                    title=item.title,
                    source_url=item.source_url,
                    publish_date=item.publish_date,
                    extracted=info,
                    match=match,
                )
            )
        state.matched_items = matched_items
        return state


class ReporterAgent:
    def run(self, state: WorkflowState) -> WorkflowState:
        assert state.profile is not None
        state.report_markdown = ReportBuilder.build_markdown(state.profile, state.matched_items)
        return state
