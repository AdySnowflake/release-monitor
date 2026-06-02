# release-monitor

监控 GitHub Release 邮件通知，通过 AI 自动筛选并下载对应平台的发布文件。

## 工作流程

```
.eml 邮件 → 解析正文 → AI 提取 Release 信息 → GitHub API 获取资源列表
                                                        ↓
                                    AI 根据 repo_rules 选择文件 → 下载到 downloads/
```

### AI 架构

| 步骤 | 作用 | 主模型 | 备用模型 |
|------|------|--------|----------|
| 提取 Release URL | 从邮件正文提取 repo、版本、URL | MiMo-7B-RL | DeepSeek Chat |
| 选择目标文件 | 根据规则从资源列表中选择文件 | MiMo-7B-RL | DeepSeek Chat |

每个 AI 调用都有三层容错：指数退避重试 → 自动切换备用 LLM → Analysis AI 诊断修复。

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 安装依赖
uv sync

# 3. 配置下载规则
cp repo_rules.example.json repo_rules.json
# 编辑 repo_rules.json 添加你需要监控的仓库

# 4. 运行
python main.py
```

## 配置说明

### 环境变量 (.env)

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（备用 LLM） |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | DeepSeek 模型名称 |
| `MIMO_API_KEY` | MiMo API Key（主 LLM） |
| `MIMO_BASE_URL` | MiMo API 地址 |
| `MIMO_MODEL` | MiMo 模型名称 |

### 仓库规则 (repo_rules.json)

`repo_rules.json` 包含你的个人下载偏好，**不会被提交到 Git**。

格式示例：

```json
{
  "repo-name": {
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

## 项目结构

```
main.py                 # 入口：设置日志、读取 .eml、调用 pipeline
pipeline.py             # 编排：邮件 → 提取 Release URL → GitHub API → 规则 → 选择文件 → 下载
config.py               # 加载 .env 配置
llm.py                  # 创建 LLM 实例（DeepSeek + MiMo）
email_parser.py         # 解析 .eml 邮件正文
ai_url_extractor.py     # 从邮件提取 Release 信息
ai_file_selector.py     # 根据规则选择目标文件
github_api.py           # 调用 GitHub Releases API
repo_rules.py           # 加载并匹配仓库规则
repo_rules.json         # 个人仓库规则（Git 忽略）
repo_rules.example.json # 规则示例文件
downloader.py           # 下载文件（进度条 + 去重）
error_handler.py        # 重试、回退、AI 诊断
```

## 依赖

- Python 3.12+
- LangChain + LangChain-OpenAI
- Requests
- python-dotenv
