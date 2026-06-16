from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from error_handler import run_with_analysis

SYSTEM_PROMPT = """你是一个 GitHub Release URL 提取器。从用户提供的邮件内容中提取 GitHub Release 信息。

邮件可能来自 Blogtrottr（RSS 转邮件服务），包含模板噪声（跟踪像素、广告等），你需要穿透这些噪声找到有效的 GitHub Release 链接。

输出必须包含以下字段：
- success: 1 表示提取成功，0 表示失败
- release_url: GitHub Release 完整链接（如 https://github.com/owner/repo/releases/tag/v1.0.0）
- repo_owner: 仓库作者（如 owner）
- repo_name: 仓库名（如 repo）
- tag: 版本标签（如 v1.0.0）
- release: 1 表示正式版，0 表示测试版（pre-release、beta、alpha、rc 等）

{format_instructions}"""

USER_PROMPT = "以下是邮件内容：\n\n{email_body}"


def build_chain(llm: BaseChatModel):
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT),
    ]).partial(format_instructions=parser.get_format_instructions())

    return prompt | llm | parser


def parse_release_url(
    email_body: str,
    llm: BaseChatModel,
    llm_fallback: BaseChatModel | None = None,
) -> dict:
    """提取 Release URL：从邮件正文中提取 GitHub Release URL 和仓库信息。"""
    return run_with_analysis(build_chain, {"email_body": email_body}, llm, llm_fallback)
