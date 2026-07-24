import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from pipeline import run_release
from github_poller import check_new_releases
from repo_rules import update_repo_tag


def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    # 文件处理器（UTF-8，DEBUG 级别，带时间戳的文件名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(log_dir / f"pipeline_{timestamp}.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # 控制台处理器（INFO 级别）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


setup_logging()

logger = logging.getLogger(__name__)


def main():
    """遍历仓库，通过 GitHub API 检查并处理新 release。"""
    logger.info("检查 GitHub 仓库的新 release")

    new_releases = check_new_releases()
    if not new_releases:
        logger.info("未发现新 release")
        return

    logger.info(f"发现 {len(new_releases)} 个新 release")

    for release in new_releases:
        try:
            logger.info(f"处理: {release.owner}/{release.repo} @ {release.tag}")
            result = run_release(release.owner, release.repo, release.tag, release.assets)
            print(json.dumps(result, ensure_ascii=False, indent=2))

            if result.get("success") == 1:
                update_repo_tag(release.owner, release.repo, release.tag)
            else:
                logger.error(
                    f"处理 {release.owner}/{release.repo} @ {release.tag} 未成功，"
                    "保留 last_tag 以便下次重试"
                )
        except Exception as e:
            logger.error(f"处理 {release.owner}/{release.repo} 失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
