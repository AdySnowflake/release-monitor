import logging
from dataclasses import dataclass

import requests

from config import get_github_headers, get_proxies
from repo_rules import load_rules

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


@dataclass
class ReleaseInfo:
    """新 release 信息。"""

    owner: str
    repo: str
    tag: str
    assets: list[dict]


def check_new_releases() -> tuple[list[ReleaseInfo], list[dict]]:
    """遍历 repo_rules.json，返回新版本和检查失败记录。"""
    rules = load_rules()
    new_releases: list[ReleaseInfo] = []
    failures: list[dict] = []

    for repo_key in rules:
        try:
            owner, repo = repo_key.split("/")
            release_info = _check_repo(
                owner,
                repo,
                rules[repo_key].get("last_tag"),
            )
            if release_info:
                new_releases.append(release_info)
        except Exception as error:
            error_log = (
                f"检查仓库 {repo_key!s} 失败: "
                f"{type(error).__name__}: {error}"
            )
            logger.error(error_log)
            failures.append(
                {
                    "stage": "release_check",
                    "repository": str(repo_key),
                    "error": type(error).__name__,
                    "error_log": error_log,
                }
            )

    logger.info(
        f"检查完成，发现 {len(new_releases)} 个新 release，"
        f"{len(failures)} 个仓库检查失败"
    )
    return new_releases, failures


def _check_repo(
    owner: str,
    repo: str,
    last_tag: str | None,
) -> ReleaseInfo | None:
    """检查单个仓库是否有新 release。"""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest"
    logger.info(f"检查仓库: {owner}/{repo}")

    resp = requests.get(
        url,
        headers=get_github_headers(),
        timeout=10,
        proxies=get_proxies(),
    )
    if resp.status_code == 404:
        logger.warning(f"仓库 {owner}/{repo} 无 release")
        return None
    resp.raise_for_status()

    data = resp.json()
    tag = data.get("tag_name")
    if not tag:
        raise ValueError("latest release 缺少 tag_name")

    if tag == last_tag:
        logger.info(f"仓库 {owner}/{repo} 无新版本（当前: {tag}）")
        return None

    assets = data.get("assets", [])
    logger.info(f"发现新版本: {owner}/{repo} @ {tag}（{len(assets)} 个 assets）")

    return ReleaseInfo(owner=owner, repo=repo, tag=tag, assets=assets)
