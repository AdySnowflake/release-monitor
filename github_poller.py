import logging
from dataclasses import dataclass

import requests

from repo_rules import load_rules, get_last_tag
from config import get_github_headers, get_proxies

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


@dataclass
class ReleaseInfo:
    """新 release 信息。"""
    owner: str
    repo: str
    tag: str
    assets: list[dict]
    api_response: dict | None = None


def check_new_releases() -> list[ReleaseInfo]:
    """遍历 repo_rules.json 中的仓库，检查是否有新 release。

    Returns:
        新 release 信息列表，无新 release 时返回空列表
    """
    rules = load_rules()
    if not rules:
        logger.warning("repo_rules.json 为空或不存在")
        return []

    new_releases = []

    for repo_key in rules:
        # 解析 owner/repo 格式
        parts = repo_key.split("/")
        if len(parts) != 2:
            logger.warning(f"跳过无效的仓库格式: {repo_key}（需要 owner/repo 格式）")
            continue

        owner, repo = parts
        release_info = _check_repo(owner, repo)
        if release_info:
            new_releases.append(release_info)

    logger.info(f"检查完成，发现 {len(new_releases)} 个新 release")
    return new_releases


def _check_repo(owner: str, repo: str) -> ReleaseInfo | None:
    """检查单个仓库是否有新 release。

    Args:
        owner: 仓库所有者
        repo: 仓库名称

    Returns:
        新 release 信息，无新 release 时返回 None
    """
    # 获取最新 release
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest"
    logger.info(f"检查仓库: {owner}/{repo}")

    try:
        resp = requests.get(
            url,
            headers=get_github_headers(),
            timeout=10,
            proxies=get_proxies(),
        )
        if resp.status_code == 404:
            logger.warning(f"仓库 {owner}/{repo} 无 release")
            return None
        if resp.status_code == 403:
            logger.warning(f"GitHub API 速率限制或权限不足: {owner}/{repo}")
            return None
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求失败 {owner}/{repo}: {e}")
        return None

    data = resp.json()
    tag = data.get("tag_name")
    if not tag:
        logger.warning(f"仓库 {owner}/{repo} 的 release 无 tag_name")
        return None

    # 与 last_tag 比较
    last_tag = get_last_tag(owner, repo)
    if tag == last_tag:
        logger.info(f"仓库 {owner}/{repo} 无新版本（当前: {tag}）")
        return None

    # 获取 assets
    assets = data.get("assets", [])
    logger.info(f"发现新版本: {owner}/{repo} @ {tag}（{len(assets)} 个 assets）")

    return ReleaseInfo(
        owner=owner,
        repo=repo,
        tag=tag,
        assets=assets,
        api_response=data,
    )
