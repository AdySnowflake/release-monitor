import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def scan_emails(email_dir: Path) -> list[Path]:
    """扫描指定目录，返回所有 .eml 文件列表。

    Args:
        email_dir: 邮件扫描目录

    Returns:
        .eml 文件路径列表，目录不存在或为空时返回空列表
    """
    if not email_dir.exists():
        logger.warning(f"邮件目录不存在: {email_dir}")
        return []

    if not email_dir.is_dir():
        logger.warning(f"邮件路径不是目录: {email_dir}")
        return []

    eml_files = sorted(email_dir.glob("*.eml"))
    logger.info(f"扫描到 {len(eml_files)} 个 .eml 文件")
    return eml_files
