# release-monitor

通过 GitHub API 监控仓库的最新 Release，使用 LLM 按仓库规则选择并下载发布文件。下载完成后可选创建 TickTick 待办，也可将文件移动到指定目录。

## 工作流程

```text
repo_rules.json
       ↓
GitHub API 检查最新 Release
       ↓
与 last_tag 比较
       ↓
AI 根据仓库规则选择 asset
       ↓
下载到 downloads/
       ↓
创建 TickTick 待办（可选，失败不影响后续处理）
       ↓
移动到指定目录（可选，不依赖 TickTick）
       ↓
更新 last_tag
```

每次运行会遍历 `repo_rules.json` 中的仓库。发现新版本后，程序获取 Release assets，按照 `extension`、`include` 和 `exclude` 规则选择文件并下载。只有文件选择、下载和可选的文件移动全部成功后，才会更新 `last_tag`。

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 LLM API Key、模型名等

# 2. 安装依赖
uv sync

# 3. 配置监控仓库
cp repo_rules.example.json repo_rules.json
# 编辑 repo_rules.json

# 4. 运行
uv run --locked python main.py
```

## 配置

### 环境变量

`.env` 用于存放 API Key、Token 等敏感信息，不会提交到 Git。主模型是必需配置：

```dotenv
LLM_PRIMARY_BASE_URL=https://api.example.com/v1
LLM_PRIMARY_API_KEY=your-key
LLM_PRIMARY_MODEL=your-model
```

`LLM_PRIMARY_API_KEY` 和 `LLM_PRIMARY_MODEL` 必填。使用自定义的 OpenAI 兼容接口时还需要填写 `LLM_PRIMARY_BASE_URL`。

备用模型不是必需的。不需要回退时不要填写；需要时完整配置：

```dotenv
LLM_FALLBACK_BASE_URL=https://api.example.com/v1
LLM_FALLBACK_API_KEY=your-key
LLM_FALLBACK_MODEL=your-fallback-model
```

可选配置：

```dotenv
# 推荐配置，避免 GitHub 匿名 API 的低速率限制
GITHUB_TOKEN=github_pat_your-token

HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

TODO_ENABLED=true
TICKTICK_ACCESS_TOKEN=your-access-token
TICKTICK_PROJECT_ID=your-project-id

# 与 TickTick 相互独立；配置后移动下载完成的文件
MOVE_TARGET_DIR=/path/to/target
```

各可选模块彼此独立：

- `GITHUB_TOKEN`：不配置时使用 GitHub 匿名 API；配置后使用认证请求。
- TickTick：只有 `TODO_ENABLED=true` 时启用，同时需要 Token 和项目 ID。待办是上海时区当天的全天任务；创建失败只记录警告，不阻止文件移动。
- 文件移动：只要配置 `MOVE_TARGET_DIR` 就会启用，与 TickTick 是否启用或成功无关。目标目录不存在时自动创建，不会覆盖同名文件。

主模型只在需要选择文件时初始化；备用模型只在主模型多次调用失败后初始化。Provider、模型和密钥都通过 `.env` 配置，不需要修改 `llms.py` 或 `config.py`。

如果文件移动失败，本轮不会更新对应仓库的 `last_tag`，下载文件会保留在 `downloads/`，下次定时运行时会再次尝试处理该 Release。

### 仓库规则

`repo_rules.json` 是监控清单，不提交到 Git：

```json
{
  "owner/repo": {
    "extension": ".apk",
    "include": ["arm64-v8a"],
    "exclude": ["legacy"],
    "last_tag": "v1.0.0"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `extension` | string | 目标文件扩展名，如 `.apk`、`.ipa`、`.exe` |
| `include` | string[] | 文件名必须包含的关键词 |
| `exclude` | string[] | 文件名不能包含的关键词 |
| `last_tag` | string | 最后成功处理的 Release tag，由程序自动更新 |

`extension`、`include` 和 `exclude` 均可省略。首次使用时从示例复制：

```bash
cp repo_rules.example.json repo_rules.json
```

仓库名必须使用 `owner/repo` 格式。

编辑完成后，可以按仓库名（`/` 后面的部分）进行不区分大小写的排序：

```bash
uv run --locked python sort_repo_rules.py
```

脚本固定处理项目目录下的 `repo_rules.json`，只调整仓库条目的顺序，不会修改各仓库的规则内容。

## 定时运行

程序执行一轮检查后退出，可交给 cron 或系统任务计划定时调用。先手动运行一次，确认配置有效并创建 `logs/` 目录。

使用 `crontab -e` 添加以下配置，每半小时运行一次：

```cron
PATH=/home/your-user/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

*/30 * * * * cd /path/to/release-monitor && uv run --locked python main.py >> /path/to/release-monitor/logs/cron.log 2>&1
```

如果 `uv` 不在 `~/.local/bin`，使用 `command -v uv` 查到实际位置并相应调整 `PATH`。每次运行的详细日志保存在 `logs/pipeline_*.log`，cron 汇总输出保存在 `logs/cron.log`。

## 项目结构

```text
main.py                 # 程序入口
github_poller.py        # 遍历监控仓库并检查最新 Release
pipeline.py             # 资产选择、下载、待办和文件移动编排
github_api.py           # GitHub Releases API
repo_rules.py           # 加载仓库规则并维护 last_tag
sort_repo_rules.py      # 按仓库名整理监控规则
ai_file_selector.py     # 根据规则选择 Release asset
llms.py                 # 通用 LLM 客户端创建
downloader.py           # 文件下载
ticktick.py             # TickTick 待办（可选）
file_transfer.py        # 下载文件转移（可选）
config.example.py       # 业务配置示例
repo_rules.example.json # 监控规则示例
```

## 依赖

- Python 3.12+
- LangChain + LangChain-OpenAI
- Requests
- python-dotenv

## 许可证

[MIT License](LICENSE)
