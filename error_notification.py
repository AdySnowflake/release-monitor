import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from feishu_notifier import send_card

logger = logging.getLogger(__name__)
TIMEZONE = ZoneInfo("Asia/Shanghai")


def send_error_notification(
    error_records: list[dict],
    ai_report: str | None = None,
) -> None:
    occurred_at = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")
    sections = [f"**发生时间**：{occurred_at}"]

    for index, record in enumerate(error_records, start=1):
        repository = (
            record.get("repository") or record.get("stage") or "未知目标"
        )
        tag = f" @ {record['tag']}" if record.get("tag") else ""
        label = "故障对象" if len(error_records) == 1 else f"故障 {index}"
        error_text = str(
            record.get("error_log")
            or record.get("message")
            or record.get("error")
            or "unknown_error"
        )
        sections.append(
            f"**{label}**：{repository}{tag}\n\n"
            f"**错误日志**\n```text\n{error_text}\n```"
        )

    if ai_report:
        sections.append(f"**AI 分析**\n\n{ai_report}")

    try:
        send_card("Release Monitor 告警", "\n\n---\n\n".join(sections))
        logger.info("飞书告警发送成功")
    except Exception:
        logger.exception("飞书告警发送失败")


def send_auto_disable_notification(events: list[dict]) -> None:
    """发送连续失败自动禁用的飞书通知，走与其他告警相同的渠道。"""
    if not config.FEISHU_ENABLED:
        logger.info("飞书通知未启用，跳过自动禁用通知")
        return
    if not config.FEISHU_WEBHOOK_URL or not config.FEISHU_SIGNING_SECRET:
        logger.error("飞书配置不完整，跳过自动禁用通知")
        return

    occurred_at = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")
    sections = [f"**发生时间**：{occurred_at}"]

    for index, event in enumerate(events, start=1):
        repository = event.get("repository") or "未知仓库"
        tag = f" @ {event['tag']}" if event.get("tag") else ""
        label = "仓库" if len(events) == 1 else f"仓库 {index}"
        error_text = str(event.get("error_log") or "unknown_error")
        sections.append(
            f"**{label}**：{repository}{tag}\n\n"
            f"**原因**：连续失败 {event.get('failures', 3)} 次，已自动禁用\n\n"
            f"**最近错误**\n```text\n{error_text}\n```\n\n"
            "**恢复方法**：修复问题后，将 repo_rules.json 中该仓库的 "
            "`\"disabled\"` 改为 `false` 或删除该字段。"
        )

    try:
        send_card("Release Monitor 自动禁用告警", "\n\n---\n\n".join(sections))
        logger.info("自动禁用飞书通知发送成功")
    except Exception:
        logger.exception("自动禁用飞书通知发送失败")
