"""将下载完成的文件移动到用户配置的目标目录。"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def move_downloaded_file(filepath: Path, target_dir: Path) -> Path | None:
    """移动文件到目标目录，成功返回新路径，失败返回 None。"""
    source = Path(filepath)
    target = Path(target_dir).expanduser()

    if not source.is_file():
        logger.error(f"待转移文件不存在: {source}")
        return None

    try:
        target.mkdir(parents=True, exist_ok=True)
        destination = target / source.name

        if destination.resolve() == source.resolve():
            logger.info(f"文件已位于目标目录: {source}")
            return source
        if destination.exists():
            logger.error(f"目标文件已存在，拒绝覆盖: {destination}")
            return None

        moved_path = Path(shutil.move(str(source), str(destination)))
    except (OSError, shutil.Error) as error:
        logger.error(f"文件转移失败: {source} → {target}: {error}")
        return None

    logger.info(f"文件转移完成: {source} → {moved_path}")
    return moved_path
