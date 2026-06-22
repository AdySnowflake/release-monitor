import logging
from pathlib import Path

import requests

from config import DOWNLOAD_DIR, get_proxies

logger = logging.getLogger(__name__)


def download_file(url: str, download_dir: Path | None = None) -> Path | None:
    """下载文件到指定目录。

    Args:
        url: 下载链接
        download_dir: 下载目录，默认 ./downloads/

    Returns:
        Path: 下载后的文件路径，失败返回 None
    """
    download_dir = download_dir or DOWNLOAD_DIR
    download_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1]
    filepath = download_dir / filename

    # 重复文件检查
    if filepath.exists():
        logger.info(f"文件已存在: {filepath}")
        return filepath

    logger.info(f"开始下载: {url}")
    resp = requests.get(url, stream=True, proxies=get_proxies())
    resp.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"下载完成: {filepath}")
    return filepath
