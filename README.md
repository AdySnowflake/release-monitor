# release-monitor

监控 GitHub Release，通过 AI 自动筛选并下载对应平台的发布文件。

支持两种运行模式：
- **邮件模式**：扫描 `.eml` 文件，解析邮件获取 Release 信息
- **API 模式**：直接通过 GitHub API 检查仓库新版本

## 工作流程

```
邮件模式: .eml 邮件 → 解析正文 → AI 提取 Release 信息 → GitHub API 获取资源列表
API 模式: repo_rules 遍历 → GitHub API 检查新版本 → 获取资源列表
                                                                    ↓
                                                AI 根据 repo_rules 选择文件 → 下载到 downloads/
                                                                                 ↓
                                                                   创建 TickTick 待办（可选）
```

### AI 架构

每个 AI 调用都有三层容错：指数退避重试 → 自动切换 LLM → Analysis AI 诊断修复。

LLM 配置在 `.env` 中，支持任何 OpenAI 兼容 API。

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 安装依赖
uv sync

# 3. 配置业务参数
cp config.example.py config.py
# 编辑 config.py 设置运行模式（MODE）等

# 4. 配置下载规则
cp repo_rules.example.json repo_rules.json
# 编辑 repo_rules.json 添加你需要监控的仓库

# 5. 运行
python main.py
```

## 配置说明

### 环境变量 (.env) vs 业务配置 (config.py)

| 维度 | `.env` | `config.py` |
|------|--------|-------------|
| **存放内容** | 敏感信息（API Key、Token） | 业务配置（模式、目录、超时） |
| **是否提交 Git** | ❌ 不提交 | ❌ 不提交（仅提交 `config.example.py`） |
| **示例** | `MIMO_API_KEY=xxx` | `MODE = "api"` |
| **加载方式** | `python-dotenv` | 直接 `import config` |

**原则**：泄露会造成安全风险 → `.env`；否则 → `config.py`。

### 业务配置 (config.py)

```python
# 运行模式: "email" | "api"
MODE = "api"

# 邮件扫描目录（仅 email 模式）
EMAIL_DIR = "./emails/"

# 下载目录
DOWNLOAD_DIR = Path(__file__).parent / "downloads"

# LLM 设置
LLM_PRIMARY = "llm_mimo"
LLM_FALLBACK = "llm_ds"

# 待办模块（可选）
TODO_ENABLED = False
TICKTICK_ACCESS_TOKEN = os.getenv("TICKTICK_ACCESS_TOKEN")
TICKTICK_PROJECT_ID = os.getenv("TICKTICK_PROJECT_ID")
```

首次使用可从示例文件复制：

```bash
cp config.example.py config.py
```

### 仓库规则 (repo_rules.json)

`repo_rules.json` 包含你的个人下载偏好，**不会被提交到 Git**。

格式示例：

```json
{
  "owner/repo": {
    "extension": ".apk",
    "include": ["arm64-v8a"],
    "exclude": ["legacy"]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `extension` | string | 目标文件扩展名，如 `.apk`、`.ipa`、`.exe` |
| `include` | string[] | 文件名必须包含的关键词 |
| `exclude` | string[] | 文件名不能包含的关键词 |

所有字段均可选，规则会作为约束传给 AI 文件选择器。

首次使用可从示例文件复制：

```bash
cp repo_rules.example.json repo_rules.json
```

## 运行模式

### 邮件模式 (MODE = "email")

扫描指定目录中的 `.eml` 文件，解析邮件获取 Release 信息并下载。

```bash
# 设置 config.py 中 MODE = "email"
python main.py
```

### API 模式 (MODE = "api")

遍历 `repo_rules.json` 中的仓库，通过 GitHub API 检查新版本并下载。

```bash
# 设置 config.py 中 MODE = "api"
python main.py
```

**注意**：API 模式需要 `repo_rules.json` 中的仓库使用 `owner/repo` 格式。

## 定时调度

程序单次执行完毕后退出，可通过外部定时任务实现自动调度。

### Windows 任务计划

1. 打开「任务计划程序」
2. 创建基本任务
3. 设置触发器（如每小时）
4. 操作：启动程序
   - 程序：`python`
   - 参数：`main.py`
   - 起始目录：`E:\dev\release-monitor`

### Linux/macOS (cron)

```bash
# 编辑 crontab
crontab -e

# 每小时运行一次（API 模式）
0 * * * * cd /path/to/release-monitor && python main.py

# 每 15 分钟运行一次（API 模式）
*/15 * * * * cd /path/to/release-monitor && python main.py
```

## 项目结构

```
main.py                 # 入口：根据 config.MODE 分发到不同执行路径
pipeline.py             # 编排：邮件模式完整流程 / API 模式跳过邮件解析
config.py               # 业务配置（运行模式、目录、LLM 设置）
config.example.py       # 配置示例（提交到 Git）
email_scanner.py        # 扫描目录中的 .eml 文件
github_poller.py        # 遍历仓库检查新 release
llms.py                 # LLM Provider 定义
email_parser.py         # 解析 .eml 邮件正文
ai_url_extractor.py     # 从邮件提取 Release 信息
ai_file_selector.py     # 根据规则选择目标文件
github_api.py           # 调用 GitHub Releases API
repo_rules.py           # 加载并匹配仓库规则（含版本跟踪）
repo_rules.json         # 个人仓库规则（Git 忽略）
repo_rules.example.json # 规则示例文件
downloader.py           # 下载文件（进度条 + 去重）
todo.py                 # 创建 TickTick 待办（可选）
error_handler.py        # 重试、回退、AI 诊断
```

## 依赖

- Python 3.12+
- LangChain + LangChain-OpenAI
- Requests
- python-dotenv

## 许可证

[MIT License](LICENSE)
