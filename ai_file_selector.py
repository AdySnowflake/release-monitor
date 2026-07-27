import json
import logging
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llms import get_llm_client, has_llm_config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 GitHub Release 文件选择器。根据 assets 列表和仓库规则，选择最合适的下载文件。

规则字段：
- extension: 文件后缀名（如 .apk、.ipa、.exe）
- include: 文件名必须包含的关键词
- exclude: 文件名不能包含的关键词

download_url 必须直接复制 assets 列表中的 browser_download_url 字段，不要自己拼接或修改，也不要使用 url 字段。

输出：
- success: 1 表示选择成功，0 表示失败
- download_url: 选中文件的原始下载链接

{format_instructions}"""

USER_PROMPT = """Assets 列表:
{assets}

仓库规则:
{rules}"""


def build_chain(llm: BaseChatModel):
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT),
    ]).partial(format_instructions=parser.get_format_instructions())

    return prompt | llm | parser


def _invoke_with_retry(role: str, input_data: dict, max_retries: int = 2) -> dict:
    """创建指定用途的客户端并带退避重试调用。"""
    llm = get_llm_client(role)
    chain = build_chain(llm)

    for attempt in range(max_retries + 1):
        try:
            return chain.invoke(input_data)
        except Exception as error:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            logger.warning(
                f"LLM {role!r} 调用失败，{wait}s 后重试 "
                f"({attempt + 1}/{max_retries}): {error}"
            )
            time.sleep(wait)

    raise RuntimeError("LLM 重试流程异常结束")


def select_file(assets: list[dict], rules: dict) -> dict:
    """选择目标文件：从 assets 列表中选择要下载的文件。"""
    input_data = {
        "assets": json.dumps(assets, ensure_ascii=False),
        "rules": json.dumps(rules, ensure_ascii=False),
    }

    try:
        result = _invoke_with_retry("primary", input_data)
    except Exception as error:
        if not has_llm_config("fallback"):
            logger.error(f"主 LLM 调用失败: {error}")
            return {"success": 0, "error": "llm_failed"}

        logger.warning(f"主 LLM 调用失败，切换备用 LLM: {error}")
        try:
            result = _invoke_with_retry("fallback", input_data)
        except Exception as fallback_error:
            logger.error(f"备用 LLM 调用失败: {fallback_error}")
            return {"success": 0, "error": "all_llms_failed"}

    if result.get("success") == 1:
        logger.debug(f"AI 调用成功: {json.dumps(result, ensure_ascii=False)}")
    else:
        logger.warning(f"AI 未选择文件: {json.dumps(result, ensure_ascii=False)}")
    return result
