from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from agent.prompts import JOB_EXTRACT_PROMPT
from agent.schemas import JobInfo


class JobExtractor:
    def __init__(self, llm) -> None:
        self.chain = ChatPromptTemplate.from_messages(
            [
                ("system", JOB_EXTRACT_PROMPT),
                (
                    "human",
                    "招聘标题：\n{title}\n\n招聘正文：\n{content}",
                ),
            ]
        ) | llm.with_structured_output(JobInfo, method="function_calling")

    def extract(self, title: str, content: str) -> JobInfo:
        return self.chain.invoke({"title": title, "content": content[:12000]})
