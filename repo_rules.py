import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent / "repo_rules.json"


def load_rules() -> dict:
    if not RULES_FILE.exists():
        logger.warning(f"规则文件不存在: {RULES_FILE}")
        return {}
    with open(RULES_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_repo_rules(repo_name: str) -> dict:
    """获取指定仓库的规则（大小写宽松匹配）。返回 { prefer: [...], exclude: [...] }，无规则返回空 dict。"""
    rules = load_rules()
    lower_name = repo_name.lower()
    for key, rule in rules.items():
        if key.lower() == lower_name:
            logger.info(f"找到 {repo_name} 的规则: {rule}")
            return rule
    return {}
