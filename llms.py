"""按用途惰性创建 OpenAI 兼容的 LLM 客户端。"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()

LLM_ROLES = {"primary", "fallback"}


def _env_name(role: str, field: str) -> str:
    return f"LLM_{role.upper()}_{field}"


def has_llm_config(role: str) -> bool:
    """指定用途存在任意配置时返回 True。"""
    if role not in LLM_ROLES:
        raise ValueError(f"未知的 LLM 用途: {role!r}")
    return any(
        os.getenv(_env_name(role, field))
        for field in ("BASE_URL", "API_KEY", "MODEL")
    )


@lru_cache(maxsize=None)
def get_llm_client(role: str) -> ChatOpenAI:
    """从环境变量读取配置，按用途创建并缓存 LLM 客户端。"""
    if role not in LLM_ROLES:
        raise ValueError(f"未知的 LLM 用途: {role!r}")

    base_url = os.getenv(_env_name(role, "BASE_URL")) or None
    api_key = os.getenv(_env_name(role, "API_KEY"), "")
    model = os.getenv(_env_name(role, "MODEL"), "")

    missing = []
    if not api_key:
        missing.append(_env_name(role, "API_KEY"))
    if not model:
        missing.append(_env_name(role, "MODEL"))
    if missing:
        raise ValueError(f"缺少 LLM 环境变量: {', '.join(missing)}")

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
        temperature=0,
    )
