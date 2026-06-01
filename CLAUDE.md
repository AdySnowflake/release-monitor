## 项目管理
- 本项目使用 uv 管理依赖，venv 通过 `python -m venv .venv` 创建
- 安装依赖：将依赖写入 `pyproject.toml`，然后执行 `uv sync`
- 运行项目：使用 `.venv/Scripts/python` 或激活 venv 后直接调用 `python`
- 配置环境：`cp .env.example .env`，然后填入 API Key
