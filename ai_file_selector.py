import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from error_handler import run_with_analysis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 GitHub Release 文件选择器。根据 assets 列表和仓库规则，选择最合适的下载文件。

规则字段：
- extension: 文件后缀名（如 .apk、.ipa、.exe）
- include: 文件名必须包含的关键词
- exclude: 文件名不能包含的关键词

download_url 必须直接复制 assets 列表中的原始链接，不要自己拼接或修改。

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


def select_file(
    assets: list[dict],
    rules: dict,
    llm: BaseChatModel,
    llm_fallback: BaseChatModel | None = None,
) -> dict:
    """选择目标文件：从 assets 列表中选择要下载的文件。"""
    assets_text = "\n".join(
        f"- {a['name']} ({a['size']} bytes, {a['content_type']})\n  url: {a['browser_download_url']}"
        for a in assets
    )
    rules_text = json.dumps(rules, ensure_ascii=False) if rules else "无"

    logger.debug(f"选择目标文件 输入 - assets: {assets_text}")
    logger.debug(f"选择目标文件 输入 - rules: {rules_text}")
    logger.info("选择目标文件 开始选择文件...")
    result = run_with_analysis(
        build_chain,
        {"assets": assets_text, "rules": rules_text},
        llm,
        llm_fallback,
    )
    logger.info(f"选择目标文件 输出: {json.dumps(result, ensure_ascii=False)}")
    return result
