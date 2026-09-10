# 项目完整交接包

更新时间：2026-09-10（Asia/Shanghai）
仓库：`D:\2019\rag-agent`

> 本文件是独立交接入口。Day 1-10 已实现、验收并形成 Git 检查点；Day 10 实现提交为
> `a614a365ff52b8fa087ce651614c23e2e1017c0b`。未实现 Day 11 Hybrid，未调用付费 API。

## A. 详细交接文档

### 1. 项目目标与当前边界

项目目标是构建可用于简历和面试讲解的企业知识库 RAG Agent：FastAPI、PostgreSQL、
Qdrant、本地 BGE、OpenAI-compatible LLM、后续 Hybrid/Rerank/LangGraph、评测、
Streamlit 与 Docker Compose。

`PLAN.md` 是 25 天范围基线。Day 10 已完成独立 BM25 并更新计划状态；Day 11 RRF/Hybrid
及以后尚未授权，不得把未来能力写成已完成。

### 2. 新会话阅读顺序

1. `HANDOFF.md`
2. `STATUS.md`
3. `DECISIONS.md`（Day 10 新增 D-043 至 D-046）
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`（Day 10 已勾选，Day 11 及以后未开始）
8. `docs/architecture.md`
9. `docs/day9-retrieval-tuning.md`
10. `docs/day10-vector-vs-bm25.md`
11. `backend/app/services/bm25.py`
12. `backend/app/api/bm25.py`
13. `backend/app/main.py`
14. `backend/requirements.txt`
15. `backend/tests/day10_bm25_cases.py`
16. `backend/tests/test_bm25.py`
17. `backend/tests/test_bm25_api.py`
18. `backend/tests/test_bm25_postgres.py`
19. `backend/tests/test_bm25_comparison_integration.py`
20. Day 8/9 回归参照：`backend/app/api/retrieval.py`、`backend/app/services/retrieval.py`、
    `backend/app/services/qdrant_store.py`、`backend/app/services/rag.py`、
    `backend/app/api/chat.py`、相关测试。

禁止读取、输出、暂存或提交 `.env`、API Key、数据库真实密码、无关 `.agents/`、
`.pytest-tmp/`、测试临时目录或 `data/models/`。

### 3. 阶段状态

#### Day 1-10：已提交

- Day 1-8 基线：`33689d31018fcf35b7526fff33a1649f7a0430ac`。
- Day 9 实现提交：`4cccbe26688de33ff25756fc10584060c82fd03f`，用户确认已推送。
- Day 9 状态文档后继提交：`f3ca9ec1541d5e774f1eae92217d32160f15153f`。
- Day 9 `PLAN.md` 状态提交：`5928fa0034aa0378ae164fe9bd1f38e0ca27b807`。
- Day 10 实现提交：`a614a365ff52b8fa087ce651614c23e2e1017c0b`。
- `PLAN.md` 的 Day 10 已按用户明确授权勾选；Day 11 及以后未修改。

#### Day 10：已实现、验收并提交

范围仅包括独立 BM25 关键词检索、真实 PostgreSQL 刷新验收和纯向量/BM25 对比。
`/chat`、RAG `0.46`、向量检索接口、上传、显式索引和 Qdrant collection 均未修改。

已完成：

- 固定并安装 `rank-bm25==0.2.2`，使用 `BM25Okapi` 默认参数。
- 新增 `POST /retrieval/bm25/search`，复用 Day 9 请求模型：query 1..4096、严格
  top_k 1..20（默认 5）、可选单 UUID doc_id、额外字段禁止；响应复用 Chunk 结构。
- raw BM25 score 可大于 1、为 0 或负数；只校验为有限 float，不与 Cosine 或 RAG
  `0.46` 比较。
- Tokenizer：NFKC + casefold；中文 unigram + bigram；英文、数字、`VPN-6203`、
  `ERR_AUTH_42` 类复合编号同时保留完整与组成 token；query 有序去重、corpus 保留 TF。
- PostgreSQL loader JOIN Document/Chunk，仅加载 `status=ready`，按
  doc_id/chunk_index/chunk_id 排序；Session 内转不可变 DTO，关闭后再分词和建索引。
- 每次可搜索请求扫描 corpus 并计算覆盖所有响应字段的 SHA-256 指纹；未变化复用索引，
  变化时在同一锁内完整构建后原子替换。刷新失败时当前请求 fail closed，不返回 stale。
- 空库或全无 token corpus 不构建 `BM25Okapi`；标点/emoji-only query 在数据库前返回空。
- 使用 `get_scores()`，禁止 `get_top_n()`；无结果门控是 token overlap，不是 `score > 0`。
  因此无关键词重合返回空数组，相关负分/零分不会被误删。
- doc_id 在 Top-K 前过滤；稳定排序为 `(-score, doc_id, chunk_index, chunk_id)`。
- 成功搜索（含空结果）恰好写一条 `bm25_search_completed` JSONL，复用
  `JSONL_LOG_MARKER`；不含 query 原文、query tokens、正文、metadata、SQL 或凭据。
- HTTP：请求非法 422；PostgreSQL/配置不可用 503；索引/score 非法安全 500；空库、
  无 token、无 overlap、未知合法 doc_id 均为 200 空数组。
- 应用 import、启动、lifespan 和 `/health` 不解析数据库配置、不读取 corpus、不建索引。

### 4. Git 检查点

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| Day 10 实现提交 | `a614a365ff52b8fa087ce651614c23e2e1017c0b` |
| Day 10 状态提交 | 本文件所在的后继提交 |
| `PLAN.md` | 仅 Day 10 四项和开发日志更新为已完成 |
| 无关工作区内容 | `.agents/` 保持未跟踪，未纳入提交 |

实现提交包含 13 个文件：BM25 API/服务、依赖和路由、5 个 Day 10 测试/数据文件，
以及 DECISIONS、README、architecture 和对比报告。后继状态提交只包含 HANDOFF、PLAN、
STATUS 和 TODO。Chat/RAG、Day 9 向量检索/Qdrant、`docker-compose.yml` 均无功能修改。

### 5. 代码入口和数据流

- `backend/app/services/bm25.py`
  - `BM25CorpusChunk`、`BM25RetrievedChunk`、`BM25Snapshot`。
  - `tokenize_bm25()`、`load_bm25_chunks()`、`build_corpus_fingerprint()`、
    `build_bm25_snapshot()`。
  - `BM25Service.search(query, *, top_k=5, doc_id=None)`。
  - `BM25UnavailableError`（数据库/配置）与 `BM25IndexError`（corpus/index/score）。
- `backend/app/api/bm25.py`
  - `require_bm25_service()` 只返回延迟服务，不加载 PostgreSQL。
  - `search_bm25()` 复用 Day 9 Pydantic 请求/响应并映射 422/500/503。
- `backend/app/main.py`
  - 只新增 BM25 router 注册，没有 startup/lifespan 索引构建。
- `backend/tests/day10_bm25_cases.py`
  - 固定 12 个正样本（精确编号/语义改写/混合各 4）与 3 个负样本。
- `backend/tests/test_bm25_comparison_integration.py`
  - PostgreSQL 与临时 Qdrant 写入同一组 24 个 Chunk ID，按 expected_phrase 计算两路 rank。

调用链：

```text
POST /retrieval/bm25/search
→ 严格 Pydantic 校验
→ BM25Service.search
→ query tokenizer + 有序去重
→ 同一锁内读取 ready Chunk、关闭 Session、fingerprint 比较/完整刷新
→ BM25Okapi.get_scores
→ finite score 校验
→ token overlap
→ 可选 doc_id filter
→ 稳定排序、Top-K
→ 安全 JSONL
→ 共享 Chunk 响应
```

### 6. 真实向量与 BM25 对比

实验使用 Day 9 的 8 页自撰制度语料、固定 500/100、Top 5、同一 24 个 Chunk ID。

| 范围 | 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---|---:|---:|---:|
| 全部 12 题 | 向量 | 0.750 | 0.917 | 0.812 |
| 全部 12 题 | BM25 | 0.833 | 1.000 | 0.882 |
| 精确编号 4 题 | 向量 | 0.750 | 1.000 | 0.812 |
| 精确编号 4 题 | BM25 | 1.000 | 1.000 | 1.000 |
| 语义改写 4 题 | 向量 | 0.500 | 0.750 | 0.625 |
| 语义改写 4 题 | BM25 | 0.500 | 1.000 | 0.646 |
| 混合表达 4 题 | 向量 | 1.000 | 1.000 | 1.000 |
| 混合表达 4 题 | BM25 | 1.000 | 1.000 | 1.000 |

负样本返回率：向量 `1.000`，BM25 `0.000`。`6203` 在向量为第 4、BM25 为第 1；
精确编号是当前 BM25 最明确的优势场景。语义改写中 BM25 依赖局部字面重合，不具备真正
语义理解。详细逐题结果和局限见 `docs/day10-vector-vs-bm25.md`。

结论只适用于当前小型受控语料，不证明 BM25 普遍优于向量，也不是 Hybrid/RRF 收益证据。

### 7. 验收证据

- 安装：`rank-bm25==0.2.2` 成功，`pip check` 为 `No broken requirements found.`。
- BM25 单元/API：`47 passed in 20.43s`。
- 真实 PostgreSQL：`1 passed in 2.54s`，覆盖中文、复合编号、Top-K 前 doc_id、
  add/update/delete 指纹刷新和 Document→Chunk cascade cleanup。
- 真实 PostgreSQL + BGE + Qdrant 对比：`1 passed in 41.29s`，24 个共享 Chunk ID，
  临时 PostgreSQL 记录和 `day10_compare_*` collection 已清理。
- Day 10 真实模块合并复验：`4 passed in 21.80s`，覆盖真实 PostgreSQL 刷新/过滤、
  清理防御和真实 BGE/Qdrant 对比，指标与首次运行完全一致。
- 最终标准套件：`264 passed, 9 skipped in 21.49s`；9 个跳过均为显式真实集成开关。
- 开启 PostgreSQL、Qdrant、本地 BGE 和 RAG 全部真实集成开关后：
  `273 passed in 59.39s`，无跳过、无失败。
- `compileall -q backend`、`git diff --check` 通过；当前失败测试为 0。
- 未调用 DeepSeek、千问或其他付费 API。

验收命令：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q backend
git diff --check

$env:RUN_POSTGRES_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_bm25_postgres.py -v

$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/test_bm25_comparison_integration.py -v -s
```

### 8. 错误、失败尝试与风险

- 第一次真实 PostgreSQL 测试有一次失败：测试错误假设完整复合编号只返回一个 Chunk；
  按既定 tokenizer，复合标识同时拆出共享前缀，因此其他 Chunk 也可低分重合。目标仍
  正确 Top 1；测试改用唯一数字组成部分验证刷新后通过。未改变产品规则。
- `rank-bm25` 首次安装在网络受限沙箱失败，获得允许后从已配置 PyPI 镜像成功安装。
- 每次请求仍全量扫描 ready Chunk 计算指纹；多 Uvicorn worker 各持索引，不适合大规模。
- unigram/bigram 可能产生常见单字的宽泛重合；未做停用词、词典或同义词。
- PostgreSQL BM25 corpus 与 Qdrant vector corpus 无自动同步、跨存储事务、outbox、删除
  同步或一致性修复；真实对比通过相同 Chunk ID 显式控制公平性。
- 历史 `%TEMP%` pytest ACL 问题未修复；本轮使用独立可写 basetemp，0 warning。
- Git 仍有 LF→CRLF 提示；`git diff --check` 无 whitespace error，`.gitattributes` 待确认。
- `query_sha256` 不等于匿名化。

### 9. 不可违反的约束

- 不修改 `PLAN.md`，除非用户明确授权；不开始 Day 11。
- 不实现 RRF、Hybrid、mode 参数、score 融合、Rerank 或 BM25→Chat/RAG 接入。
- 不直接相加或比较 BM25/Cosine score；不把 BM25 score 当概率。
- 不新增 BM25 表、磁盘索引、无鉴权 refresh API、jieba 或 PostgreSQL/Qdrant 自动同步。
- 不修改 `/chat`、RAG `0.46`、sources/SSE、上传、显式 Qdrant 索引或 collection schema。
- Python 3.11；后端位于 `backend/`；公共函数有类型标注；完成前运行 pytest。
- 不读取、输出、暂存或提交 `.env`、API Key、数据库密码、`.agents/`、`.pytest-tmp/`、
  `data/models/` 或测试临时目录。
- 不调用付费 API，除非获得新的明确授权。
- Day 10 Git 检查点只包含本阶段文件；未来 Git 写操作仍需由用户任务授权。

### 10. 下一步（最多 5 项）

1. Day 10 已收口，不再扩展其范围。
2. 等待用户明确授权 Day 11 Hybrid/RRF。
3. Day 11 开始前复核远端、工作区和 `PLAN.md` 边界。
4. 继续排除 `.env`、`.agents/`、模型缓存和测试临时目录。
5. 不得提前开始 Rerank、LangGraph 或后续计划能力。

### 11. Day 10 客观验收清单

- [x] 固定 `rank-bm25==0.2.2`。
- [x] 独立 `POST /retrieval/bm25/search`，严格契约与 Day 9 一致。
- [x] 中文、英文、数字、复合编号 tokenizer；query 去重、corpus 保留 TF。
- [x] ready Chunk loader、Session 边界、全局 IDF、指纹复用/刷新、fail closed。
- [x] `get_scores()` + token overlap；不使用 `get_top_n()` 或 `score > 0`。
- [x] doc_id 在 Top-K 前，稳定排序，有限 raw score。
- [x] 空库/无 token/无 overlap/未知 doc_id 为 200 空数组。
- [x] 数据库 503、索引/score 500、`/health` lazy、安全 JSONL。
- [x] 真实 PostgreSQL与共享 Chunk 的真实向量/BM25 对比通过并完成清理。
- [x] 对比文档包含逐题 rank、Hit@1、Hit@5、MRR@5 和负样本返回率。
- [x] 完整 pytest、pip check、compileall、diff check 通过。
- [x] Chat/RAG/Day 9 功能无回归；PLAN 仅更新 Day 10；未实现 Day 11；未调用付费 API。
- [x] Day 10 实现已提交，PLAN 状态已更新；远端推送已获用户授权，因当前主机无法连接
  GitHub 443 暂未完成。

## B. 300 字以内快速恢复摘要

`D:\2019\rag-agent` 的 Day 1-10 已完成。Day 10 实现提交 `a614a36`：独立 BM25 API、
NFKC 中英混合 tokenizer、ready Chunk 指纹刷新、overlap 门控、Top-K 前 doc_id、安全
JSONL。相同 24 Chunk 的 12 题对比：向量 0.750/0.917/0.812，BM25
0.833/1.000/0.882；标准测试 264 passed/9 skipped，全部真实集成开启后 273 passed。
PLAN 已更新且 Day 11 未开始，无付费 API；继续排除敏感与无关目录。

## C. 新会话启动提示词

```text
仓库 D:\2019\rag-agent。先完整阅读 HANDOFF/STATUS/DECISIONS/TODO/AGENTS/README/PLAN、
architecture、Day 10 报告及 HANDOFF 列出的 Day 10 代码测试。Day 10 实现提交为
a614a365ff52b8fa087ce651614c23e2e1017c0b；标准测试 264 passed/9 skipped，全部真实
集成开启后 273 passed。PLAN 已勾选 Day 10，Chat/RAG/Day 9 检索无功能回归。禁止读取
.env 或纳入无关 .agents/、data/models/ 和测试临时目录。先只读核验工作区与远端，再等待
唯一动作；不要直接开始 Day 11、执行未授权 Git 写操作或调用付费 API。
```
