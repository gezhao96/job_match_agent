from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class UserProfile(BaseModel):
    """Structured user intent parsed from natural language input."""

    url: str = Field(..., description="招聘网站列表页或详情页 URL")
    target_directions: List[str] = Field(default_factory=list, description="目标研究方向或岗位方向")
    preferred_locations: List[str] = Field(default_factory=list, description="期望工作地点")
    degree: str = Field(default="", description="用户学历")
    preferred_org_types: List[str] = Field(default_factory=list, description="偏好单位类型")
    excluded_job_types: List[str] = Field(default_factory=list, description="不考虑的岗位类型")
    max_jobs: int = Field(default=10, ge=1, le=30, description="最多分析的岗位数量")
    max_pages: int = Field(default=3, ge=1, le=10, description="最多抓取的列表页数量")


class CrawlItem(BaseModel):
    """Raw page item produced by crawler before structured extraction."""

    title: str = Field(default="")
    source_url: str = Field(default="", description="页面原始链接")
    # 标识当前抓取内容是详情页、列表页还是未知类型
    page_type: Literal["detail_page", "list_page", "unknown"] = "unknown"
    publish_date: Optional[str] = None
    content: str = Field(default="")
    # 仅当来源于列表页抓取时记录页码
    list_page: Optional[int] = None


class JobInfo(BaseModel):
    """Normalized job information extracted from page content."""

    company_name: str = Field(default="")
    job_title: str = Field(default="")
    location: str = Field(default="")
    degree_required: str = Field(default="")
    major_required: str = Field(default="")
    organization_type: str = Field(default="")
    responsibilities: str = Field(default="")
    requirements: str = Field(default="")
    deadline: str = Field(default="")
    application_method: str = Field(default="")
    # 供报告快速展示的一段摘要
    summary: str = Field(default="")
    # 用于过滤非招聘内容（如通知、新闻等）
    is_recruitment_related: bool = Field(default=True)


class MatchResult(BaseModel):
    """Scoring result between user profile and one job posting."""

    # 综合匹配分，范围 0-100
    match_score: int = Field(ge=0, le=100)
    # 各维度子分，范围 0-100
    direction_match: int = Field(ge=0, le=100)
    location_match: int = Field(ge=0, le=100)
    degree_match: int = Field(ge=0, le=100)
    org_match: int = Field(ge=0, le=100)
    recommendation: Literal["强推荐", "可关注", "不推荐"]
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class JobWithMatch(BaseModel):
    """Final report item that combines extracted job info and match scores."""

    title: str
    source_url: str
    publish_date: Optional[str] = None
    extracted: JobInfo
    match: MatchResult
