import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

import config
from error_analysis import generate_error_report
from error_notification import send_error_notification
from github_poller import check_new_releases
from pipeline import run_release
from repo_rules import update_repo_tag

NOISY_LOGGERS = ("httpcore", "httpx", "openai", "urllib3")


def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    # 文件处理器（UTF-8，DEBUG 级别，带时间戳的文件名）
    timestamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        log_dir / f"pipeline_{timestamp}.log",
        encoding="utf-8",
    )
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

    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def _notify_failures(error_records: list[dict]) -> None:
    """先尝试生成 AI 报告，再发送不依赖分析成功与否的通知。"""
    if not error_records:
        return
    if not config.FEISHU_ENABLED:
        logger.info("飞书通知未启用")
        return
    if not config.FEISHU_WEBHOOK_URL or not config.FEISHU_SIGNING_SECRET:
        logger.error("飞书配置不完整，跳过错误通知")
        return

    llm_failed = any(
        record.get("error") in {"llm_failed", "all_llms_failed"}
        for record in error_records
    )
    ai_report = None
    if not llm_failed:
        ai_report = generate_error_report(error_records)
    send_error_notification(error_records, ai_report)


def main():
    """遍历仓库，通过 GitHub API 检查并处理新 release。"""
    setup_logging()
    logger.info("检查 GitHub 仓库的新 release")

    try:
        new_releases, failures = check_new_releases()
    except Exception as error:
        logger.exception("检查 GitHub release 失败")
        _notify_failures(
            [
                {
                    "stage": "release_check",
                    "error": type(error).__name__,
                    "message": str(error),
                }
            ]
        )
        return

    if not new_releases:
        logger.info("未发现可处理的新 release")
        _notify_failures(failures)
        return

    logger.info(f"发现 {len(new_releases)} 个新 release")

    for release in new_releases:
        try:
            logger.info(f"处理: {release.owner}/{release.repo} @ {release.tag}")
            result = run_release(
                release.owner, release.repo, release.tag, release.assets
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

            if result.get("success") == 1:
                update_repo_tag(release.owner, release.repo, release.tag)
            else:
                logger.error(
                    f"处理 {release.owner}/{release.repo} @ {release.tag} 未成功，"
                    "保留 last_tag 以便下次重试"
                )
                failures.append(
                    {
                        "stage": "release_processing",
                        "repository": f"{release.owner}/{release.repo}",
                        "tag": release.tag,
                        "error": result.get("error", "processing_failed"),
                        "error_log": result.get("error_log"),
                    }
                )
        except Exception as e:
            logger.exception(f"处理 {release.owner}/{release.repo} 失败")
            failures.append(
                {
                    "stage": "release_processing",
                    "repository": f"{release.owner}/{release.repo}",
                    "tag": release.tag,
                    "error": type(e).__name__,
                    "message": str(e),
                }
            )

    _notify_failures(failures)


if __name__ == "__main__":
    main()
