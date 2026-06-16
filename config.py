from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 下载目录
DOWNLOAD_DIR = Path(__file__).parent / "downloads"

# LLM 设置：指定主模型和 fallback 模型（对应 llms.py 中的变量名）
LLM_PRIMARY = "llm_mimo"
LLM_FALLBACK = "llm_ds"
