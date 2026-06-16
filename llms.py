"""LLM Provider 定义。

新增 provider 只需在下方添加一个 LLM 实例。
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()


class LLM:
    """LLM 配置与实例。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self._client = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key),
            temperature=0,
        )

    @property
    def client(self) -> ChatOpenAI:
        return self._client


# --- LLM 实例 ---

llm_mimo = LLM(
    base_url=os.getenv("MIMO_BASE_URL", ""),
    api_key=os.getenv("MIMO_API_KEY", ""),
    model=os.getenv("MIMO_MODEL", ""),
)

llm_ds = LLM(
    base_url=os.getenv("DS_BASE_URL", ""),
    api_key=os.getenv("DS_API_KEY", ""),
    model=os.getenv("DS_MODEL", ""),
)

# 新增示例：
# llm_openai = LLM(
#     base_url="https://api.openai.com/v1",
#     api_key=os.getenv("OPENAI_API_KEY", ""),
#     model="gpt-4o-mini",
# )
