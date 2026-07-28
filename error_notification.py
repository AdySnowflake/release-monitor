import logging
from datetime import datetime
from zoneinfo import ZoneInfo

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
