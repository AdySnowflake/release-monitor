import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 下载目录
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", Path(__file__).parent / "downloads"))

# DeepSeek
DS_BASE_URL = os.getenv("DS_BASE_URL", "https://api.deepseek.com/v1")
DS_API_KEY = os.getenv("DS_API_KEY")
DS_MODEL = os.getenv("DS_MODEL", "deepseek-chat")

# MiMo
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.xiaoai.mi.com/v1")
MIMO_API_KEY = os.getenv("MIMO_API_KEY")
MIMO_MODEL = os.getenv("MIMO_MODEL", "MiMo-7B-RL")
