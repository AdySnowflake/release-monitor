import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 下载目录
DOWNLOAD_DIR = Path(__file__).parent / "downloads"

# 代理设置（从 .env 读取，可选）
HTTP_PROXY = os.getenv("HTTP_PROXY")
HTTPS_PROXY = os.getenv("HTTPS_PROXY")

# GitHub API Token（可选；未配置时使用匿名请求）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# LLM 设置：指定主模型和 fallback 模型（对应 llms.py 中的变量名）
LLM_PRIMARY = "llm_mimo"
LLM_FALLBACK = "llm_ds"

# 待办模块（下载完成后自动创建待办，可选）
TODO_ENABLED = os.getenv("TODO_ENABLED", "false").lower() == "true"

# TickTick API（启用 TODO_ENABLED 后必填）
TICKTICK_ACCESS_TOKEN = os.getenv("TICKTICK_ACCESS_TOKEN")
TICKTICK_PROJECT_ID = os.getenv("TICKTICK_PROJECT_ID")


def get_proxies() -> dict | None:
    """返回 requests 的 proxies 参数，未配置时返回 None。"""
    if HTTP_PROXY or HTTPS_PROXY:
        return {"http": HTTP_PROXY, "https": HTTPS_PROXY}
    return None


def get_github_headers() -> dict[str, str]:
    """返回 GitHub API 请求头，配置 Token 时自动启用认证。"""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers
