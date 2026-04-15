from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agent.schemas import CrawlItem, JobInfo, JobWithMatch, UserProfile


class WorkflowState(BaseModel):
    """Shared mutable state for supervisor-driven multi-agent workflow."""

    user_input: str
    profile: UserProfile | None = None
    crawl_items: list[CrawlItem] = Field(default_factory=list)
    job_infos: list[JobInfo] = Field(default_factory=list)
    matched_items: list[JobWithMatch] = Field(default_factory=list)
    critic_feedback: list[str] = Field(default_factory=list)
    report_markdown: str = ""

    next_action: Literal[
        "parse_profile",
        "crawl",
        "extract",
        "match",
        "critic",
        "report",
        "end",
    ] = "parse_profile"
    retry_target: Literal["extract", "match", ""] = ""
    retry_count: int = 0
    max_retries: int = 1
    errors: list[str] = Field(default_factory=list)
