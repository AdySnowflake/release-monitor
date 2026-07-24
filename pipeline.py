import json
import logging

from downloader import download_file
from github_api import get_release_assets
from ai_file_selector import select_file
from repo_rules import get_repo_rules
from todo import create_todo

import llms
import config
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


def _process_release_assets(
    owner: str,
    repo: str,
    tag: str,
    primary,
    fallback,
    assets: list[dict] | None = None,
) -> dict:
    """选择并下载 release asset。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 版本标签
        primary: 主 LLM 客户端
        fallback: 备用 LLM 客户端
        assets: 预获取的 assets 列表，为 None 时从 API 获取

    Returns:
        处理结果字典
    """
    full_repo = f"{owner}/{repo}"
    total_steps = 4

    # [1/4] 获取 Release 资源
    with StepLogger(1, total_steps, "获取 Release 资源") as step:
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

    # [2/4] 加载仓库规则
    with StepLogger(2, total_steps, "加载仓库规则") as step:
        step.log(f"{owner}/{repo}")
        rules = get_repo_rules(f"{owner}/{repo}")
        step.log(json.dumps(rules, ensure_ascii=False) if rules else "无匹配规则")

    # [3/4] AI 选择文件
    with StepLogger(3, total_steps, "AI 选择文件") as step:
        file_result = select_file(assets=assets, rules=rules, llm=primary, llm_fallback=fallback)
        step.log(json.dumps(file_result, ensure_ascii=False, indent=2))
        if file_result.get("success") != 1:
            return {"success": 0, "error": "file_selection_failed"}

    download_url = file_result.get("download_url")
    asset_urls = {
        asset.get("browser_download_url")
        for asset in assets
        if isinstance(asset.get("browser_download_url"), str)
    }
    if not isinstance(download_url, str) or download_url not in asset_urls:
        logger.error(f"AI 返回的下载地址不在 Release assets 中: {download_url!r}")
        return {"success": 0, "error": "invalid_download_url"}

    # [4/4] 下载文件
    with StepLogger(4, total_steps, "下载文件") as step:
        step.log(download_url)
        filepath = download_file(download_url)
        if not filepath:
            step.log("下载失败")
            return {"success": 0, "error": "download_failed"}
        step.log(f"→ {filepath}")

    # 创建待办（可选）
    if getattr(config, "TODO_ENABLED", False):
        if not create_todo(repo, tag):
            logger.warning("待办创建未成功，但不影响下载结果")

    logger.info(f"流程完成: {total_steps}/{total_steps} 步骤成功")
    return {"success": 1, "download_url": download_url, "file": str(filepath)}


def run_release(owner: str, repo: str, tag: str, assets: list[dict] | None = None) -> dict:
    """处理 GitHub release assets。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 版本标签
        assets: 预获取的 assets 列表，为 None 时从 API 获取

    Returns:
        处理结果字典
    """
    primary, fallback = _get_llm_clients()

    logger.info(f"开始处理 API release: {owner}/{repo} @ {tag}")

    return _process_release_assets(owner, repo, tag, primary, fallback, assets=assets)
