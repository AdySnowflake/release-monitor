# release-monitor

`release-monitor` 定时检查 GitHub 仓库的最新 Release，使用 OpenAI 兼容模型按规则选择合适的 asset，下载文件，并按需创建 TickTick 待办或移动文件。处理最终失败时，程序会汇总本轮错误、尝试生成 AI 错误报告，并通过飞书自定义机器人发送通知。

程序每次只执行一轮检查，适合由 cron 或其他任务调度器定时运行。

## 处理流程

```text
读取 repo_rules.json
        │
        ▼
逐个查询 GitHub 最新 Release（单仓库失败不阻断其他仓库）
        │
        ├─ tag 与 last_tag 相同 ──────────────► 跳过
        │
        ▼
主 LLM 按规则选择 asset（失败时重试）
        │
        ├─ 主 LLM 最终失败 ─► 备用 LLM（可选，同样重试）
        │
        ▼
校验下载地址确实来自 Release assets
        │
        ▼
下载到 downloads/
        │
        ├─ 创建 TickTick 待办（可选、非阻断）
        │
        └─ 移动到目标目录（可选）
        │
        ▼
成功后更新 last_tag
```

一轮运行中出现最终失败时：

```text
汇总 GitHub 检查失败和 Release 处理失败
        │
        ▼
尝试让主/备用 LLM 生成错误报告
        │
        ├─ 分析成功 ─► 可读报错 + AI 分析 ─► 飞书告警
        │
        └─ 分析失败 ─► 可读报错，无 AI 内容 ─► 飞书告警
```

AI 错误分析与飞书发送是两条解耦的路径。即使 LLM 因 API Key 余额耗尽、鉴权失败或服务不可用而无法分析，程序仍会直接发送原始错误通知。文件选择阶段已经确认不可用的模型不会被错误分析再次调用。

## 环境要求

- Python 3.12 或更高版本
- [uv](https://docs.astral.sh/uv/)
- 一个 OpenAI 兼容的聊天模型接口
- 可选：GitHub Token、TickTick、飞书自定义机器人

## 快速开始

```bash
git clone <repository-url>
cd release-monitor

cp .env.example .env
cp repo_rules.example.json repo_rules.json

# 编辑 .env 和 repo_rules.json 后安装并运行
uv sync --locked
uv run --locked python main.py
```

运行日志会写入 `logs/pipeline_YYYYMMDD_HHMMSS.log`，下载文件默认保存在 `downloads/`。

## 配置 LLM

主模型用于选择 Release asset，也是错误分析的首选模型：

```dotenv
LLM_PRIMARY_BASE_URL=https://api.example.com/v1
LLM_PRIMARY_API_KEY=sk-your-key
LLM_PRIMARY_MODEL=your-model
# 单次请求超时，默认 30 秒
LLM_REQUEST_TIMEOUT_SECONDS=30
```

`LLM_PRIMARY_API_KEY` 与 `LLM_PRIMARY_MODEL` 必填。使用服务商默认地址时可以省略 `LLM_PRIMARY_BASE_URL`。

备用模型可选。建议使用不同的 API Key 或服务商，使主接口发生配额、网络或服务故障时仍有回退能力：

```dotenv
LLM_FALLBACK_BASE_URL=https://api.example.com/v1
LLM_FALLBACK_API_KEY=sk-your-fallback-key
LLM_FALLBACK_MODEL=your-fallback-model
```

备用模型只有同时填写 API Key 和模型名时才启用；配置不完整时按未启用处理。

文件选择时，每个模型默认调用 3 次：首次调用加 2 次指数退避重试。OpenAI 客户端自身的重试已关闭，主模型全部失败后才会切换备用模型。最终失败时记录最后一次异常。

所有环境变量只由 `config.py` 读取。`llms.py` 仅负责按角色惰性创建和缓存客户端，不包含用户专属 Provider 配置。

## 配置监控规则

监控清单位于 `repo_rules.json`：

```json
{
  "owner/repo-name": {
    "extension": ".apk",
    "include": ["arm64-v8a"],
    "exclude": ["legacy"],
    "last_tag": null
  }
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `extension` | string | 目标文件扩展名，例如 `.apk`、`.ipa`、`.exe` |
| `include` | string[] | 文件名应包含的关键词 |
| `exclude` | string[] | 文件名不能包含的关键词 |
| `last_tag` | string/null | 最后成功处理的 tag，由程序自动维护 |

仓库键必须采用 `owner/repo` 格式。`extension`、`include` 和 `exclude` 可以省略；规则会连同 GitHub 返回的 assets 一起交给 LLM 判断。

程序比较的是 GitHub “latest release”的 tag 与 `last_tag` 是否相同，不进行语义化版本排序。首次运行时 `last_tag` 可设为 `null`，此时会处理当前最新 Release。

`repo_rules.json` 缺失或 JSON 无效会终止本轮检查，并在飞书已配置时发送错误通知；空对象 `{}` 表示暂时没有需要监控的仓库。

需要整理规则文件顺序时运行：

```bash
uv run --locked python sort_repo_rules.py
```

该脚本按仓库名（`/` 后面的部分）进行不区分大小写的排序，不会改动规则内容。

## 配置飞书错误通知

在飞书群中添加启用“签名校验”的自定义机器人，然后将 Webhook 和签名密钥写入当前项目的 `.env`：

```dotenv
FEISHU_ENABLED=true
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...
FEISHU_SIGNING_SECRET=your-signing-secret
```

飞书通知由 `feishu_notifier.py` 使用项目已有的 `requests` 依赖实现，消息类型为交互式卡片。

告警使用红色卡片，标题固定为 `Release Monitor 告警`，每轮运行只汇总发送一条：

- 发生时间；
- 故障仓库和 tag；
- 以代码文本框显示由失败发生处传递的最终错误日志；
- AI 给出的分析内容（仅分析成功时）。

告警不在通知层翻译错误码或生成错误描述，不定义程序中不存在的严重级别或运行状态，也不会展示重试次数、内部错误码或 JSON。错误记录会提供给 AI 分析，本地日志保留完整异常。

以下情况不会阻止错误通知：

- 主模型无法生成错误分析；
- 主、备用模型均无法生成错误分析；
- 没有配置备用模型。

只有 `FEISHU_ENABLED=true` 时才启用飞书通知，此时 Webhook 和签名密钥必须同时填写。未启用时不会额外调用 LLM 生成错误报告。Webhook 无效或通知请求失败时，程序会记录错误，但无法再通过飞书报告自身的发送故障。

## 其他可选配置

### GitHub Token

```dotenv
GITHUB_TOKEN=github_pat_your-token
```

未配置时使用 GitHub 匿名 API；配置后使用认证请求，可降低匿名接口速率限制的影响。

### HTTP 代理

```dotenv
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

代理用于 GitHub API、文件下载、TickTick 和飞书 Webhook 请求。

### TickTick 待办

```dotenv
TODO_ENABLED=true
TICKTICK_ACCESS_TOKEN=your-access-token
TICKTICK_PROJECT_ID=your-project-id
```

启用后，下载完成会创建一个上海时区当天的全天待办。TickTick 创建失败只记录日志，不会让 Release 处理失败，也不会阻止文件移动或 `last_tag` 更新。

### 移动下载文件

```dotenv
MOVE_TARGET_DIR=/path/to/target
```

配置后，下载成功的文件会移动到目标目录。目标目录不存在时自动创建；同名目标文件已存在时拒绝覆盖，并将本次 Release 标记为失败。此时 `last_tag` 不会更新，下载文件保留在 `downloads/`，下一轮会重新处理该 Release。

## 成功与失败判定

只有以下步骤都成功时才更新对应仓库的 `last_tag`：

1. 获取到 Release assets；
2. LLM 成功选择文件；
3. LLM 返回的 URL 确实属于当前 Release；
4. 文件下载成功；
5. 配置了文件移动时，移动成功。

TickTick 是非阻断功能，不参与成功判定。飞书错误通知也不改变 Release 的处理结果。

一轮中某个仓库失败不会阻止其他仓库继续处理。GitHub 403、网络失败、无效响应及后续处理错误都会汇总进入错误分析和通知流程；仓库确实没有 Release 的 404 响应仍视为正常跳过。

## 定时运行

先手动运行一次，确认环境配置、目录权限和日志均正常。然后使用 `crontab -e` 添加任务，例如每 30 分钟执行一次：

```cron
PATH=/home/your-user/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

*/30 * * * * cd /path/to/release-monitor && flock -n /tmp/release-monitor.lock uv run --locked python main.py >> /path/to/release-monitor/logs/cron.log 2>&1
```

使用 `command -v uv` 确认 `uv` 的实际路径，并按需调整 cron 的 `PATH`。`flock -n` 会在上一轮仍未结束时直接跳过新一轮，避免重复下载、重复待办和并发写入规则文件。

## 项目结构

```text
main.py                  # 入口；汇总本轮失败并触发分析和通知
github_poller.py         # 检查各仓库的最新 Release
pipeline.py              # 文件选择、下载、待办和移动编排
ai_file_selector.py      # LLM 文件选择、重试与备用模型回退
error_analysis.py        # 将全部失败记录交给 LLM 生成错误报告
error_notification.py    # 构造并发送汇总错误通知
feishu_notifier.py       # 飞书卡片、签名与 Webhook 请求
llms.py                  # 按角色惰性创建 LLM 客户端
downloader.py            # 流式下载和临时文件处理
file_transfer.py         # 可选的下载文件移动
ticktick.py              # 可选的 TickTick 待办
repo_rules.py            # 规则读取、保存与 last_tag 更新
sort_repo_rules.py       # 整理 repo_rules.json 顺序
config.py                # 从环境变量生成运行配置
.env.example             # 环境变量模板
repo_rules.example.json  # 仓库规则模板
```

## 安全说明

- `.env`、`repo_rules.json`、`downloads/` 和 `logs/` 已加入 `.gitignore`。
- 不要把 LLM API Key、GitHub Token、TickTick Token、飞书 Webhook 或签名密钥提交到版本库。
- 错误分析可能会把第三方 API 异常消息发送给已配置的 LLM；飞书通知会包含最终错误摘要和可选的 AI 分析，请选择合适的模型服务与飞书群。

## 许可证

[MIT License](LICENSE)
