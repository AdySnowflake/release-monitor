import email
import logging
from email import policy
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_eml(file_path: Path) -> str:
    """从 .eml 文件中提取 text/plain 正文。"""
    with open(file_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            content = part.get_content()
            logger.info(f"已提取邮件正文，长度: {len(content)} 字符")
            return content

    logger.warning(f"邮件中未找到 text/plain 内容: {file_path.name}")
    return ""
