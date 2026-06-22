import json
import logging
from pathlib import Path

from downloader import download_file
from email_parser import extract_text_from_eml
from github_api import get_release_assets
from ai_file_selector import select_file
from ai_url_extractor import parse_release_url
from repo_rules import get_repo_rules

import llms
from config import LLM_PRIMARY, LLM_FALLBACK

logger = logging.getLogger(__name__)


class StepLogger:
    """流水线步骤日志器。"""

    def __init__(self, step_num: int, total: int, name: str):
        self.step_num = step_num
        self.total = total
        self.name = name
        self.lines: list[str] = []

    def __enter__(self):
        logger.info(f"━━━ [{self.step_num}/{self.total}] {self.name} ━━━")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for line in self.lines:
            logger.info(f"  {line}")
        if exc_type:
            logger.error(f"  ✗ 失败 — {exc_val}")
        else:
            logger.info("  ✓ 完成")
        return False

    def log(self, text: str):
        self.lines.append(text)


def _get_llm_clients():
    """获取 LLM 客户端配置。"""
    primary_llm = getattr(llms, LLM_PRIMARY, None)
    fallback_llm = getattr(llms, LLM_FALLBACK, None)
    if not primary_llm or not fallback_llm:
        raise ValueError(f"LLM 配置错误: LLM_PRIMARY={LLM_PRIMARY!r}, LLM_FALLBACK={LLM_FALLBACK!r}，请检查 config.py 和 llms.py")
    return primary_llm.client, fallback_llm.client


def _process_release_assets(owner: str, repo: str, tag: str, primary, fallback, total_steps: int = 4, step_offset: int = 3, assets: list[dict] | None = None) -> dict:
    """处理 release assets 的共享逻辑（步骤 3-6）。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 版本标签
        primary: 主 LLM 客户端
        fallback: 备用 LLM 客户端
        total_steps: 总步骤数
        step_offset: 起始步骤编号
        assets: 预获取的 assets 列表，为 None 时从 API 获取

    Returns:
        处理结果字典
    """
    full_repo = f"{owner}/{repo}"

    # [3/6] 获取 Release 资源
    with StepLogger(step_offset, total_steps, "获取 Release 资源") as step:
        step.log(f"{full_repo} @ {tag}")
        if assets is None:
            assets = get_release_assets(full_repo, tag)
        if not assets:
            step.log("未获取到任何 assets")
            return {"success": 0, "error": "no_assets"}
        assets_display = "\n".join(
            f"    - {a['name']} ({a['size'] / 1024 / 1024:.1f}MB, {a['content_type']})\n"
            f"      {a['browser_download_url']}"
            for a in assets
        )
        step.log(f"{len(assets)} 个 assets:\n{assets_display}")

    # [4/6] 加载仓库规则
    with StepLogger(step_offset + 1, total_steps, "加载仓库规则") as step:
        step.log(f"{owner}/{repo}")
        rules = get_repo_rules(f"{owner}/{repo}")
        step.log(json.dumps(rules, ensure_ascii=False) if rules else "无匹配规则")

    # [5/6] AI 选择文件
    with StepLogger(step_offset + 2, total_steps, "AI 选择文件") as step:
        file_result = select_file(assets=assets, rules=rules, llm=primary, llm_fallback=fallback)
        step.log(json.dumps(file_result, ensure_ascii=False, indent=2))
        if file_result.get("success") != 1:
            return {"success": 0, "error": "file_selection_failed"}

    download_url = file_result["download_url"]

    # [6/6] 下载文件
    with StepLogger(step_offset + 3, total_steps, "下载文件") as step:
        step.log(download_url)
        filepath = download_file(download_url)
        if not filepath:
            step.log("下载失败")
            return {"success": 0, "error": "download_failed"}
        step.log(f"→ {filepath}")

    logger.info(f"流程完成: {total_steps}/{total_steps} 步骤成功")
    return {"success": 1, "download_url": download_url, "file": str(filepath)}


def run(eml_path: Path) -> dict:
    """运行流水线：邮件解析 → 提取 Release URL → GitHub API → 规则匹配 → 选择文件 → 下载。"""
    total_steps = 6
    primary, fallback = _get_llm_clients()

    logger.info(f"开始处理: {eml_path.name}")

    # [1/6] 邮件解析
    with StepLogger(1, total_steps, "邮件解析") as step:
        step.log(f"文件: {eml_path.name}")
        body = extract_text_from_eml(eml_path)
        if not body:
            step.log("邮件正文为空")
            return {"success": 0, "error": "empty_email_body"}
        step.log(f"正文 {len(body)} 字符")

    # [2/6] AI 提取 URL
    with StepLogger(2, total_steps, "AI 提取 URL") as step:
        url_result = parse_release_url(body, primary, llm_fallback=fallback)
        step.log(json.dumps(url_result, ensure_ascii=False, indent=2))
        if url_result.get("success") != 1:
            return {"success": 0, "error": "url_extraction_failed"}

    repo_owner = url_result["repo_owner"]
    repo_name = url_result["repo_name"]
    tag = url_result["tag"]

    # [3-6/6] 处理 release assets
    return _process_release_assets(repo_owner, repo_name, tag, primary, fallback, total_steps, step_offset=3)


def run_release(owner: str, repo: str, tag: str, assets: list[dict] | None = None) -> dict:
    """运行 API 模式流水线：跳过邮件解析，直接处理 release assets。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 版本标签
        assets: 预获取的 assets 列表，为 None 时从 API 获取

    Returns:
        处理结果字典
    """
    total_steps = 4
    primary, fallback = _get_llm_clients()

    logger.info(f"开始处理 API release: {owner}/{repo} @ {tag}")

    # [1-4/4] 处理 release assets（跳过邮件解析和 AI URL 提取）
    return _process_release_assets(owner, repo, tag, primary, fallback, total_steps, step_offset=1, assets=assets)
