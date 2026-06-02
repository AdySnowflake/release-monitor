import logging
from pathlib import Path

from downloader import download_file
from email_parser import extract_text_from_eml
from github_api import get_release_assets
from llm import llm_ds, llm_mimo
from ai_file_selector import select_file
from ai_url_extractor import parse_release_url
from repo_rules import get_repo_rules

logger = logging.getLogger(__name__)


def run(eml_path: Path) -> dict:
    """运行流水线：邮件解析 → 提取 Release URL → GitHub API → 规则匹配 → 选择文件 → 下载。"""
    logger.info(f"开始处理: {eml_path.name}")

    # 邮件解析
    body = extract_text_from_eml(eml_path)
    if not body:
        logger.error("邮件正文为空，终止流程")
        return {"success": 0, "error": "empty_email_body"}

    # 提取 Release URL（重试 + 备用 LLM + Analysis AI）
    url_result = parse_release_url(body, llm_mimo, llm_fallback=llm_ds)
    if url_result.get("success") != 1:
        logger.warning("未能从邮件提取 Release URL")
        return {"success": 0, "error": "url_extraction_failed"}

    release_url = url_result["release_url"]
    repo_owner = url_result["repo_owner"]
    repo_name = url_result["repo_name"]
    tag = url_result["tag"]
    full_repo = f"{repo_owner}/{repo_name}"

    logger.info(f"提取成功: {release_url} ({full_repo} @ {tag})")

    # 获取 Release 资源列表
    assets = get_release_assets(full_repo, tag)
    if not assets:
        logger.error("未获取到任何 assets")
        return {"success": 0, "error": "no_assets"}

    # 加载仓库下载规则
    rules = get_repo_rules(repo_name)

    # 根据规则选择目标文件（重试 + 备用 LLM + Analysis AI）
    file_result = select_file(assets=assets, rules=rules, llm=llm_mimo, llm_fallback=llm_ds)
    if file_result.get("success") != 1:
        logger.warning("未能选择目标文件")
        return {"success": 0, "error": "file_selection_failed"}

    logger.info(f"选择文件: {file_result.get('download_url')}")

    # 下载文件
    download_url = file_result["download_url"]
    filepath = download_file(download_url)
    if not filepath:
        logger.error("文件下载失败")
        return {"success": 0, "error": "download_failed"}

    logger.info(f"下载完成: {filepath}")
    return {"success": 1, "download_url": download_url, "file": str(filepath)}
