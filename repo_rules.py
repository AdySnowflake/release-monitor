import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

RULES_FILE = Path(__file__).parent / "repo_rules.json"

TIMEZONE = ZoneInfo("Asia/Shanghai")
MAX_CONSECUTIVE_FAILURES = 3
BACKOFF_BASE_HOURS = 1


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


def is_disabled(rule: dict) -> bool:
    """判断仓库是否被禁用，仅接受布尔值 true，其他取值视为非法配置。"""
    value = rule.get("disabled")
    if value is None or isinstance(value, bool):
        return value is True
    raise ValueError(
        f"disabled 字段应为布尔值 true/false，当前为 {value!r}"
    )


def is_backing_off(rule: dict) -> bool:
    """判断仓库是否处于失败退避期内。"""
    raw = rule.get("next_check_after")
    if not raw:
        return False
    try:
        next_check = datetime.fromisoformat(str(raw))
    except ValueError:
        logger.warning(f"next_check_after 无法解析: {raw!r}，按已过期处理")
        return False
    if next_check.tzinfo is None:
        next_check = next_check.replace(tzinfo=TIMEZONE)
    return datetime.now(TIMEZONE) < next_check


def clear_failure_state(owner: str, repo: str) -> None:
    """清除仓库的连续失败计数与退避时间，字段不存在时不写盘。"""
    full_name = f"{owner}/{repo}"
    try:
        rules = load_rules()
        rule = rules.get(full_name)
        if rule is None:
            return
        if "consecutive_failures" not in rule and "next_check_after" not in rule:
            return
        rule.pop("consecutive_failures", None)
        rule.pop("next_check_after", None)
        save_rules(rules)
        logger.info(f"已清除 {full_name} 的连续失败状态")
    except Exception:
        logger.exception(f"清除 {full_name} 的失败状态出错")


def record_failure(
    owner: str,
    repo: str,
    *,
    tag: str | None = None,
    error_log: str | None = None,
) -> dict | None:
    """记录一次失败：计数 +1 并设置退避；达到阈值则自动禁用。

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        tag: 本次失败的版本标签（检查阶段失败时为 None）
        error_log: 最近一次失败的错误信息

    Returns:
        触发自动禁用时返回事件字典，否则返回 None。
    """
    full_name = f"{owner}/{repo}"
    try:
        rules = load_rules()
        rule = rules.get(full_name)
        if rule is None:
            logger.warning(f"{full_name} 不在规则中，跳过失败计数")
            return None

        count = int(rule.get("consecutive_failures") or 0) + 1
        if count < MAX_CONSECUTIVE_FAILURES:
            backoff = timedelta(hours=BACKOFF_BASE_HOURS * 2 ** (count - 1))
            next_check = datetime.now(TIMEZONE) + backoff
            rule["consecutive_failures"] = count
            rule["next_check_after"] = next_check.isoformat(timespec="seconds")
            save_rules(rules)
            logger.warning(
                f"{full_name} 连续失败 {count} 次，退避至 {next_check.isoformat()}"
            )
            return None

        rule.pop("consecutive_failures", None)
        rule.pop("next_check_after", None)
        rule["disabled"] = True
        save_rules(rules)
        logger.error(
            f"{full_name} 连续失败 {MAX_CONSECUTIVE_FAILURES} 次，已自动禁用"
        )
        return {
            "repository": full_name,
            "tag": tag,
            "error_log": error_log,
            "failures": MAX_CONSECUTIVE_FAILURES,
        }
    except Exception:
        logger.exception(f"记录 {full_name} 的失败状态出错")
        return None
