import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent / "repo_rules.json"


def load_rules() -> dict:
    """加载规则文件。"""
    with open(RULES_FILE, encoding="utf-8") as file:
        return json.load(file)


def save_rules(rules: dict) -> None:
    """保存规则文件。"""
    with open(RULES_FILE, "w", encoding="utf-8") as file:
        json.dump(rules, file, ensure_ascii=False, indent=2)
        file.write("\n")
    logger.info(f"规则已保存到 {RULES_FILE}")


def get_repo_rules(full_name: str) -> dict:
    """获取指定仓库的规则。

    Args:
        full_name: 仓库全名，格式为 owner/repo

    Returns:
        规则字典
    """
    rule = load_rules()[full_name]
    logger.info(f"找到 {full_name} 的规则: {rule}")
    return rule


def update_repo_tag(owner: str, repo: str, tag: str) -> None:
    """更新仓库的 last_tag 字段并保存。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 新的版本标签
    """
    rules = load_rules()
    full_name = f"{owner}/{repo}"
    rules[full_name]["last_tag"] = tag
    logger.info(f"更新 {full_name} 的 last_tag 为 {tag}")
    save_rules(rules)
