from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from agent.prompts import MATCH_PROMPT
from agent.schemas import JobInfo, MatchResult, UserProfile


class JobMatcher:
    def __init__(self, llm) -> None:
        self.chain = ChatPromptTemplate.from_messages(
            [
                ("system", MATCH_PROMPT),
                (
                    "human",
                    "用户画像：\n{profile}\n\n岗位信息：\n{job_info}",
                ),
            ]
        ) | llm.with_structured_output(MatchResult, method="function_calling")

    def match(self, profile: UserProfile, job_info: JobInfo) -> MatchResult:
        return self.chain.invoke(
            {
                "profile": profile.model_dump_json(ensure_ascii=False, indent=2),
                "job_info": job_info.model_dump_json(ensure_ascii=False, indent=2),
            }
        )
