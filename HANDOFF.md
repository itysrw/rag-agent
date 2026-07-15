# 项目完整交接包

更新时间：2026-07-15（America/New_York）
仓库：`D:\2019\rag-agent`
当前阶段：Day 3 已完成并形成本地提交检查点；尚未推送，功能开发已按用户要求暂停。

> 本文档不依赖历史聊天。新工作会话应依次阅读：`HANDOFF.md`、`STATUS.md`、
> `DECISIONS.md`、`README.md`、`AGENTS.md`，再阅读与当前任务直接相关的代码。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- 使用 FastAPI 提供后端接口；
- 支持 PDF、Markdown、TXT 文档上传、解析、切分与元数据存储；
- 使用 Embedding、Qdrant、BM25、RRF 和 Rerank 完成检索增强；
- 使用 OpenAI-compatible LLM 生成带引用的回答；
- 使用 LangGraph 实现检索决策、工具调用和多轮记忆；
- 使用评测数据集量化 source hit、答案质量与延迟；
- 使用 Streamlit 展示，最终通过 Docker Compose 一键启动；
- 形成 README、架构图、评测结果、简历描述和面试讲解材料。

完整 25 天路线以 `PLAN.md` 为唯一计划基线，不得把计划内容写成已完成事实。

### 2. 仓库与环境精确状态

| 项目 | 当前值 |
|---|---|
| 当前分支 | `master` |
| 最近一次有效提交 | `177ad2bfece0fc7cc5c6b347f2b3f4ecfe612c55` |
| 提交摘要 | `feat: complete Day 3 DeepSeek chat integration` |
| 远端 | `origin https://github.com/itysrw/rag-agent.git` |
| 上游跟踪分支 | 未配置；`git branch -vv` 未显示 `[origin/...]` |
| Python | `3.11.15` |
| 虚拟环境 | `D:\2019\rag-agent\.venv` |
| OpenAI Python SDK | `2.45.0` |
| 依赖状态 | `pip check` 输出 `No broken requirements found.` |
| `.env` | 存在；验收过程未读取或输出 Key |
| `.env` Git 状态 | 被 `.gitignore` 忽略，未被 Git 跟踪 |
| 工作区 | 非干净；仅 `HANDOFF.md`、`STATUS.md`、`TODO.md` 有本次交接刷新，均未暂存；业务代码无新增修改 |

Day 3 检查点包含以下实现改动：

- 修改：`.env.example`
- 修改：`README.md`
- 修改：`backend/app/api/chat.py`
- 修改：`backend/app/core/config.py`
- 修改：`backend/requirements.txt`
- 新增：`backend/app/services/llm.py`
- 新增：`backend/tests/test_chat.py`
- 新增：`backend/tests/test_llm.py`

检查点还包含：`HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、
`docs/architecture.md`，以及 `README.md` 中的交接文档入口。

提交 `177ad2b` 创建后，用户要求生成最终交接包，因此当前工作区又修改了
`HANDOFF.md`、`STATUS.md`、`TODO.md`。这三项只更新交接状态，尚未提交；不得把它们误认为业务代码改动。

### 3. 已完成内容

#### Day 1：已提交并完成

- 初始化本地 Git 仓库和 `.gitignore`；
- 配置 GitHub 远端 `origin`；
- 确定项目边界、25 天计划和目录结构；
- README 包含目标架构 Mermaid 图；
- 提交：`751dc40 docs: complete Day 1 project architecture`。

#### Day 2：已提交、已验收

- FastAPI 应用入口：`backend/app/main.py`；
- 路由：`GET /health`、`POST /chat` 占位、`POST /documents/upload` 占位；
- 配置：`backend/app/core/config.py`；
- Loguru：`backend/app/core/logging.py`；
- 请求日志中间件记录 method、path、status、latency，不记录请求正文或密钥；
- `/health` 真实 Uvicorn 验收返回 `200 {"status":"ok"}`；
- Day 2 当时 pytest 为 `1 passed`；
- 提交：`607645d feat: complete Day 2 FastAPI foundation`。

#### Day 3：代码实现和最终验收完成、已本地提交、未推送

- `LLMSettings` 已加入 `backend/app/core/config.py`；
- `LLMClient` 已加入 `backend/app/services/llm.py`；
- 支持非流式 `LLMClient.complete(message)`；
- 支持流式 `LLMClient.stream(message)`，结束或中断时调用流对象的 `close()`；
- `POST /chat` 接受 `{"message":"...","stream":false}` 并返回 JSON；
- `POST /chat` 接受 `{"message":"...","stream":true}` 并返回 SSE；
- SSE 每个增量格式为 `data: {"delta":"..."}\n\n`，完成标记为
  `data: [DONE]\n\n`；
- 未配置 `LLM_API_KEY` 时 `/chat` 返回安全的 `503`，不会影响 `/health`；
- 普通上游错误映射为 `502`，不把供应商原始错误回传给客户端；
- 流中错误用 SSE `event: error` 和通用 `detail` 返回；
- 使用 `SecretStr` 保存 API Key；
- 模拟测试已扩展到成功路径、503/502、SSE error、流关闭和 SecretStr 脱敏；
- 验收前后复测均为 `12 passed, 1 warning`；
- 真实非流式返回 `200`、非空 answer 和 `deepseek-v4-flash`；
- 真实 SSE 返回 `200 text/event-stream; charset=utf-8`、3 个 delta、无 error，并以 `[DONE]` 结束；
- 日志未发现 API Key、Authorization、Bearer 或请求正文；
- 用户已明确授权按 `PLAN.md` 和规范文件同步 Day 3 状态，Day 3 已勾选完成。

### 4. 当前实现状态

#### 4.1 当前接口

| 接口 | 请求 | 当前行为 |
|---|---|---|
| `GET /health` | 无 | `200 {"status":"ok"}`；不依赖 LLM |
| `POST /chat` | `{"message":"...","stream":false}` | 有 Key 时返回 `{"answer":"...","model":"deepseek-v4-flash"}`；无 Key 时 `503` |
| `POST /chat` | `{"message":"...","stream":true}` | 有 Key 时返回 `text/event-stream`；无 Key 时 `503` |
| `POST /documents/upload` | 当前无文件参数 | `501 Not Implemented`；必须留到 Day 4 |
| `GET /docs` | 无 | FastAPI Swagger UI |
| `GET /openapi.json` | 无 | OpenAPI 描述 |

`POST /chat` 中 `message` 会去除首尾空白且至少一个字符；空字符串或纯空白返回 `422`。

#### 4.2 关键文件、类与函数

| 文件 | 关键符号 | 作用 |
|---|---|---|
| `backend/app/main.py` | `lifespan()`、`create_app()`、`app` | 组装 FastAPI、路由和请求日志 |
| `backend/app/api/health.py` | `health()` | 进程存活检查 |
| `backend/app/api/chat.py` | `ChatRequest`、`ChatResponse`、`require_llm_client()`、`stream_sse()`、`chat()` | 非流式与 SSE 聊天接口 |
| `backend/app/api/documents.py` | `upload_document()` | Day 4 占位接口，当前必须保持 `501` |
| `backend/app/core/config.py` | `Settings`、`LLMSettings`、`get_settings()`、`get_llm_settings()` | 应用与 LLM 配置 |
| `backend/app/core/logging.py` | `configure_logging()` | Loguru 控制台日志 |
| `backend/app/services/llm.py` | `OpenAICompatibleClient`、`LLMConfigurationError`、`LLMServiceError`、`LLMClient`、`get_llm_client()` | 供应商无关的兼容客户端 |
| `backend/tests/test_health.py` | `test_health_returns_ok()` | 健康检查测试 |
| `backend/tests/test_chat.py` | 3 个 `test_chat_*` | JSON、SSE、空消息验证 |
| `backend/tests/test_llm.py` | `test_complete_uses_compatible_request_shape()`、`test_stream_yields_only_text_deltas()` | 兼容请求形状和流增量测试 |

#### 4.3 LLM 关键参数

`.env.example` 当前定义：

```dotenv
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=60
LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
```

`LLM_EXTRA_BODY` 是不透明的供应商扩展配置。`LLMClient` 只把它透传给
OpenAI-compatible SDK，不按供应商名称分支。

### 5. 已确认技术决策及原因

完整决策记录见 `DECISIONS.md`。必须保留的核心决策如下：

1. **Day 3 只接 DeepSeek。** 用户已有 DeepSeek 额度，避免同时开通多家 API、扩大范围。
2. **模型使用 `deepseek-v4-flash`。** DeepSeek 官方已说明旧的
   `deepseek-chat`/`deepseek-reasoner` 将于北京时间 2026-07-24 23:59 停用。
3. **Day 3 关闭思考模式。** 普通对话与 SSE 教学阶段不需要额外
   `reasoning_content`；关闭后流解析、延迟和成本更可控。
4. **客户端保持 OpenAI-compatible。** 只通过 API Key、Base URL、模型名和
   `extra_body` 切换供应商，不在 `LLMClient` 中写 DeepSeek 判断。
5. **ChatGPT Plus 不作为后端 API。** Plus 与 OpenAI API 分开计费；当前没有确认 OpenAI API 余额。
6. **Day 6 Embedding 供应商待确认。** 候选为 OpenAI、阿里云百炼/通义千问或本地 BGE；当前禁止提前选择。
7. **Day 18 千问对比为可选亮点，待确认。** 不能在 Day 3 提前接入。

官方参考：

- DeepSeek 首次调用与模型弃用：<https://api-docs.deepseek.com/zh-cn/>
- DeepSeek 思考模式：<https://api-docs.deepseek.com/zh-cn/guides/thinking_mode>
- OpenAI ChatGPT Plus 说明：<https://help.openai.com/en/articles/6950777-what>

### 6. 不可违反的约束

来自 `AGENTS.md`：

- 必须使用 Python 3.11；
- 后端代码必须位于 `backend/`；
- 不得实现超出当前 `PLAN.md` day 的功能；
- 公共函数必须使用类型标注；
- 必须使用 pytest，并在任务完成前运行测试；
- 绝不能提交 `.env` 或 API Key；
- 未经用户明确要求不得修改 `PLAN.md`。

本阶段的额外约束：

- Day 3 已完成真实验收；新会话不得重复消耗额度或重做实现，除非用户明确要求；
- Day 3 建立提交检查点且用户明确要求前，不得开始 Day 4；
- 不得在 Day 3 实现文档上传、Embedding、Qdrant、LangGraph 或千问对比；
- 不得把 DeepSeek Key 写入 `.env.example`、README、测试、日志或 Git；
- `GET /health` 必须继续返回精确的 `{"status":"ok"}`；
- `POST /documents/upload` 必须保持 Day 4 占位 `501`；
- 不要擅自改回即将弃用的 `deepseek-chat` 或 `deepseek-reasoner`；
- 不要重写或删除 Day 3 检查点；后续修改必须从当前提交状态继续。

### 7. 已尝试但失败的方案

1. **在受限环境内直接安装 `openai` SDK：失败。**
   - 命令：`.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt`
   - 失败：访问清华 PyPI 镜像时出现 `[WinError 10013]`，网络套接字被权限阻止。
   - 后续：经用户批准以提升权限重试，成功安装 `openai==2.45.0`；无需再次处理。
2. **pytest 写入 `.pytest_cache`：持续失败但不影响测试。**
   - 错误：`PytestCacheWarning: could not create cache path ... [WinError 5] 拒绝访问`。
   - 测试仍然全部通过；根因待确认，可能是当前受限执行环境的目录权限。
3. **受限沙箱内真实 DeepSeek 调用：失败，但不是代码故障。**
   - 结果：非流式为通用 `502`，流式为 SSE error；日志未泄露凭据。
   - 后续：经批准在沙箱外运行同一脱敏验收，非流式和 SSE 均成功。
4. **PowerShell 独立进程启动验收：失败，但未影响项目。**
   - 原因：当前 Windows 环境同时存在大小写重复的 `Path`/`PATH`，`Start-Process` 构建环境字典失败；旧版和新版 `ProcessStartInfo` 环境属性也不兼容。
   - 后续：改用临时 Python 进程内的 Uvicorn 线程完成真实 HTTP 验收；未创建或修改仓库文件，临时端口已停止监听。
5. **旧模型名方案已否决。**
   - `deepseek-chat`/`deepseek-reasoner` 因临近官方停用而不再使用。
6. **Day 3 同时接入 DeepSeek 与千问方案已否决。**
   - 原因：违反单日范围、增加配置和测试复杂度；千问仅保留为 Day 18 可选对比。

### 8. 当前错误和日志

#### 8.1 当前测试

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

最近结果：

```text
collected 12 items
12 passed, 1 warning
```

通过的测试：

- `backend/tests/test_chat.py::test_chat_returns_complete_response`
- `backend/tests/test_chat.py::test_chat_returns_sse_stream`
- `backend/tests/test_chat.py::test_chat_rejects_blank_message`
- `backend/tests/test_chat.py::test_chat_returns_503_without_llm_configuration`
- `backend/tests/test_chat.py::test_chat_maps_complete_failure_to_502`
- `backend/tests/test_chat.py::test_chat_sends_error_event_after_stream_starts`
- `backend/tests/test_health.py::test_health_returns_ok`
- `backend/tests/test_llm.py::test_complete_uses_compatible_request_shape`
- `backend/tests/test_llm.py::test_stream_yields_only_text_deltas`
- `backend/tests/test_llm.py::test_stream_closes_when_consumer_stops_early`
- `backend/tests/test_llm.py::test_stream_closes_when_upstream_fails`
- `backend/tests/test_llm.py::test_llm_api_key_is_redacted_in_settings_repr`

当前失败测试：无。

当前警告原文：

```text
PytestCacheWarning: could not create cache path
C:\Users\CodexSandboxOffline\.codex\.sandbox\cwd\be1beccfab9cc41a\.pytest_cache\v\cache\nodeids:
[WinError 5] 拒绝访问。
```

较早在仓库直接路径运行时，同一警告指向
`D:\2019\rag-agent\.pytest_cache\v\cache\nodeids`。两者均为缓存写入权限警告，测试本身通过；根因待确认。

#### 8.2 未配置 LLM 时的已确认行为

请求：`POST /chat`，body 为 `{"message":"hello"}`。

```text
503 {"detail":"The language model is not configured."}
```

这是预期安全行为，不是当前代码缺陷。

#### 8.3 当前 Git 行尾警告

`git diff` 对若干文件提示：

```text
LF will be replaced by CRLF the next time Git touches it
```

当前 `core.autocrlf=true`。`git diff --check` 通过；此警告目前非阻断，是否增加
`.gitattributes` 为待确认事项，不得在 Day 3 验收时擅自扩展范围。

### 9. 当前不确定信息

- 用户的 DeepSeek API Key：已由用户保存在本地 `.env`；内容未读取，也不得写入交接包。
- DeepSeek 账户的实际剩余额度：用户表示有额度，具体数值待确认。
- pytest 缓存权限警告在当前验收环境仍出现；根因和是否修复待确认。
- Day 6 Embedding 使用 OpenAI、通义千问还是本地 BGE：待确认。
- Day 18 是否增加千问模型效果/成本对比：待确认。
- 是否给 `master` 设置远端上游并推送 Day 3：待用户决定。

### 10. 待完成任务

唯一当前任务：**保持暂停，等待用户明确选择提交交接刷新、推送 Day 3、开始 Day 4 或继续暂停。**

不得提前开始 Day 4。完整后续顺序见 `TODO.md` 和 `PLAN.md`。

### 11. 下一步具体操作

新会话严格按此顺序执行：

1. 完整阅读本交接包列出的文件，不依赖历史聊天。
2. 只读运行 `git status --short --branch` 和 `git log -1 --oneline`。
3. 预期为分支 `master`、HEAD `177ad2b`、无上游跟踪；工作区仅有 `HANDOFF.md`、`STATUS.md`、`TODO.md` 三份未暂存交接刷新。
4. 只确认 `.env` 存在、被忽略且未跟踪；不得读取或输出 Key。
5. 不重复真实 DeepSeek 调用，除非用户明确要求重新验收。
6. 向用户复述状态、列出缺失或矛盾信息，并给出最多 5 个步骤。
7. 等待用户明确选择下一动作；不得自行提交、推送或开始 Day 4。

### 12. Day 3 验收结果

以下条件已经满足：

- Python 为 `3.11.15`；
- `pip check` 输出 `No broken requirements found.`；
- `GET /health` 为 `200 {"status":"ok"}`；
- 无 Key 时 `/chat` 的模拟测试为安全的 `503`；
- 有真实 Key 时非流式 `/chat` 返回 `200`、非空 `answer`、模型为 `deepseek-v4-flash`；
- 有真实 Key 时流式 `/chat` 返回 `200`，`Content-Type` 为 `text/event-stream; charset=utf-8`，收到 3 个 delta，最后为 `[DONE]`，无 error 事件；
- 空白消息返回 `422`；
- `POST /documents/upload` 仍返回 `501`；
- pytest `12 passed, 1 warning`，没有测试失败；
- `.env` 和真实 Key 未进入 Git，`.env.example` 为占位符；
- 日志未发现 API Key、Authorization、Bearer 或请求正文；
- `git diff --check` 通过，仅有 LF/CRLF 非阻断提示；
- 没有实现 Day 4 或更晚功能；
- 用户已明确授权同步 `PLAN.md`，Day 3 已标为完成；
- Day 3 已形成本地提交检查点，尚未推送。

当前暂停状态的恢复验收标准：

- 新对话准确识别 HEAD `177ad2b`、Day 3 已完成且未推送；
- 新对话准确识别仅三份交接文件有未提交刷新，业务代码没有新增修改；
- 不读取或输出 `.env`/API Key；
- 不重复 Day 3 实现或真实 API 调用；
- 不提交、不推送、不开始 Day 4，直到用户明确授权；
- 对待确认事项保持“待确认”，不自行补全。

### 13. 精确命令

所有命令从 `D:\2019\rag-agent` 执行：

```powershell
# 查看状态
git status --short --branch
git log -1 --oneline

# 安装依赖
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# 检查依赖
.\.venv\Scripts\python.exe -m pip check

# 测试
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 首次创建本地配置；不要提交 .env
Copy-Item .env.example .env

# 启动
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Swagger UI：`http://127.0.0.1:8000/docs`
健康检查：`http://127.0.0.1:8000/health`

### 14. 交接文件维护规则

每完成一个可验收检查点：

1. 更新 `STATUS.md`；
2. 更新 `HANDOFF.md`；
3. 只有产生新决策时更新 `DECISIONS.md`；
4. 更新 `TODO.md`，只保留一个明确的下一步；
5. 记录实际修改文件、执行命令、测试结果和错误；
6. 禁止把计划中的内容提前写成已完成；
7. 更新 `PLAN.md` 前必须得到用户明确授权。

## B. 300 字以内快速恢复摘要

仓库 `D:\2019\rag-agent`，分支 `master`，HEAD `177ad2b`。Day 3 已提交但未推送：OpenAI-compatible `LLMClient`、`deepseek-v4-flash`、JSON/SSE 均已实现，真实非流式/SSE 验收通过，pytest `12 passed, 1 warning`。`.env` 存在但被忽略且未跟踪。当前仅 `HANDOFF.md`、`STATUS.md`、`TODO.md` 有未提交交接刷新，功能开发暂停。恢复后先只读复述状态，等待用户决定提交、推送或 Day 4。

## C. 新对话第一条启动提示词

```text
这是一个已有项目的新工作会话，仓库位于 D:\2019\rag-agent。

请先完整阅读：
1. HANDOFF.md
2. STATUS.md
3. DECISIONS.md
4. TODO.md
5. AGENTS.md
6. README.md
7. docs/architecture.md
8. backend/app/api/chat.py
9. backend/app/services/llm.py
10. backend/app/core/config.py
11. backend/tests/test_chat.py
12. backend/tests/test_llm.py

执行规则：
- 不要重新完成已经完成的工作。
- 不要擅自推翻 DECISIONS.md 中的技术决策。
- 不要假设未提供的信息；不确定内容标记为“待确认”。
- 不要读取、输出或提交 .env/API Key。
- 不要修改 PLAN.md，除非我明确授权。
- 不要开始 Day 4 或更晚任务。
- 先只读检查，不要立即改代码。

请先回复：
1. 你理解的项目目标和当前状态；
2. 已提交内容与未提交内容；
3. 发现的缺失、矛盾或风险；
4. 接下来最多 5 个步骤。

预期基线：分支 master，HEAD 177ad2b；Day 3 真实 deepseek-v4-flash 非流式和 SSE 验收已通过，pytest 12 passed、1 warning；Day 3 已本地提交但尚未推送。当前仅 HANDOFF.md、STATUS.md、TODO.md 有未暂存交接刷新。

当前唯一目标：只读确认交接包和 Git 状态，复述项目状态并等待用户指定下一动作。

本轮验收标准：准确识别已完成/未提交/未推送内容和待确认事项；列出缺失或矛盾信息；给出最多 5 个步骤；不改代码、不读取 .env、不提交、不推送、不开始 Day 4。

复述完成后等待我确认，再从 HANDOFF.md 的“下一步具体操作”开始。
```
