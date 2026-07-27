import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import config

logger = logging.getLogger(__name__)

TICKTICK_API_URL = "https://api.ticktick.com/open/v1/task"
TIMEZONE = ZoneInfo("Asia/Shanghai")


def create_todo(repo_name: str, tag: str) -> bool:
    """创建 TickTick 待办事项。

    Args:
        repo_name: 仓库名称（不含 owner）
        tag: 版本标签

    Returns:
        是否创建成功
    """
    title = f"{repo_name} - {tag}"
    content = "GitHub release monitor"
    start_datetime = datetime.now(TIMEZONE).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    token = config.TICKTICK_ACCESS_TOKEN
    project_id = config.TICKTICK_PROJECT_ID
    if not token or not project_id:
        logger.warning("TickTick 配置缺失，跳过创建待办")
        return False

    task_data = {
        "title": title,
        "content": content,
        "projectId": project_id,
        "startDate": start_datetime.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "isAllDay": True,
        "timeZone": "Asia/Shanghai",
    }
    headers = {
        "Authorization": f"Bearer {token}",
    }

    logger.info(f"创建待办: {title} @ {start_datetime.date().isoformat()}")

    try:
        resp = requests.post(
            TICKTICK_API_URL,
            json=task_data,
            headers=headers,
            proxies=config.get_proxies(),
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"待办创建成功: {result.get('id')}")
        return True
    except requests.RequestException as e:
        logger.error(f"待办创建失败: {e}")
        return False
