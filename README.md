# release-monitor

通过 GitHub API 监控仓库的最新 Release，按仓库规则选择对应平台的发布文件并下载。

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
创建 TickTick 待办（可选）
       ↓
移动到指定目录（可选）
```

每次运行会遍历 `repo_rules.json` 中的仓库。发现新版本后，程序获取 Release assets，按照 `extension`、`include` 和 `exclude` 规则选择文件并下载。

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 LLM API Key、模型名等

# 2. 安装依赖
uv sync

# 3. 配置业务参数
cp config.example.py config.py

# 4. 配置监控仓库
cp repo_rules.example.json repo_rules.json
# 编辑 repo_rules.json

# 5. 运行
python main.py
```

## 配置

### 环境变量

`.env` 用于存放 API Key、Token 等敏感信息：

```dotenv
LLM_PRIMARY_BASE_URL=https://api.example.com/v1
LLM_PRIMARY_API_KEY=your-key
LLM_PRIMARY_MODEL=your-model
```

备用模型为可选配置，需要时填写对应环境变量：

```dotenv
LLM_FALLBACK_BASE_URL=https://api.example.com/v1
LLM_FALLBACK_API_KEY=your-key
LLM_FALLBACK_MODEL=your-fallback-model
```

可选配置：

```dotenv
# 配置后使用认证请求；不配置则使用匿名请求
GITHUB_TOKEN=github_pat_your-token

HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

TODO_ENABLED=true
TICKTICK_ACCESS_TOKEN=your-access-token
TICKTICK_PROJECT_ID=your-project-id

# 配置后在 TickTick 处理完成后移动下载文件
MOVE_TARGET_DIR=/path/to/target
```

`GITHUB_TOKEN` 不是必填项。未配置时使用 GitHub 匿名 API；配置后自动在请求中添加 Bearer Token。

### 业务配置

`config.py` 管理下载目录、文件转移目录和 TickTick 开关。首次使用时从示例复制：

```bash
cp config.example.py config.py
```

具体 Provider 只在 `.env` 中配置，不需要修改项目代码。程序在使用时才初始化
主模型；填写任意 `LLM_FALLBACK_*` 配置后，备用模型也只会在主模型调用失败时
初始化。

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
python sort_repo_rules.py
```

脚本固定处理项目目录下的 `repo_rules.json`，只调整仓库条目的顺序，不会修改各仓库的规则内容。

## 定时运行

程序执行一轮检查后退出，可交给 cron 或系统任务计划定时调用。

Linux/macOS 示例：

```bash
# 每小时运行
0 * * * * cd /path/to/release-monitor && python main.py

# 每 15 分钟运行
*/15 * * * * cd /path/to/release-monitor && python main.py
```

## 项目结构

```text
main.py                 # 程序入口
github_poller.py        # 遍历监控仓库并检查最新 Release
pipeline.py             # 资产选择、下载和待办编排
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
