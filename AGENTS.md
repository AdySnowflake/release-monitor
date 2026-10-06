## 项目管理
- 本项目使用 uv 管理 Python、虚拟环境和依赖
- 添加依赖：使用 `uv add <package>`
- 安装锁定依赖：使用 `uv sync --locked`
- 运行项目：使用 `uv run --locked python main.py`
- 配置环境：`cp .env.example .env`，然后填入 API Key
