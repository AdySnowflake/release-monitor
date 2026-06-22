import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from pipeline import run, run_release
from email_scanner import scan_emails
from github_poller import check_new_releases
from repo_rules import update_repo_tag
import config


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
    mode = getattr(config, "MODE", None)

    if mode == "email":
        _run_email_mode()
    elif mode == "api":
        _run_api_mode()
    else:
        logger.error(f"无效的 MODE 配置: {mode!r}，请在 config.py 中设置 MODE = 'email' 或 'api'")
        sys.exit(1)


def _run_email_mode():
    """邮件模式：扫描目录中的 .eml 文件并处理。"""
    email_dir = Path(getattr(config, "EMAIL_DIR", "./emails/"))
    logger.info(f"邮件模式，扫描目录: {email_dir}")

    eml_files = scan_emails(email_dir)
    if not eml_files:
        logger.info("未发现 .eml 文件")
        return

    logger.info(f"发现 {len(eml_files)} 个 .eml 文件")

    for eml_path in eml_files:
        try:
            logger.info(f"处理: {eml_path.name}")
            result = run(eml_path)
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # 处理完成后删除 .eml 文件
            eml_path.unlink()
            logger.info(f"已删除: {eml_path.name}")
        except Exception as e:
            logger.error(f"处理 {eml_path.name} 失败: {e}", exc_info=True)


def _run_api_mode():
    """API 模式：遍历仓库检查新 release 并处理。"""
    logger.info("API 模式，检查仓库新 release")

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

            # 更新 last_tag（无论成功失败，避免永久失败无限重试）
            update_repo_tag(release.owner, release.repo, release.tag)
        except Exception as e:
            logger.error(f"处理 {release.owner}/{release.repo} 失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
