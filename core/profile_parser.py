from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from agent.prompts import USER_PROFILE_PROMPT
from agent.schemas import UserProfile


class UserProfileParser:
    """将用户自然语言输入解析为结构化 UserProfile。"""

    def __init__(self, llm) -> None:
        # 构建一个两段式提示词：系统规则 + 用户原始输入。
        # 再通过 with_structured_output 强制模型按 UserProfile 输出。
        self.chain = ChatPromptTemplate.from_messages(
            [
                ("system", USER_PROFILE_PROMPT),
                ("human", "{user_input}"),
            ]
        ) | llm.with_structured_output(UserProfile, method="function_calling")

    def parse(self, user_input: str) -> UserProfile:
        """执行调用并返回结构化后的用户画像。"""

        # invoke 入参的 key 必须与模板中的 {user_input} 一致。
        return self.chain.invoke({"user_input": user_input})
