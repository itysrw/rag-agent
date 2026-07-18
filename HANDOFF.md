# 项目完整交接包

更新时间：2026-07-16（America/New_York）
仓库：`D:\2019\rag-agent`

> 本文件是独立交接入口。Day 9 检索优化已在本地工作区实现并验收；当前暂停开发，
> 等待用户指定审查、计划更新或 Git 检查点动作。Day 9 未调用任何付费 API。

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
3. `DECISIONS.md`（Day 9 新增 D-039 至 D-042）
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`（只读）
8. `docs/architecture.md`
9. `docs/day8-rag-smoke.md`
10. `docs/day9-retrieval-tuning.md`
11. `.env.example`（禁止读取 `.env`）
12. `backend/app/api/retrieval.py`
13. `backend/app/services/retrieval.py`
14. `backend/app/services/qdrant_store.py`
15. `backend/app/services/rag.py`（Day 9 未修改，回归参照）
16. `backend/tests/test_retrieval.py`
17. `backend/tests/test_qdrant_store.py`
18. `backend/tests/test_qdrant_integration.py`
19. `backend/tests/day9_tuning_corpus.py`
20. `backend/tests/test_retrieval_tuning_integration.py`
21. `backend/tests/test_rag.py`、`backend/tests/test_chat.py`（回归参照）

禁止读取、输出或提交 `.env`、API Key、数据库真实密码；不得读取或提交无关 `.agents/`
或测试产物 `.pytest-tmp/`，不得提交 `data/models/`。

### 3. 阶段状态

#### Day 1-8：已提交

- Day 1-3：项目边界、FastAPI、日志、OpenAI-compatible DeepSeek JSON/SSE。
- Day 4-5：PDF/Markdown/TXT 上传解析、PostgreSQL、按页 `o200k_base` 500/100 切分。
- Day 6：固定 revision 本地 BGE，CPU、512 维、归一化、批量 ≤32、tokenizer 预检。
- Day 7：显式 `index_document` 写入 unnamed 512/Cosine Qdrant，固定 Top 5 检索 API。
- Day 8：`/chat` 基础 RAG（固定 Top 5 → `0.46` 门控 → 结构化 Prompt → 后端 sources、
  模型来源标记清理、固定拒答不调用 LLM）；真实 DeepSeek 冒烟覆盖报销 JSON、VPN SSE、
  Python 门控拒答。

当前已提交基线：

```text
33689d31018fcf35b7526fff33a1649f7a0430ac feat: complete Day 8 basic RAG
```

#### Day 9：本地已实现并验收，未提交

范围：仅独立检索层。`/chat`、RAG 门槛、上传、索引命令、collection 契约均未修改。

已完成：

- `POST /retrieval/search` 请求模型：`query`（1..4096，strip）、`top_k`
  （`Field(strict=True, ge=1, le=20)`，默认 5）、`doc_id`（UUID|None）、禁止额外字段。
  `0/21/true/"5"/5.0/null` 与非法 UUID 均 422。
- `RetrievalService.search(query, *, top_k=5, doc_id=None)`：非法 top_k 在 Embedding
  前抛 `ValueError`；Day 8 旧调用 `search(question)` 行为不变。
- `QdrantVectorStore.search(vector, *, limit, doc_id=None)`：doc_id 非空时把顶层
  `doc_id` 的 `MatchValue(str(doc_id))` 过滤器传入 `query_points(query_filter=...)`，
  Qdrant 内先过滤再取 limit；None 时不传参数保持原调用形状；解析后校验所有结果属于
  请求文档，越界抛 `QdrantResultError`（502）；非 UUID doc_id 直接 `ValueError`。
- 合法但无匹配 doc_id：200 空数组，不引入 404。
- 检索日志：每次成功检索（含空结果）恰好一条 `retrieval_search_completed` 单行 JSON
  进入 message；字段 query_sha256/query_len/top_k/filter_doc_id/result_count/
  results（rank/chunk_id/doc_id/filename/page/score）；无 query 原文/正文/metadata/
  向量/凭据；序列化失败只记安全错误、不影响请求。
- Day 7 遗留"拒绝 Day 9 参数"测试已改为接受合法参数。
- 确定性 300/500/800 真实实验、唯一命中判据与统一 token 口径（见第 5 节）。

### 4. Git 与工作区精确状态

最后只读核对：

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| HEAD | `33689d31018fcf35b7526fff33a1649f7a0430ac` |
| 本地 `origin/master` | `33689d31018fcf35b7526fff33a1649f7a0430ac` |
| 暂存区 | 空 |
| Day 9 commit/push | 无 / 无 |
| GitHub 实时 HEAD | 本轮未重新查询；不得用本地跟踪引用替代实时结论 |

Day 9 已修改跟踪文件（12 个）：

- `README.md`
- `DECISIONS.md`
- `STATUS.md`
- `TODO.md`
- `HANDOFF.md`
- `docs/architecture.md`
- `backend/app/api/retrieval.py`
- `backend/app/services/retrieval.py`
- `backend/app/services/qdrant_store.py`
- `backend/tests/test_retrieval.py`
- `backend/tests/test_qdrant_store.py`
- `backend/tests/test_qdrant_integration.py`

（其中 6 个为文档，6 个为代码/测试。）

Day 9 新增未跟踪文件（3 个）：

- `backend/tests/day9_tuning_corpus.py`
- `backend/tests/test_retrieval_tuning_integration.py`
- `docs/day9-retrieval-tuning.md`

另有无关未跟踪 `.agents/`，未读取或修改，必须排除；`.pytest-tmp/` 当前不存在。
`PLAN.md`、`backend/app/api/chat.py`、`backend/app/services/rag.py`、
`backend/requirements.txt`、`docker-compose.yml` 无差异；未读取 `.env`，未新增生产依赖。

### 5. 精确代码位置、接口与运行入口

- `backend/app/api/retrieval.py`
  - `RetrievalSearchRequest`：`query`、严格 `top_k=5`、`doc_id: UUID | None`，额外字段禁止。
  - `RetrievedChunkResponse`、`RetrievalSearchResponse`：响应结构保持不含向量。
  - `require_retrieval_service()`：延迟解析依赖并把配置错误安全映射为 503。
  - `search_retrieval()`：透传 `top_k/doc_id`，保留 422/502/503 错误契约。
- `backend/app/services/retrieval.py`
  - `RETRIEVAL_TOP_K=5`、`RETRIEVAL_TOP_K_MIN=1`、`RETRIEVAL_TOP_K_MAX=20`。
  - `RETRIEVAL_SEARCH_EVENT="retrieval_search_completed"`。
  - `RetrievalService.search(query, *, top_k=5, doc_id=None)`。
  - `_validated_top_k()`：在 Embedding 前拒绝 bool、非 int 和范围外数值。
  - `_log_search_event()`：把安全单行 JSON 实际写入 Loguru message。
- `backend/app/services/qdrant_store.py`
  - `QdrantVectorStore.search(query_vector, *, limit, doc_id=None)`：构造可选
    `models.Filter`/`FieldCondition`/`MatchValue(str(doc_id))`，并复验返回 doc_id。
  - `_parse_scored_point()` 继续负责 UUID、payload、metadata 和有限 score 的安全校验。
- `backend/tests/day9_tuning_corpus.py`
  - `TuningQuestion`、`DETERMINISTIC_AUDIT_TOKEN`、`AUDIT_SUFFIX`、`CORPUS_PAGES`、
    `QUESTIONS`、`page_texts()`。
- `backend/tests/test_retrieval_tuning_integration.py`
  - `normalized()`、`chunk_hits_phrase()`、`token_count()`、`configuration_drafts()`、
    `ConfigReport`。
  - `test_normalization_is_nfkc_and_outer_strip_only()`、
    `test_corpus_satisfies_the_patched_structural_contract()` 在标准套件运行。
  - `test_chunk_size_configurations_produce_real_metrics()` 由两个真实集成开关控制。
- `backend/tests/test_retrieval.py`
  - 新增/更新 `test_retrieval_service_defaults_to_fixed_top_five()`、
    `test_retrieval_service_passes_top_k_and_doc_id_through()`、严格 top_k 参数化测试、
    三个安全日志测试，以及 API 默认值/边界/doc_id/空结果/错误映射测试。
- `backend/tests/test_qdrant_store.py`
  - 新增 `test_search_with_doc_id_applies_top_level_string_filter_in_query()`、
    `test_search_without_doc_id_keeps_the_original_call_shape()`、返回 doc_id 越界拒绝、
    非 UUID 拒绝和本地模式过滤回归。
- `backend/tests/test_qdrant_integration.py`
  - `test_real_qdrant_doc_id_filter_returns_only_the_requested_document()` 使用两个 doc_id
    验证 Qdrant 内过滤并在 finally 中清理临时 collection。

安装、启动和测试均从仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

PostgreSQL 与 Qdrant 的本地启动、初始化和显式索引命令见 `README.md`；应用启动和
`GET /health` 本身不会连接 PostgreSQL、BGE、Qdrant 或 LLM。

### 6. Day 9 技术决策与实验结论

决策记录：`DECISIONS.md` D-039（top_k 严格校验 1..20）、D-040（Qdrant 内过滤 +
一致性校验 + 200 空数组语义）、D-041（单行 JSON 检索日志边界）、D-042（确定性实验
语料、唯一命中判据与统一 token 口径）。

chunk size 实验（`docs/day9-retrieval-tuning.md`，全部真实运行）：

| 配置 | Chunk 数 | 平均 token | Hit@1 | Hit@5 | MRR@5 | Top-5 context token 总量 |
|---|---:|---:|---:|---:|---:|---:|
| 300/60 | 40 | 199.3 | 1.00 | 1.00 | 1.000 | 7986 |
| 500/100 | 24 | 332.9 | 1.00 | 1.00 | 1.000 | 13590 |
| 800/160 | 16 | 499.9 | 1.00 | 1.00 | 1.000 | 18576 |

关键结论：

- 语料与 8 个问题固定在纯 Python 常量中，自撰、可公开提交、不随机、不联网；每题有
  `expected_phrase`，命中只按 NFKC + strip 后的子串包含判断。
- 每页 982～1011 o200k token；三配置产生不同 Chunk 数（40/24/16）并全部通过真实 BGE
  与 Qdrant。最大 BGE token 为 62/114/213。
- 三配置命中指标均满分，当前简单事实语料不能区分质量；Top-5 上下文 token 总量随
  chunk size 增加。固定长审计标识会被 BGE tokenizer 高度压缩，结果不外推到自然长文本。
- 生产默认保持 `500/100`；不宣称普遍最优。

### 7. HTTP 与错误契约（Day 9 后）

`POST /retrieval/search` 请求：

```json
{"query": "VPN 出现故障应该联系谁？", "top_k": 8, "doc_id": "可选 UUID 或 null"}
```

成功响应结构不变（results 数组，无向量）。错误映射：

- 请求字段不合法（含 top_k 类型/范围、非法 UUID、额外字段）：`422`。
- BGE Query 超限：`422`。
- Embedding/Qdrant 不可用或 collection 不匹配：`503`。
- Qdrant Point/Payload 无效，或 filter 查询返回其他文档：安全 `502`。
- 无匹配结果：`200 {"results": []}`，不新增 404。

`/chat` 契约与 Day 8 完全一致。应用启动和 `GET /health` 不连接任何外部服务。

### 8. 不可违反的约束

- 只实现 `PLAN.md` 当前获授权的 Day；Day 10 BM25 及以后尚未授权。
- 未经明确授权不得修改 `PLAN.md`；不得把计划能力写成已完成。
- Python 固定为 3.11；后端代码位于 `backend/`；公共函数保留类型标注；使用 pytest。
- 不得读取、输出、暂存或提交 `.env`、真实 API Key、数据库密码、`.agents/`、
  `.pytest-tmp/` 或 `data/models/`。
- 不得再次调用 DeepSeek 或其他付费 API，除非用户给出新的明确授权。
- 不得修改 `backend/app/api/chat.py`、`backend/app/services/rag.py`、RAG `0.46` 门槛、
  `/chat` 请求/响应/sources/SSE 契约。
- 不得修改上传、显式 `index_document` 流程或 Qdrant collection schema/初始化契约；
  不得创建 payload index。
- Day 9 只支持单个 `doc_id`；不得提前实现 score threshold、多 doc_id、BM25、Hybrid、
  RRF、Rerank、request_logs、admin traces、LangGraph 或多轮记忆。
- 暂存、commit、实时远端核验和 push 是不同动作，分别等待明确授权。
- 工作区已有修改属于当前任务，不得用 reset/checkout 覆盖；暂存时必须逐项选择 Day 9
  文件并排除无关内容。

### 9. 验证证据

- 开发前门禁：HEAD `33689d3`，本地 `origin/master` 一致，工作区仅 `.agents/` 未跟踪。
- 检索/适配层与实验前置校验：`68 passed, 1 skipped, 1 warning in 12.14s`；Day 8
  定向回归历史证据：`27 passed`。
- 真实 Qdrant 回归（含双文档 filter）：`3 passed, 1 warning in 12.40s`。
- 真实 BGE + Qdrant 实验套件：`3 passed, 1 warning in 13.90s`；`day9_tuning_*`
  collection 已清理。
- 最终标准套件：`214 passed, 7 skipped, 1 warning in 14.12s`。
- `pip check`、`compileall -q backend`、`git diff --check`：通过；密钥模式扫描 0 匹配。
- 当前失败测试：无。

精确命令：

```powershell
# 标准套件（真实外部集成默认跳过）
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 静态/依赖检查
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q backend
git diff --check

# 真实 Qdrant 模块（含双文档 filter）
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v

# 真实 300/500/800 chunk size 实验
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_retrieval_tuning_integration.py -v -s
```

环境注意：`%TEMP%\pytest-of-袁伟鑫` 目录 ACL 损坏会导致所有 `tmp_path` 测试 ERROR。
本轮通过设置 `PYTEST_DEBUG_TEMPROOT` 指向可写目录绕过；损坏目录未删除（需管理员），
根因待确认。若标准套件出现大量 `PermissionError [WinError 5]` ERROR，先设置该环境变量。

### 10. 已尝试但失败或被否决的方案

- 已替换：短页语料会让 500/800 退化为相同 Chunk，长自然中文段落又可能超过 BGE 512
  上限，均不能满足三配置完整指标。最终使用明确披露的固定审计标识构造确定性长页，
  让三个配置产生不同 Chunk 数且均通过 BGE 预检。
- 已否决：搜索后在 Python 中过滤 doc_id（其他文档挤占 limit 名额）。
- 已否决：`metadata.doc_id` 作为 filter key（payload 的 doc_id 在顶层）、MatchValue
  传 UUID 对象（payload 为字符串，无法命中）。
- 已否决：为 doc_id 建 Qdrant payload index（扩大 Day 7 collection 初始化契约）。
- 已失败并修复：`ConfigReport(slots=True)` 用 `__dict__` 序列化（AttributeError），
  改用 `dataclasses.asdict`。
- 环境障碍：强制修复 `%TEMP%\pytest-of-*` ACL 的操作被权限策略拒绝，改用
  `PYTEST_DEBUG_TEMPROOT` 非破坏绕过。

### 11. 当前错误、日志、未验证项与残余风险

- 当前失败测试：无。
- 当前持续 warning：pytest 无法写入仓库 `.pytest_cache`，日志为
  `PytestCacheWarning: [WinError 5] Access is denied`；不影响测试通过。
- Git 仍提示部分工作区 LF 将来可能转为 CRLF；`git diff --check` 已通过，是否增加
  `.gitattributes` 为“待确认”。
- 最终检查确认 `day9_tuning_*` / `day9_filter_*` 临时 Qdrant collection 残留数为 0；
  本地 Markdown 失效链接 0，常见密钥模式匹配 0。
- 实验语料受控且小规模，固定审计标识造成非自然 tokenizer 比例；三配置满分不外推为
  普遍等价或最优，更大、更难且接近真实文档分布的评测集仍待后续建设。
- `query_sha256` 不等于匿名化；`top_k=20` 的 Rerank 用途在 Day 12 之前不实现。
- `%TEMP%\pytest-of-袁伟鑫` ACL 损坏目录未修复；`.pytest_cache` WinError 5 与
  LF→CRLF 根因待确认。
- GitHub 实时远端 HEAD 未联网查询；只能确认本地 `origin/master=33689d3`，实时状态
  标记为“待确认”。
- 真实 DeepSeek 四题全覆盖仍待用户确认（Day 9 未调用付费 API）。
- PostgreSQL/Qdrant 无跨存储事务、outbox、删除同步或一致性修复。

### 12. 待完成任务

- Day 9 功能与文档本地验收已完成；尚未修改 `PLAN.md`、暂存、commit、实时远端核验或
  push，这些都需要用户分别授权。
- Day 10（BM25）及以后尚未开始，也未获授权。
- 更自然、更困难的 chunk size 评测语料与召回曲线属于后续复验，不是本检查点阻塞项。
- pytest 临时目录/缓存 ACL、LF/CRLF 规范、真实 DeepSeek 年假/月球补充调用、
  PostgreSQL/Qdrant 一致性方案均为“待确认”。

### 13. 下一步具体操作（最多 5 步）

1. 等待用户指定 Day 9 审查或检查点操作。
2. 只有明确授权后才修改 `PLAN.md` Day 9 状态。
3. 只有明确授权后才暂存，并逐项排除 `.env`、`.agents/`、`data/models/`。
4. commit、实时远端核验和 push 分别等待独立授权。
5. Day 9 检查点完成且用户授权后，才可开始 Day 10（BM25）。

### 14. 当前检查点验收标准

Day 9 只有同时满足以下条件才可视为完成；当前本地工作区均已满足：

- `POST /retrieval/search` 默认 Top 5；严格接受 `top_k=1..20`，拒绝
  `0/21/true/"5"/5.0/null`；可选单个 UUID `doc_id`。
- doc_id filter 在 Qdrant `query_points(query_filter=...)` 内、limit 前执行；返回结果
  再做 doc_id 一致性检查；无匹配为 200 空数组。
- 每次成功检索输出一条安全单行 JSON，不含 query 原文、Chunk 正文、metadata、向量
  或凭据。
- Day 8 `/chat` 仍通过 `RetrievalService.search(question)` 使用默认 Top 5，RAG `0.46`
  门槛和 JSON/SSE/sources 契约无变化。
- 固定语料至少 8 问且每题有 `expected_phrase`；每页 o200k token >800；三配置 Chunk
  数互不相同；命中只使用 NFKC + strip 子串规则。
- 300/60、500/100、800/160 都经真实本地 BGE + 临时 Qdrant 产生完整 Hit@1、Hit@5、
  MRR@5、Chunk 数、平均 Chunk token、Top-5 context token 总量。
- README 与 `docs/day9-retrieval-tuning.md` 写入实际数字和局限，不宣称普遍最优。
- 标准测试、真实 Qdrant、真实实验、`pip check`、`compileall`、`git diff --check` 通过；
  当前失败测试为 0，临时 collection 残留为 0。
- `PLAN.md`、Chat/RAG、requirements、docker-compose 无差异；未调用付费 API；没有
  暂存、commit 或 push Day 9 文件。

## B. 300 字以内快速恢复摘要

`D:\2019\rag-agent`，master/HEAD `33689d3`；Day 1-8 已提交。Day 9 已本地验收且未暂存/
提交/推送：检索支持严格 top_k、单 doc_id 过滤和安全 JSON 日志。8 页 8 问实验 Chunk
数为 40/24/16，三项命中指标均为 1.0。标准测试 214 passed/7 skipped/1 warning；真实
Qdrant 与实验各 3 passed。PLAN/Chat/RAG 无差异，无付费 API；排除 `.env`、`.agents/`、
`.pytest-tmp/`、`data/models/`，等待唯一动作。

## C. 新会话启动提示词

```text
这是已有项目的新会话，仓库 D:\2019\rag-agent。先完整阅读 HANDOFF.md、STATUS.md、
DECISIONS.md、TODO.md、AGENTS.md、README.md、PLAN.md、docs/architecture.md、
docs/day9-retrieval-tuning.md 及 HANDOFF 列出的 Day 9 代码/测试。第一轮只读核验并
复述：master/HEAD 33689d3；Day 1-8 已提交；Day 9 有 12 个修改跟踪文件和 3 个新文件，
已验收但未暂存/提交/推送；标准测试 214 passed/7 skipped/1 warning；真实 Qdrant 回归
3 passed；真实 chunk size 实验 3 passed，三配置均有完整指标；PLAN.md 无差异。
禁止读取 .env 或无关 .agents/，排除 data/models/。若 pytest 出现大量 WinError 5
ERROR，先设置 PYTEST_DEBUG_TEMPROOT；同时排除 .pytest-tmp/。GitHub 实时 HEAD 待确认，
不得用本地 origin/master 代替实时结论。先复述已完成内容、当前工作区、错误/风险、
约束和验收证据，列出矛盾/待确认项及最多 5 个下一步，然后等待我指定唯一动作；不要
直接改代码、修改 PLAN.md、暂存、提交、推送或调用付费 API。

当前唯一目标：完成 Day 9 检查点的只读状态确认，不开始 Day 10。
本轮验收标准：复述与 HANDOFF/Git 一致，明确未提交文件、测试证据、约束、错误和
待确认项；在我指定下一动作前不产生任何仓库或外部状态变更。
```
