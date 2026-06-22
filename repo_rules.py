import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent / "repo_rules.json"

# 内存中的规则缓存，避免重复读取文件
_rules_cache: dict | None = None


def load_rules() -> dict:
    """加载规则文件，使用缓存避免重复读取。"""
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    if not RULES_FILE.exists():
        logger.warning(f"规则文件不存在: {RULES_FILE}")
        return {}
    with open(RULES_FILE, encoding="utf-8") as f:
        _rules_cache = json.load(f)
        return _rules_cache


def save() -> None:
    """将内存中的规则持久化到 repo_rules.json。"""
    global _rules_cache
    if _rules_cache is None:
        return
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(_rules_cache, f, ensure_ascii=False, indent=2)
    logger.info(f"规则已保存到 {RULES_FILE}")


def get_repo_rules(full_name: str) -> dict:
    """获取指定仓库的规则（大小写宽松匹配）。

    Args:
        full_name: 仓库全名，格式为 owner/repo

    Returns:
        规则字典，无规则返回空 dict
    """
    rules = load_rules()
    lower_name = full_name.lower()
    for key, rule in rules.items():
        if key.lower() == lower_name:
            logger.info(f"找到 {full_name} 的规则: {rule}")
            return rule
    return {}


def get_last_tag(owner: str, repo: str) -> str | None:
    """获取仓库最后处理的 tag。

    Args:
        owner: 仓库所有者
        repo: 仓库名称

    Returns:
        最后处理的 tag，无记录返回 None
    """
    rules = load_rules()
    full_name = f"{owner}/{repo}".lower()
    for key, rule in rules.items():
        if key.lower() == full_name:
            return rule.get("last_tag")
    return None


def update_repo_tag(owner: str, repo: str, tag: str) -> None:
    """更新仓库的 last_tag 字段并保存。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 新的版本标签
    """
    global _rules_cache
    rules = load_rules()
    full_name = f"{owner}/{repo}".lower()

    # 查找匹配的仓库（大小写宽松匹配）
    for key in rules:
        if key.lower() == full_name:
            rules[key]["last_tag"] = tag
            logger.info(f"更新 {key} 的 last_tag 为 {tag}")
            save()
            return

    # 仓库不存在时的提示
    logger.warning(f"仓库 {owner}/{repo} 不在 repo_rules.json 中，无法更新 last_tag")
