from __future__ import annotations

import os

from dotenv import load_dotenv

try:
    # 优先使用独立的 OpenAI 集成包（推荐）
    from langchain_openai import ChatOpenAI
except ImportError:
    # 兼容旧环境：若未安装 langchain-openai，则回退到 community 包
    from langchain_community.chat_models import ChatOpenAI


# 如需更换模型或服务地址，修改下面 3 个常量即可。
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_API_KEY = "Your API Key Here"


def build_llm(temperature: float = 0.0) -> ChatOpenAI:
    load_dotenv()

    # 优先级：OPENAI_* > DEEPSEEK_* > 代码默认值
    model = (
        os.getenv("OPENAI_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or DEFAULT_MODEL
    )
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or DEFAULT_BASE_URL
    )
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or DEFAULT_API_KEY
    )

    if not api_key:
        raise ValueError(
            "未配置 API Key。请在 core/llm_factory.py 的 DEFAULT_API_KEY 填写，"
            "或设置 OPENAI_API_KEY/DEEPSEEK_API_KEY。"
        )

    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)

"""
请帮我分析这个招聘网站里前两页适合我的岗位： https://job.hust.edu.cn/xjssd123123/index.htm我的求职方向是光纤传感、光电信息、AI算法、智能感知、大模型； 希望工作地在上海、武汉； 学历是博士；优先考虑高校、研究院或企业的技术研发类岗位； 不考虑销售、行政和纯运维类岗位。

"""