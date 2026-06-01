from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from config import DS_BASE_URL, DS_API_KEY, DS_MODEL, MIMO_BASE_URL, MIMO_API_KEY, MIMO_MODEL


def _make_llm(base_url: str, api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key or ""),
        temperature=0,
    )


llm_ds = _make_llm(DS_BASE_URL, DS_API_KEY, DS_MODEL)
llm_mimo = _make_llm(MIMO_BASE_URL, MIMO_API_KEY, MIMO_MODEL)
