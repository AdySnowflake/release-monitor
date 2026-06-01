import json
import logging
import time
from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """你是一个错误分析器。AI 节点未能成功完成任务，请分析原因并尝试修正。

原始任务:
{original_prompt}

AI 输出:
{ai_output}

请分析失败原因，重新尝试完成任务，输出 JSON 格式：
- success: 1 表示修正成功，0 表示无法修正
- 修正后的结果字段"""


def retry_with_backoff(func, max_retries: int = 2):
    """带指数退避的重试。"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"重试 {max_retries} 次后仍然失败: {e}")
                raise
            wait = 2 ** attempt
            logger.warning(f"调用失败，{wait}s 后重试 ({attempt + 1}/{max_retries}): {e}")
            time.sleep(wait)


def run_with_analysis(
    build_chain: Callable[[BaseChatModel], any],
    input_data: dict,
    llm: BaseChatModel,
    llm_fallback: BaseChatModel | None = None,
) -> dict:
    """运行 chain，失败时用备用 LLM 或 Analysis AI 二次分析。

    Args:
        build_chain: 接受 LLM 返回 chain 的函数
        input_data: chain 的输入
        llm: 主 LLM
        llm_fallback: 备用 LLM

    Returns:
        dict: chain 的输出，或 Analysis AI 的修正结果
    """
    chain = build_chain(llm)

    # 技术失败：重试 + 备用 LLM
    try:
        result = retry_with_backoff(lambda: chain.invoke(input_data))
    except Exception:
        if llm_fallback:
            logger.warning("主 LLM 失败，切换备用 LLM")
            try:
                fallback_chain = build_chain(llm_fallback)
                result = retry_with_backoff(lambda: fallback_chain.invoke(input_data))
            except Exception:
                logger.error("备用 LLM 也失败，终止流程")
                return {"success": 0, "error": "all_llms_failed"}
        else:
            return {"success": 0, "error": "llm_failed"}

    # 业务失败：Analysis AI 二次分析
    if result.get("success") == 1:
        logger.debug(f"AI 调用成功: {json.dumps(result, ensure_ascii=False)}")
        return result

    logger.warning(f"AI 返回 success=0，启动 Analysis AI... 输出: {json.dumps(result, ensure_ascii=False)}")
    return _run_analysis(input_data, result, llm)


def _run_analysis(input_data: dict, ai_output: dict, llm: BaseChatModel) -> dict:
    """Analysis AI：分析失败原因并尝试修正。"""
    analysis_chain = ChatPromptTemplate.from_messages([
        ("system", ANALYSIS_PROMPT),
        ("user", "请分析并修正。"),
    ]) | llm

    try:
        analysis_result = analysis_chain.invoke({
            "original_prompt": json.dumps(input_data, ensure_ascii=False),
            "ai_output": json.dumps(ai_output, ensure_ascii=False),
        })
        logger.info(f"Analysis AI 输出: {analysis_result.content}")
        try:
            return json.loads(analysis_result.content)
        except json.JSONDecodeError:
            logger.error("Analysis AI 输出非合法 JSON")
            return {"success": 0, "error": "analysis_invalid_json"}
    except Exception as e:
        logger.error(f"Analysis AI 调用失败: {e}")
        return {"success": 0, "error": "analysis_failed"}
