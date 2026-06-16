import logging

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def get_release_assets(repo_name: str, tag: str) -> list[dict]:
    """通过 GitHub API 获取指定 release 的 assets 列表。

    Args:
        repo_name: 仓库全名，如 "CeuiLiSA/Pixiv-Shaft"
        tag: 版本标签，如 "v4.7.5"

    Returns:
        list[dict]: GitHub API 原始 asset 对象列表
    """
    url = f"{GITHUB_API}/repos/{repo_name}/releases/tags/{tag}"
    logger.info(f"请求 GitHub API: {url}")

    resp = requests.get(url, headers={"Accept": "application/vnd.github+json"})
    if resp.status_code == 404:
        logger.error(f"Release 不存在: {repo_name} @ {tag}")
        return []
    if resp.status_code == 403:
        logger.error("GitHub API Rate Limit 或权限不足")
        return []
    resp.raise_for_status()

    data = resp.json()
    assets = data.get("assets", [])

    logger.info(f"获取到 {len(assets)} 个 assets")
    return assets
