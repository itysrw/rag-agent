# 项目完整交接包

更新时间：2026-07-16（America/New_York）
仓库：`D:\2019\rag-agent`

> 本文件是独立交接入口。Day 8 基础 RAG 已在本地工作区实现并验收；当前暂停开发。
> 真实 DeepSeek 已在用户授权下完成一次付费冒烟验收；不要再次调用，除非获得新的明确授权。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供文档上传、检索和问答 API；
- PostgreSQL 保存 Document/Chunk 业务数据，Qdrant 保存本地 BGE 向量；
- 后续使用 BM25、RRF、Rerank 优化检索；
- OpenAI-compatible LLM 生成带来源引用的答案；
- LangGraph 实现工具选择和多轮记忆；
- 通过评测集量化检索、答案和延迟；
- Streamlit 与 Docker Compose 提供最终演示和部署；
- 形成 README、架构图、评测报告、简历描述和面试材料。

`PLAN.md` 是 25 天范围基线。未来功能不得写成已完成；未经明确授权不得修改该文件。

### 2. 新会话阅读顺序

1. `HANDOFF.md`
2. `STATUS.md`
3. `DECISIONS.md`
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`（只读）
8. `docs/architecture.md`
9. `docs/day7-retrieval-smoke.md`
10. `docs/day8-rag-smoke.md`
11. `.env.example`（禁止读取 `.env`）
12. `backend/requirements.txt`
13. `backend/app/core/config.py`
14. `backend/app/api/chat.py`
15. `backend/app/api/retrieval.py`
16. `backend/app/services/llm.py`
17. `backend/app/services/embedding.py`
18. `backend/app/services/qdrant_store.py`
19. `backend/app/services/retrieval.py`
20. `backend/app/services/rag.py`
21. `backend/app/commands/index_document.py`
22. `backend/tests/test_chat.py`
23. `backend/tests/test_llm.py`
24. `backend/tests/test_rag.py`
25. `backend/tests/test_rag_integration.py`
26. `backend/tests/test_qdrant_integration.py`
27. `backend/tests/pdf_fixtures.py`
28. `backend/tests/test_document_parser.py`

禁止读取、输出或提交 `.env`、API Key、数据库真实密码；不得读取或提交无关 `.agents/`，
不得提交 `data/models/`。

### 3. 阶段状态

#### Day 1-7：已提交

- Day 1-3：项目边界、FastAPI、日志、OpenAI-compatible DeepSeek JSON/SSE。
- Day 4-5：PDF/Markdown/TXT 上传解析、PostgreSQL、按页 `o200k_base` 500/100 切分、
  有序 Chunk 和同事务两次 flush。
- Day 6：固定 revision 的本地 BGE，CPU、512 维、归一化、批量最多 32、tokenizer 预检、
  固定 snapshot 和安全重试。
- Day 7：显式 `index_document` 将 PostgreSQL Chunk 写入 unnamed 512/Cosine Qdrant，
  稳定 Chunk UUID 幂等 upsert；`POST /retrieval/search` 固定 Top 5、不返回向量。

当前已提交基线：

```text
683f516777345a1a000c6f94ade5fb4232a3a58e feat: complete Day 7 Qdrant retrieval
```

Day 6 两个已提交 P2：

1. Embedding `ValidationError` 在客户端创建边界转为 `EmbeddingConfigurationError`，不再误报数据库不可用。
2. 模型缓存目录创建 `OSError` 安全包装为 `ModelDownloadError`，不泄露路径且不调用 downloader。

#### Day 8：本地已实现并验收，未提交

链路：

```text
POST /chat
  → Day 7 固定 Top 5
  → RAG 层 score >= 0.46 门控
  → system 规则 + user JSON Context
  → DeepSeek/OpenAI-compatible LLM
  → answer + 后端 sources
```

已完成：

- `RAGSettings(min_relevance_score=0.46)`，范围 `0..1`；只在生成层使用。
- `LLMMessage`、`complete_messages()`、`stream_messages()`；旧单消息接口保持兼容。
- `RAGSource`、`PreparedRAG`、`RAGAnswer`、`RAGService`。
- Prompt 中 system 保存规则，Context 作为不可信 JSON user 数据，仅含 filename/page/content。
- 无相关 Context 精确返回 `知识库中没有相关信息`，不调用 LLM 方法。
- sources 从实际 Context 按 filename/page 去重，不解析模型文本。
- 模型正文中的文件名、页码和 `SNN` 类来源标记会被清理；可信引用只通过后端
  结构化 `sources` 返回。
- 普通 `/chat` 返回 answer/model/sources。
- SSE 成功返回 delta → sources event → DONE；流失败不发送 sources 或 DONE。
- `prepare()` 在 `StreamingResponse` 前完成，检索错误保持 HTTP 422/502/503。
- 上传接口仍不自动索引；完整链路保持 upload → `index_document` → `/chat`。

未实现 Day 9：没有可调 top_k、doc filter、请求 threshold、BM25、Hybrid、Rerank 或 trace。

### 4. Git 与工作区精确状态

最后只读核对：

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| HEAD | `683f516777345a1a000c6f94ade5fb4232a3a58e` |
| 本地 `origin/master` | `683f516777345a1a000c6f94ade5fb4232a3a58e` |
| 基于本地跟踪引用 ahead/behind | `0/0` |
| 暂存区 | 空 |
| Day 8 commit/push | 无 / 无 |
| GitHub 实时 HEAD | 本轮未重新查询；不得用本地跟踪引用替代实时结论 |

Day 8 已修改跟踪文件：

- `.env.example`
- `DECISIONS.md`
- `HANDOFF.md`
- `README.md`
- `STATUS.md`
- `TODO.md`
- `backend/app/api/chat.py`
- `backend/app/core/config.py`
- `backend/app/services/llm.py`
- `backend/tests/pdf_fixtures.py`
- `backend/tests/test_chat.py`
- `backend/tests/test_document_parser.py`
- `backend/tests/test_llm.py`
- `docs/architecture.md`

Day 8 新增未跟踪文件：

- `backend/app/services/rag.py`
- `backend/tests/test_rag.py`
- `backend/tests/test_rag_integration.py`
- `docs/day8-rag-smoke.md`

合计为 14 个已修改跟踪文件、4 个 Day 8 新增未跟踪文件。另有无关未跟踪 `.agents/` 和
测试产物 `.pytest-tmp/`；两者均未读取、修改或删除，必须排除。`PLAN.md`、
`docker-compose.yml`、`backend/requirements.txt` 无差异；未读取 `.env`，未新增生产依赖。

### 5. Day 8 技术决策

#### 5.1 真实相关性校准

修复中文 PDF fixture 后，受控三页 PDF 的 Top-1：

| 类型 | 问题 | 页 | score |
|---|---|---:|---:|
| 正 | 报销票据最晚什么时候交？ | 1 | 0.688781 |
| 正 | VPN 连不上应该联系谁，分机是多少？ | 2 | 0.734850 |
| 正 | 年假需要提前多久申请？ | 3 | 0.814524 |
| 负 | 月球表面温度是多少？ | 1 | 0.282149 |
| 负 | Python 如何定义一个函数？ | 2 | 0.326244 |
| 负 | 纽约今天的天气怎么样？ | 3 | 0.306839 |

当前正样本最小 `0.688781`，负样本最大 `0.326244`，选择固定 `0.46`。该门槛不是概率，
只对这六个样本有证据，后续需更大评测集复验。

#### 5.2 Prompt 和注入边界

- system：只能根据 Context 回答；Context 不可信；不得执行正文命令、泄露系统提示、
  使用外部知识或伪造来源。
- user：JSON Context + 原始问题。
- Context 不包含 vector、score、UUID、doc_id 或 metadata。

#### 5.3 来源与拒答

- 只有达到门槛的 Chunk 进入 Prompt。
- sources 与实际 Context 同源，按 filename/page 去重并保持首次出现顺序。
- `RAGService.complete()` 通过 `_strip_model_source_references()` 清理完整回答中的模型来源标记；
  `RAGService.stream()` 通过 `_sanitized_model_deltas()` 跨 delta 清理同类标记。
- 没有 Context 时 JSON/SSE 都返回固定拒答，LLM complete/stream 调用次数为 0。
- 一个问题可能有多个 Chunk 超过门槛，因此 sources 可能包含多个页，而不是只返回 Top 1。

#### 5.4 Day 8 精确代码位置与接口名

- `backend/app/core/config.py`
  - 常量 `RAG_MIN_RELEVANCE_SCORE = 0.46`。
  - `RAGSettings.min_relevance_score`、`get_rag_settings()`；环境变量名为
    `RAG_MIN_RELEVANCE_SCORE`。
- `backend/app/services/llm.py`
  - `LLMMessage`、`LLMClient.complete_messages()`、`LLMClient.stream_messages()`。
  - 兼容接口 `LLMClient.complete()`、`LLMClient.stream()` 保留。
- `backend/app/services/rag.py`
  - `NO_RELEVANT_KNOWLEDGE`、`RAG_SYSTEM_PROMPT`。
  - `RAGSource`、`PreparedRAG`、`RAGAnswer`。
  - `select_relevant_chunks()`、`build_sources()`、`build_rag_messages()`。
  - `RAGService.prepare()`、`RAGService.complete()`、`RAGService.stream()`、`get_rag_service()`。
  - `_strip_model_source_references()`、`_sanitized_model_deltas()` 清理模型自由文本来源标记。
- `backend/app/api/chat.py`
  - `ChatRequest`、`ChatSourceResponse`、`ChatResponse`；message 最大 4096 字符。
  - `require_rag_service()`、`chat()`、`stream_sse()`。
- `backend/tests/test_rag.py`：门控、Prompt、来源、拒答、结构化 LLM 调用与空流单测。
- `backend/tests/test_chat.py`：JSON/SSE、错误映射、来源清理、lazy dependency 单测。
- `backend/tests/test_rag_integration.py`：
  `test_upload_index_and_chat_returns_answer_source_and_safe_refusal()`，使用真实
  PostgreSQL/BGE/Qdrant 与 Stub LLM。
- `backend/tests/pdf_fixtures.py`：`build_text_pdf()`、`_build_text_stream()`。

### 6. HTTP 与错误契约

普通响应：

```json
{
  "answer": "……",
  "model": "deepseek-v4-flash",
  "sources": [{"filename": "policy.pdf", "page": 1}]
}
```

SSE 成功：delta events → sources event → `[DONE]`。无 Context 时发送一条固定拒答 delta、
空 sources event、`[DONE]`。

错误映射：

- 空白 message：Pydantic `422`。
- BGE Query 超限：`422`。
- Embedding/Qdrant 不可用或 collection 不匹配：`503`。
- Qdrant Point/Payload 无效：安全 `502`。
- LLM 未配置：`503`。
- 普通 LLM 失败：`502`。
- LLM 流开始后失败：SSE error event，不发送 sources 或 DONE。

应用启动和 `GET /health` 不连接 PostgreSQL、BGE、Qdrant 或 LLM。

### 7. 中文 PDF fixture 修复

真实端到端首次上传返回 PostgreSQL `DataError`。根因是旧 Type1+BOM UTF-16BE fixture
被 pypdf 提取为带 NUL 的字节映射；第一次分数测量也因此无效。

修复：测试 PDF 改为 Type0 `/STSong-Light`、`/UniGB-UCS2-H`、CIDFont 与无 BOM
UTF-16BE hex text。回归测试验证中文精确提取且无 NUL。随后真实 PostgreSQL 上传、
Day 7 Qdrant 相关性和 Day 8 端到端均通过。

### 8. 验证证据

开发前标准基线：

```text
153 passed, 4 skipped, 1 warning in 30.41s
```

Day 8 初验标准套件：

```text
183 collected
178 passed, 5 skipped, 1 warning in 16.43s
```

加入模型来源标记清理回归后，本轮重新运行的当前标准套件：

```text
186 collected
181 passed, 5 skipped, 1 warning in 13.91s
```

五个跳过项：真实 PostgreSQL、真实 BGE、两个真实 Qdrant、一个真实 RAG 端到端。

其他已执行：

- 定向 LLM/RAG/Chat：`35 passed, 1 warning in 13.06s`。
- 修复后真实 Qdrant+BGE：`2 passed, 1 warning in 14.41s`。
- 真实 PostgreSQL+BGE+Qdrant、Stub LLM 端到端：`1 passed, 1 warning in 15.81s`。
- 中文解析与上传单测：`25 passed, 1 warning in 14.98s`。
- `pip check`、`compileall -q backend`、`git diff --check`：通过；Day 8 文件常见密钥模式匹配 0。
- 当前失败测试：无。

持续 warning：`.pytest_cache` 写入 `PytestCacheWarning: [WinError 5] Access is denied`；
不影响通过，根因待确认。

精确命令：

```powershell
# 标准套件（真实外部集成默认跳过）
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 静态/依赖检查
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q backend
git diff --check

# 真实 Qdrant + BGE
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v

# 真实 PostgreSQL + BGE + Qdrant，Stub LLM
$env:RUN_RAG_INTEGRATION='1'
$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_rag_integration.py -v
```

#### 8.1 真实 DeepSeek 付费冒烟验收

`docs/day8-rag-smoke.md` 记录 2026-07-16 在用户明确授权下执行一次真实调用，使用
`get_llm_client()` 和 `deepseek-v4-flash`，走真实
upload → `index_document` → `/chat`，并在结束后清理临时 Qdrant collection、PostgreSQL
文档行和上传文件。实际覆盖：

- JSON：“报销票据最晚什么时候交？”回答“每月二十五日前提交给财务组”；sources 为第 1、3 页。
  第 1 页是正确主来源，第 3 页因也超过 `0.46` 被纳入，符合既有契约。
- SSE：“VPN 连不上应该联系谁，分机是多少？”拼接为“联系网络组，分机是 6203”；
  sources 仅第 2 页，以 `[DONE]` 结束，正文无引用标记泄漏。
- 知识库外：“Python 如何定义一个函数？”固定拒答，sources 为空，LLM 调用数未增加。

真实验收没有加入 pytest；一次性脚本未保留。当前仓库没有
`RUN_DEEPSEEK_RAG_INTEGRATION` 开关或对应测试，当前任务也没有可读取的原始终端会话。
因此可确认的是上述验收记录；精确一次性脚本和原始终端日志为“待确认”。未单独真实调用
“年假需要提前多久申请？”或“月球表面温度是多少？”，不得写成四题真实调用全覆盖。

### 9. 已尝试但失败或被否决的方案

- 已失败并修复：Type1 字体 + BOM UTF-16BE 中文 PDF fixture。pypdf 产生带 NUL 文本，
  真实上传触发 PostgreSQL `DataError`；基于该 fixture 的首次相关性分数无效，不得引用。
- 已否决：把模型答案中的文件名/页码当作可信引用。当前实现只信任后端 `sources`，并清理
  模型正文中的来源标记。
- 已否决：在 Day 8 修改 `/retrieval/search` 或开放 top_k/filter/threshold；这些属于 Day 9。
- 已否决：将真实 DeepSeek 调用加入标准 pytest；原因是网络、余额、费用和结果非确定性。

### 10. 当前错误、未验证项与残余风险

- 当前失败测试：无。
- 当前持续 warning：`.pytest_cache` 的 `PytestCacheWarning: [WinError 5] Access is denied`；
  不影响通过，根因待确认。
- 未跟踪 `.pytest-tmp/` 为测试产物；内容未检查，是否清理待确认，不得提交。
- `git diff --check` 通过，但 Git 提示工作区 LF 将来可能转为 CRLF；是否增加
  `.gitattributes` 待确认。
- 真实 DeepSeek 已覆盖 JSON、SSE 和一种门控拒答，但年假真实生成、月球真实拒答未单独执行；
  是否需要补充为完整四题验收待确认，当前暂停且不得自动重跑。
- `0.46` 校准集仅六题，领域和文档分布变化后可能误拒绝或误接受。
- PostgreSQL/Qdrant 无跨存储事务，仍无 outbox、删除同步和一致性修复。
- 模型首次下载、完全离线部署、新机器 Qdrant 复现待确认。
- 上传崩溃孤儿文件、SQLAlchemy 私有 `_state` 和 Alembic 引入时机仍待确认。

### 11. 下一步（最多 5 步）

1. 新会话先只读核验本交接包、Git 状态、14 个已修改文件、4 个 Day 8 新文件，以及需排除的
   `.agents/` 和 `.pytest-tmp/`。
2. 等待用户选择是否需要补充真实 DeepSeek 四题全覆盖；未经新授权不得再次产生费用。
3. 只有明确授权后才修改 `PLAN.md` Day 8 状态。
4. 暂存、commit、实时远端核验、push 分别等待明确授权；暂存时排除 `.env`、`.agents/`、
   `data/models/`。
5. Day 8 检查点完成且用户明确授权后，才可开始 Day 9。

### 12. 验收标准

当前交接检查点：

- 新对话不依赖聊天即可定位目标、状态、决策、失败方案、代码、命令、日志、风险和下一步。
- Git 基线为 `683f516777345a1a000c6f94ade5fb4232a3a58e`；暂存区为空；Day 8 未提交、未推送。
- 当前标准测试 `181 passed, 5 skipped, 1 warning`；真实 Qdrant+BGE `2 passed`；真实
  PostgreSQL+BGE+Qdrant、Stub LLM RAG `1 passed`。
- 真实 DeepSeek 冒烟的实际覆盖范围按 8.1 记录，不扩大成未执行问题。
- `PLAN.md`、`docker-compose.yml`、`backend/requirements.txt` 无差异；没有读取 `.env`，
  没有读取/修改无关 `.agents/` 或 `.pytest-tmp/`，没有暂存、commit 或 push。

若未来补充完整四题付费验收，完成条件为：三个知识库内问题事实正确、首要 sources 页分别
命中 1/2/3；至少覆盖一次 JSON 与一次 SSE；“月球表面温度是多少？”固定拒答、sources 为空且
不调用 DeepSeek；不得记录凭据、完整 Prompt 或知识库全文；模型自然语言不得用脆弱全文匹配。

## B. 300 字以内快速恢复摘要

`D:\2019\rag-agent`，`master`，HEAD `683f516`。Day 1-7 已提交；Day 8 RAG 已验收，
14 改、4 新均未暂存/提交/推送，`PLAN.md` 无差异。固定 Top 5、门槛 `0.46`；
测试 `181 passed/5 skipped/1 warning`，真实检索+Stub LLM RAG `1 passed`。DeepSeek 已通过
报销 JSON、VPN SSE、Python 拒答；年假/月球未单独调用。排除 `.env`、`.agents/`、
`.pytest-tmp/`、`data/models/`，当前暂停。

## C. 新会话启动提示词

```text
这是已有项目的新会话，仓库 D:\2019\rag-agent。先完整阅读 HANDOFF.md、STATUS.md、
DECISIONS.md、TODO.md、AGENTS.md、README.md、PLAN.md、docs/architecture.md、
docs/day7-retrieval-smoke.md、docs/day8-rag-smoke.md 及 HANDOFF 列出的 Day 8 代码/测试。
第一轮只读核验并复述：master/HEAD 683f516；Day 1-7 已提交；Day 8 有 14 个修改文件和
4 个新文件，另有须排除的 .agents/ 和 .pytest-tmp/；已验收但未暂存/提交/推送；标准测试
181 passed/5 skipped/1 warning；真实
Qdrant+BGE 2 passed；真实 PostgreSQL+BGE+Qdrant、Stub LLM RAG 1 passed；真实 DeepSeek
已覆盖报销 JSON、VPN SSE、Python 门控拒答，年假/月球未单独真实调用；PLAN.md 无差异。
禁止读取 .env 或无关 .agents/，排除 data/models/。列出矛盾/待确认项和最多 5 个下一步，
然后等待我指定唯一动作，不要直接改代码或再次调用付费 API。
```
