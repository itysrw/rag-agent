# 项目完整交接包

更新时间：2026-10-28（Asia/Shanghai）
仓库：`D:\2019\rag-agent`
当前模式：**功能开发暂停，仅交接。新会话先只读确认状态，再等待用户指定唯一动作。**

> 本文件 A/B/C 是独立恢复入口，不依赖聊天记录，并取代旧的 Day 10 启动提示。
> “实现完成”“计划标记完成”“测试证据”“Git 发布”必须分别描述。
> 未知信息标记为“待确认”，不能以历史记录或本地 tracking ref 填补。

## A. 详细交接文档

### 1. 项目最终目标

构建用于作品展示、简历和面试讲解的企业知识库 RAG Agent：

- FastAPI 后端、Streamlit 前端；
- PostgreSQL 保存 Document/Chunk，Qdrant 保存向量；
- 本地 BGE Embedding、向量/BM25/Hybrid/RRF，后续 Rerank；
- OpenAI-compatible LLM 生成带可信引用的 JSON/SSE 答案；
- 后续 LangGraph 工具编排、多轮记忆、评测、trace 和完整 Docker Compose 部署。

`PLAN.md` 是每日范围和顺序基线。Day 1–11 已完成，Day 12 及以后未开始。
Rerank、LangGraph、记忆、评测 UI、Streamlit、完整一键部署仍是目标，不是当前交付物。

### 2. Git 与工作区精确快照

下表为本次交接的本地只读核验；本轮未查询实时远端。

| 项目 | 精确状态 |
|---|---|
| 工作目录/终端 | `D:\2019\rag-agent`，PowerShell |
| 分支 | `master` |
| 最近有效提交/本地 HEAD | `98ff9d3860e845f47df91e366811663c71a0ec5d`，`docs: mark Day 10 complete in plan` |
| Day 10 实现提交 | `a614a365ff52b8fa087ce651614c23e2e1017c0b`，`feat: complete Day 10 BM25 retrieval` |
| 本地 origin/master tracking ref | `98ff9d3860e845f47df91e366811663c71a0ec5d` |
| 本地 tracking 关系 | `master...origin/master`，无 ahead/behind 标记 |
| GitHub 当前实时 HEAD | **待确认**，不能从 tracking ref 推断 |
| 暂存区 | 空 |
| Day 11 发布状态 | 工作区实现，未暂存、未提交、未推送 |
| PLAN 状态 | 2026-10-28 用户确认审查、测试与修复通过，Day 11 四项及开发日志已勾选 |
| 下一天 | Day 12 未开始，没有执行授权 |

提交顺序：

~~~text
33689d31018fcf35b7526fff33a1649f7a0430ac  feat: complete Day 8 basic RAG
4cccbe26688de33ff25756fc10584060c82fd03f  feat: complete Day 9 retrieval tuning
f3ca9ec1541d5e774f1eae92217d32160f15153f  docs: refresh Day 9 published status
5928fa0034aa0378ae164fe9bd1f38e0ca27b807  docs: mark Day 9 complete in plan
a614a365ff52b8fa087ce651614c23e2e1017c0b  feat: complete Day 10 BM25 retrieval
98ff9d3860e845f47df91e366811663c71a0ec5d  docs: mark Day 10 complete in plan
~~~

既有记录：Day 11 开工门禁已推送 Day 10 两提交并独立核对远端。
2026-10-27 收尾再次查询 GitHub 时 443 失败；当前实时 HEAD 仍待确认。
本次交接不执行 fetch、push、commit 或暂存。

以下仓库内路径均相对 `D:\2019\rag-agent`。相关未提交文件共15个：

8个 tracked 修改：

~~~text
DECISIONS.md
HANDOFF.md
PLAN.md
README.md
STATUS.md
TODO.md
backend/app/main.py
docs/architecture.md
~~~

7个相关 untracked 文件：

~~~text
backend/app/api/hybrid.py
backend/app/services/hybrid.py
backend/tests/test_hybrid.py
backend/tests/test_hybrid_api.py
backend/tests/test_hybrid_comparison_integration.py
docs/day11-hybrid-comparison.md
docs/docker-desktop-recovery.md
~~~

另有无关 untracked 内容 `.agents/` 和 `就业推荐表_完整填充版.pdf`。
必须排除，不读取、不打包、不提交。原有6份交接文档的修改已合并保留，不能重置。
不要使用 `git add .`。本次交接仅整理文档，保留现有代码、测试和 PLAN 完成标记。

本次交接实际修改：`HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`README.md`、
`docs/architecture.md`。没有新增技术决策，没有修改代码、测试、PLAN、依赖或Compose。

### 3. 已完成内容与当前实现

| 阶段 | 已实现事实 |
|---|---|
| Day 1–3 | 仓库/架构、模块化 FastAPI、配置日志、OpenAI-compatible LLM、JSON/SSE |
| Day 4–5 | PDF/MD/TXT 上传解析、PostgreSQL Document/Chunk、按页 token 切分、事务持久化 |
| Day 6 | 固定本地 BGE revision、CPU、批量32、512维归一化、BGE tokenizer 独立预检 |
| Day 7 | unnamed 512/Cosine Qdrant、显式幂等索引、向量检索 |
| Day 8 | 基础 RAG、固定 Top5 与0.46生成门控、可信 sources、无相关内容直接拒答 |
| Day 9 | 严格 top_k 1..20、Qdrant内 doc_id过滤、安全JSONL、300/500/800真实实验 |
| Day 10 | 独立BM25 API、混合分词、PostgreSQL指纹刷新、overlap门控、真实两路对比 |
| Day 11 | 独立Hybrid API、标准RRF、身份/一致性检查、安全日志、真实三路对比与回归基线 |
| 2026-10-28 | 用户确认审查/测试/修复通过，已授权标记Day11任务与开发日志完成 |

上传不自动生成向量或索引，仍需显式命令。PostgreSQL/Qdrant 没有跨存储事务、
outbox、删除同步或一致性修复。应用启动与 `GET /health` 不探测外部依赖。

### 4. 接口与关键参数

| 方法与路径 | 请求/当前行为 |
|---|---|
| `GET /health` | `200 {"status":"ok"}`，不探测数据库/Qdrant/BGE/LLM |
| `POST /documents/upload` | multipart字段 `file`，PDF/MD/TXT，成功201 |
| `POST /retrieval/search` | query/top_k/doc_id；Chunk响应，score为Cosine |
| `POST /retrieval/bm25/search` | 同一请求/Chunk结构，score为raw BM25；无token重合返回空 |
| `POST /retrieval/hybrid/search` | 同一结构，两路各取20再融合截取，score为RRF |
| `POST /chat` | message/stream；JSON answer/model/sources 或 SSE delta→sources→DONE |

共享模型在 `backend/app/api/retrieval.py`：

- `RetrievalSearchRequest`：query strip后1..4096，top_k严格整数1..20、默认5，
  doc_id为单UUID或null，`extra="forbid"`。
- 拒绝 top_k 的 bool、字符串、浮点、null、0、21。不开放 mode、candidate_k、k、weight。
- `RetrievedChunkResponse`：chunk_id、doc_id、chunk_index、content、page、filename、
  metadata、score；`RetrievalSearchResponse` 为 `{"results":[...]}`。
- Hybrid的 vector_rank/bm25_rank 仅内部使用，不进入HTTP；不返回向量。
- 合法无匹配 doc_id 是200空数组，不引入404。
- 上传上限20MiB、PDF最多500页；PDF页边界保留，默认按页500/100 o200k token切分。

Hybrid错误契约：

| HTTP | 情况 |
|---:|---|
| 422 | 请求非法或BGE query token超限 |
| 500 | BM25内部索引/计算失败，或内部HybridError |
| 502 | 非法Qdrant结果、分支重复ID、跨库同ID payload冲突 |
| 503 | Embedding/Qdrant/PostgreSQL/BM25不可用、配置无效或collection不匹配 |
| 200空数组 | 两路均无结果，或合法过滤条件无结果 |

错误只给安全detail，不暴露原始异常、正文或凭据。

### 5. 精确代码位置、函数和已修改点

#### backend/app/services/hybrid.py（新增）

- `RRF_RANK_CONSTANT=60`、`HYBRID_CANDIDATE_K=RETRIEVAL_TOP_K_MAX=20`、
  `HYBRID_SEARCH_EVENT="hybrid_search_completed"`。
- DTO：`HybridRetrievedChunk`；异常：`HybridError`、`HybridResultError`。
- `reciprocal_rank_fusion(vector_results, bm25_results, *, top_k, rank_constant=60)`。
- `HybridRetrievalService.search(query, *, top_k=5, doc_id=None)`。
- `get_hybrid_retrieval_service()`：lru_cache惰性工厂，复用既有两路工厂。
- 内部函数：`_ranked_branch()`、`_validated_payload()`、`_validated_metadata()`、
  `_same_payload()`、`_best_rank()`、`_validated_top_k()`、
  `_validated_rank_constant()`、`_log_search_event()`。

流程：

1. 两路调用前防御性校验 top_k、query、doc_id。
2. 同步向量 `search(query, top_k=20, doc_id=doc_id)`，再调用BM25同一参数；无并发。
3. 按chunk_id聚合并集。分支内重复ID拒绝；跨路同ID比较doc_id、chunk_index、content、
   page、filename、metadata，原始score不参与比较。
4. metadata键序无关，但标量类型和值必须一致；`true`、`1`、`1.0` 不可互换。
5. 标准等权 `Σ 1/(60+rank)`，rank从1开始，缺席一路贡献0；原始分支score不参与。
6. 按 `(-rrf_score, best_rank, str(doc_id), chunk_index, str(chunk_id))` 排序后截取。
   不修改输入列表；结果metadata复制，防止共享修改。
7. 任一路失败整体失败；单路独有Chunk允许返回。成功/空结果均尝试安全日志。

#### backend/app/api/hybrid.py（新增）

- `require_hybrid_retrieval_service()`：惰性依赖，配置ValidationError安全转503。
- `search_hybrid()`：独立接口、共享输入输出、上述错误分类，隐藏内部rank。

#### backend/app/main.py（修改）

只新增 hybrid_router 导入，在 `create_app()` 注册路由。
`lifespan()` 没有增加模型加载、数据库或Qdrant探测。

#### 前序支撑文件（Day11未修改）

| 文件 | 关键函数/职责 |
|---|---|
| `backend/app/services/retrieval.py` | `RetrievalService.search()`、`get_retrieval_service()` |
| `backend/app/services/bm25.py` | `tokenize_bm25()`、`load_bm25_chunks()`、`build_corpus_fingerprint()`、`build_bm25_snapshot()`、`BM25Service.search()`、`BM25Service._refresh_snapshot()`、`get_bm25_service()` |
| `backend/app/services/qdrant_store.py` | `QdrantVectorStore.initialize_collection()/validate_collection()/upsert_chunks()/search()`、`_parse_scored_point()` |
| `backend/app/services/rag.py` | `RAGService.prepare()/complete()/stream()`、`build_sources()`、`build_rag_messages()`、来源标记清理 |
| `backend/app/core/logging.py` | `JSONL_LOG_MARKER="jsonl"`、`configure_logging()`、互斥handler |
| `backend/app/core/config.py` | 独立Settings/LLMSettings/DatabaseSettings/EmbeddingSettings/QdrantSettings/RAGSettings |
| `backend/app/core/database.py` | `get_engine()`、`get_session_factory()`，惰性同步SQLAlchemy |

### 6. 日志与安全边界

Hybrid完成事件字段：

~~~text
event=hybrid_search_completed
query_sha256, query_len, top_k, candidate_k, rrf_rank_constant, filter_doc_id,
vector_result_count, bm25_result_count, result_count,
results[{rank,chunk_id,doc_id,vector_rank,bm25_rank,rrf_score}]
~~~

Hybrid事件不含query原文、正文、tokens、metadata、向量、原始分支score或凭据。
正常请求产生向量、BM25、Hybrid三条完成日志。两路既有日志仍含各自score，
不能误写成“所有日志均无原始分数”。

`configure_logging()` 输出到stderr，没有既定项目日志文件。human handler排除JSONL，
专用 `{message}` handler只处理JSONL，避免截断与重复。
序列化失败只记 `Hybrid search event serialization failed.`，不泄露异常详情或丢弃结果。
query_sha256不等于匿名化。

### 7. 已确认技术决策与原因

完整记录为 `DECISIONS.md` D-001至D-049；本次交接不新增或推翻决策。

| 决策 | 结论与原因 |
|---|---|
| D-001/D-014 | 每日范围与文档检查点，防止跨Day实现或把计划当成果 |
| D-016/D-022 | 同步SQLAlchemy；先flush Document再flush Chunk，避免真实PostgreSQL外键失败 |
| D-019/D-020 | o200k_base、按页500/100；可复现token与可靠页码 |
| D-024/D-025 | 固定本地BGE、CPU512维；BGE tokenizer独立预检，禁止静默截断 |
| D-028/D-029 | 显式索引、Point ID=Chunk UUID、unnamed512/Cosine；隔离上传失败面并支持幂等 |
| D-032–D-037 | RAG固定0.46，system规则+user JSON Context，后端控制来源与拒答 |
| D-039/D-040 | top_k严格1..20，Qdrant先过滤doc_id再取TopK，返回再校验 |
| D-041 | JSONL与human互斥，不记录query/正文 |
| D-043 | NFKC+casefold、中文unigram/bigram、英文数字复合编号；query去重，corpus保留TF |
| D-044 | ready Chunk全局快照+SHA256指纹，完整构建后原子替换；刷新失败不返回旧快照 |
| D-045 | get_scores与token-overlap；保留相关零/负分，不补齐无关零分 |
| D-046 | BM25独立API，只比较排名，不直接比较Cosine/BM25 raw score |
| D-047 | 等权RRF60、两路各20；避免量纲差异，候选深度与返回数分离 |
| D-048 | UUID身份，payload类型/值一致，冲突安全失败；允许单路独有项 |
| D-049 | 独立Hybrid、惰性依赖、安全日志和客观评测；不提前改/chat或做Rerank |

明确不采用：直接相加/归一化两路raw score、加权RRF、问题类型路由、统一mode、
静默降级、按正文或filename/page去重、RRF套0.46、根据小样本反复调k。
以上是已否决或未选择的方案，不是都曾执行并证明失败的实验。

### 8. 审查修复与回归结构

- `_same_payload()` 显式比较metadata标量类型，避免 `True == 1 == 1.0` 漏报冲突。
  测试：`test_metadata_equal_values_with_different_types_are_conflicts`。
- `_assert_experiment_acceptance()` 校验问题身份/顺序、聚合指标、逐题排名/候选详情、
  候选统计及负样本返回率，不只检查聚合指标。
- 默认可运行的两项回归：
  `test_experiment_acceptance_rejects_candidate_detail_drift`、
  `test_experiment_acceptance_rejects_query_identity_order_drift`。

测试位置：

1. `backend/tests/test_hybrid.py`：公式、一基rank、缺席分支、分数独立、重复/冲突、
   metadata类型、稳定平局、TopK 1/5/20、候选深度、失败不降级、日志与输入不变性。
2. `backend/tests/test_hybrid_api.py`：共享请求、200/422/500/502/503、安全错误、
   内部rank隐藏、health lazy、OpenAPI无额外调参字段。
3. `backend/tests/test_hybrid_comparison_integration.py`：
   `test_real_vector_bm25_and_hybrid_on_identical_chunks()`、
   `_positive_metrics()`、`_query_details()`、`_query_identities()`、
   `_candidate_statistics()`、`_insert_corpus()`、`_delete_document()`。
   基线常量：EXPECTED_POSITIVE_METRICS、EXPECTED_QUERY_IDENTITIES、EXPECTED_QUERY_DETAILS、
   EXPECTED_CANDIDATE_STATISTICS、EXPECTED_NEGATIVE_RETURN_RATE。
4. 复用 `backend/tests/day9_tuning_corpus.py`、`backend/tests/day10_bm25_cases.py`；
   不为“得到更好结果”现场改问题、命中标准或分词规则。

### 9. 测试证据：日期、版本与当前失败

| 阶段/日期 | 实际结果 | 证据边界 |
|---|---|---|
| Day10标准 | 264 passed / 9 skipped | 历史基线 |
| Day10全真实 | 273 passed | 历史基线 |
| Day11首次真实三路，2026-10-27 | 1 passed in 28.65s | PostgreSQL+本地BGE+REST Qdrant，含真实Hybrid API/doc_id/空结果 |
| Day11实现标准，2026-10-27 | 333 passed / 10 skipped in 14.39s | 旧版本记录 |
| 最近全真实，2026-10-27 | 343 passed in 35.42s | 当时无跳过/失败，不是当前版本重新全量验收 |
| 最新标准，2026-10-28 | **335 passed / 10 skipped in 57.73s** | 上一轮进度收口实际执行，10项真实集成默认跳过 |
| 本次交接 | 文件/Git/文档核验 | 未重新运行代码测试或真实集成 |

当前已知失败测试：0，依据最近一次实际标准测试。
当前代码全部真实开关重新验收结果：**待确认**。
不能推算新全真实通过数，也不能把历史343写成当前全部测试重新通过。

既有 `pip check`、`compileall -q backend` 通过。交接收尾单独做diff与本地链接检查。
保留既有LF→CRLF提示，不写成whitespace error。
2026-10-27实验finally已清理，独立核验临时Document/Chunk/collection均0；
这是历史清理证据，本次未连接数据库再次检查。未调用付费API，RAG集成使用LLM替身。

### 10. 三路真实指标与局限

8页自撰制度手册，500/100、o200k_base、24个相同Chunk ID/payload；
真实PostgreSQL+临时Qdrant；12正样本（精确/语义/混合各4）+3负样本。
两路候选最多20，评估Top5；NFKC+strip后正文包含固定expected_phrase才算命中。

| 方法 | Hit@1 | Hit@5 | MRR@5 | 负样本返回率 |
|---|---:|---:|---:|---:|
| 向量 | 0.750 | 0.917 | 0.812 | 1.000 |
| BM25 | 0.833 | 1.000 | 0.882 | 0.000 |
| Hybrid | 0.917 | 1.000 | 0.944 | 1.000 |

Hybrid语义改写组为0.750/1.000/0.833，精确/混合组三项均1.0。
逐题Hybrid首次命中排名：`1,1,1,1,3,1,1,1,1,1,1,1`。
平均候选Jaccard=0.567；逐题累计仅向量 87、仅 BM25 24（query/Chunk对数）；
独有正确候选命中均0；补回向量Top5漏检1题、补回BM25漏检0题。
远程接入题的目标在向量候选第7、BM25第3、Hybrid第3，收益来自排序重组。

完整逐题问题、expected_phrase、三路排名及重合率见
[Day11实验](docs/day11-hybrid-comparison.md)，并由测试常量固定回归。
这是24 Chunk受控小样本；审计标识被BGE高度压缩，不能外推到自然长中文、表格或多跳。
BM25中文单字重合较宽，RRF不提供拒答，不能宣称Hybrid普遍优于单路。
未据此调整生产切分默认值、k、权重或tokenizer。

### 11. 已尝试但失败的方案

| 实际尝试 | 结果与结论 |
|---|---|
| 受限网络安装rank-bm25 | 初次失败，获网络允许后成功；不是版本冲突 |
| 用完整复合编号断言BM25只命中一个Chunk | 分词会拆共享前缀；改用唯一数字验证刷新，未改产品分词 |
| 默认%TEMP%/仓库pytest临时目录 | 曾大量WinError5；改Public独立basetemp，未修复系统ACL |
| 只重命名Docker/run再启动 | 暴露Secrets Engine第二处socket故障，不能作为完整修复 |
| 关闭EnableDockerAI/disable model-runner | 监听器仍初始化；引擎不可用时CLI也不能完成禁用 |
| 仅升级Docker4.49→4.97 | 安装成功，但默认路径engine.sock rename仍失败；升级不是完整修复 |
| 普通/管理员目录操作、cipher /d、WSL访问 | 没形成可用默认路径修复；EFS和1920仅为观察，不是根因证明 |
| 升级后首次沿用C盘数据位置 | 引擎启动但容器空；D盘旧VHDX仍在，恢复配置后旧容器重新可见 |
| 内存Qdrant预评估 | 只能作初步证据，后续真实服务实验通过，不以其替代验收 |
| GitHub实时查询 | 2026-10-27收尾443失败，保留待确认，不用tracking ref填空 |

### 12. 当前错误、日志与Docker规避

当前外部问题：默认socket故障未根治、GitHub实时HEAD未确认、历史pytest ACL未系统修复。
Docker/容器/后端当前是否运行：**待确认**；最后运行及重启成功验证为2026-10-27，
本次交接不探测或重启。没有新的代码失败报告，不把外部错误归因于Hybrid代码。

GitHub最近失败原文：

~~~text
fatal: unable to access 'https://github.com/itysrw/rag-agent.git/': Failed to connect to github.com port 443 after 21063 ms: Could not connect to server
~~~

原Docker4.49错误：

~~~text
starting services: initializing Inference manager: listening on unix://C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: remove C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: The file cannot be accessed by the system. (listener: The filename, directory name, or volume label syntax is incorrect.)
~~~

升级后仍观察到：

~~~text
starting services: initializing Secrets Engine: listening on unix://C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock: rename C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock.stale: The file cannot be accessed by the system. (listener: The file cannot be accessed by the system.)
~~~

当前安装文件版本4.97.0.244584；最后验证Engine29.9.2。
源目录出现Encrypted/ReparsePoint属性，不能据此断言中文用户名、EFS、内核或磁盘损坏
就是根因。未改变全局ACL/加密策略，未上传诊断数据。

默认日志目录：`C:\Users\袁伟鑫\AppData\Local\Docker\log\host`；
规避后：`D:\Docker\codex-runtime-20261027\Docker\log\host`。
旧报错曾在 `com.docker.backend.exe.log`；最新具体文件和时间须届时只读核验，
不批量输出日志，不读取Secrets Engine凭据存储。

已验证方案与备份：

- 仓库外脚本 `D:\Docker\Start-DockerDesktop.ps1`，2378字节，本次核验存在，未执行。
- 仅给新Docker进程设置 `LOCALAPPDATA=D:\Docker\codex-runtime-20261027`；
  恢复调用shell原值，不改系统/用户环境变量，仍用原Roaming配置。
- 脚本要求无Docker进程；将专用路径内仅含零字节端点的Docker/run与docker-secrets-engine
  目录重命名保留；发现非零文件、子目录或链接则停止，不强杀进程或删除目录。
- 已验证启动→识别原容器→正常停止→脚本重启→容器恢复→真实集成通过。
- 原盘 `D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx`。
- 停机完整备份 `D:\Docker\docker_data.codex-pre-recovery-20261027.vhdx`，
  `5,602,541,568` 字节，恢复前SHA256与原盘一致；本次仅核验存在/大小。
- `CustomWslDistroDir=D:\Docker\DockerDesktopWSL` 已恢复。
- 原配置备份 `C:\Users\袁伟鑫\AppData\Roaming\Docker\settings-store.codex-backup-20261027.json`。
- 升级后备份 `D:\Docker\settings-store.codex-post-upgrade-20261027.json`。
- C盘新空盘、旧runtime目录和完整VHDX备份均保留。失败移动创建的空目录不算完整备份。
  没有factory reset、WSL unregister、volume prune或数据库覆盖。

脚本和备份不在Git仓库，复制仓库不会自动携带；异机可用性待确认。
详细记录见 [Docker恢复](docs/docker-desktop-recovery.md)。

### 13. 启动、测试与核验命令

以下从 `D:\2019\rag-agent` 执行。**命令仅供后续恢复，不是第一轮执行授权。**

安装/后端：

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
~~~

Python3.11（最近测试3.11.15）；sentence-transformers==5.3.0、qdrant-client==1.18.0、
rank-bm25==0.2.2；Day11无新依赖。
BGE为 `BAAI/bge-small-zh-v1.5`，revision
`4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4`，CPU512维归一化、批量最多32。
固定查询instruction：`为这个句子生成表示以用于检索相关文章：`。
BGE512 token上限含特殊token，不能拿o200k长度代替预检。

获指定服务动作后，恢复已有容器：

~~~powershell
& 'D:\Docker\Start-DockerDesktop.ps1'
docker start rag-agent-postgres-1 rag-agent-qdrant
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' rag-agent-postgres-1 rag-agent-qdrant
~~~

脚本启动后等待引擎可用再启动容器；不重复启动正常引擎。
最后记录PostgreSQL healthy、Qdrant running，其他无关容器停止；本次未重新探测。
Compose仅编排PostgreSQL，新环境显式建表：

~~~powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m backend.app.models.init_db
~~~

已有环境不为只读确认重新建表。显式Qdrant操作：

~~~powershell
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
~~~

`<UUID>` 必须替换为用户指定文档，不编造或自动索引所有文档。
Embedding-only入口：`python -m backend.app.commands.embed_document --document-id <UUID>`，
不写Qdrant。Qdrant固定镜像qdrant/qdrant:v1.18.1、本机REST6333、命名卷
rag-agent-qdrant-data，正式collection默认documents；不自动recreate。

标准测试和静态命令：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pytest backend/tests/test_hybrid.py backend/tests/test_hybrid_api.py -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q backend
git diff --check
~~~

本机最新标准测试的实际命令（结果335/10）：

~~~powershell
$env:RUN_POSTGRES_INTEGRATION='0'
$env:RUN_QDRANT_INTEGRATION='0'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='0'
$env:RUN_RAG_INTEGRATION='0'
$env:PYTEST_DEBUG_TEMPROOT='C:\Users\Public\codex-pytest-rag-agent-day11'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=C:\Users\Public\codex-pytest-rag-agent-day11\progress-closeout-20261028 -p no:cacheprovider
~~~

未来重跑换新且独占的basetemp；pytest可能清理指定目录，不复用未知路径，
不递归清理整个Public/仓库/缓存树。Public写入可能需要运行环境批准。

真实实验与全部集成（有必要且获指定动作后）：

~~~powershell
$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_hybrid_comparison_integration.py -v -s

$env:RUN_RAG_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v
~~~

必要时附加新basetemp。离线标记需已有模型，不擅自改版本或上限；RAG测试使用LLM替身。
实验创建day11_hybrid_compare_<uuid> collection与
day11-hybrid-comparison-handbook.txt临时Document/Chunk，finally删除并校验清理。

只读Git核验：

~~~powershell
git status --short --branch
git rev-parse HEAD
git rev-parse origin/master
git log -6 --oneline
git diff --cached --name-only
git diff --name-only
git diff -- PLAN.md
~~~

若另行要求实时远端确认，可 `git ls-remote origin refs/heads/master`；
失败记录待确认，不以fetch/push或修改网络配置替代。

### 14. 不可违反的约束

- 遵守AGENTS.md：Python3.11、backend/、公开函数类型标注、pytest、按授权每日范围。
- 不重新实现Day1–11，不推翻D-001至D-049，不把未来能力写成已完成。
- PLAN的Day11已完成；本次交接不改计划，未来修改需用户明确要求。
- 默认保护/chat、JSON/SSE/sources、RAG0.46、两路既有API、上传、显式索引、Qdrant schema；
  只有新唯一任务明确要求时再讨论改变。
- 不读取/输出/暂存/提交.env、API Key、数据库密码或凭据；不读取无关.agents/、PDF、
  .pytest-tmp/、.pytest_cache/、data/models/和模型/测试缓存内容。
- 本次不修改代码、测试、PLAN、模型缓存、依赖、数据库schema、Compose或全局设置。
- 不调用付费API，不自行补充真实LLM冒烟，不上传诊断或发送外部消息。
- 暂存/提交/推送、Day12、服务重启是独立动作，不能从交接请求推导授权。
- 保留未提交变更；禁用reset --hard、checkout --、自动recreate_collection、prune、
  删除用户数据或覆盖备份。命令示例不是执行许可。

### 15. 待完成与待确认

| 优先级 | 内容 | 边界 |
|---|---|---|
| 唯一下一步 | 新会话只读恢复Day11检查点 | 先复述、列矛盾、最多5步，再等待用户 |
| 后续待指定 | Day11 Git发布 | 未暂存/提交/推送，不自行选择提交或混入排除项 |
| 后续待指定 | Day12 Rerank | 方案、模型/API、费用、接入边界待用户指定 |
| 待确认 | GitHub实时HEAD | 最近443失败，tracking ref不作实时结论 |
| 待确认 | Docker/容器/后端当前状态 | 最后成功记录10月27日，本次未探测 |
| 待确认 | 当前代码重新全真实验收 | 当前标准335/10，历史343不等于当前完整重跑 |
| 长期延后 | 自然语料、BM25扩展性、多worker、outbox/同步 | 不能在交接顺手实现 |
| 长期延后 | 默认socket、EFS/ACL、LF/CRLF、迁移方案 | 未修复，不回退Day11完成标记 |

### 16. 下一步具体操作（最多5步）

1. 按C部分阅读交接、状态、决策、计划、架构、实验与相关代码，不执行示例写操作。
2. 只读Git核对分支、HEAD、tracking ref、空暂存区、8个tracked修改/7个相关新增，
   确认两个排除项不混入交付。
3. 对照PLAN四项/日志、335/10与历史343、回归常量及Docker仓库外脚本依赖；
   列矛盾或缺失，未知项保留待确认。
4. 复述目标、已完成、实现、Git、决策原因、失败方案、报错、测试、约束和风险。
5. 状态确认后停止，等用户指定唯一动作；再确定最小改动与验收，不合并发布和Day12。

当前下一步最小改动：**无代码/计划改动，无Git写操作，无服务或外部状态变更**。

### 17. 完成判定与验收标准

本次实际核验：`git diff --check` 通过；本地Markdown失效链接0；B部分摘要275字符。
PLAN、6个Day11相关代码/测试文件、requirements与Compose共9个文件的SHA256与交接前一致。
本地HEAD/tracking ref未变，暂存区仍空，相关工作区清单仍为8个tracked修改+7个新增文件。
本次未重新运行代码测试、真实集成或服务探测。

本交接包：

- A/B/C能独立恢复，精确保留文件、接口、函数、命令、参数、拒绝/失败方案。
- Git清单准确、暂存区空；Day11完成但未提交，实时远端待确认。
- 明确335/10（2026-10-28）和历史343（2026-10-27）版本/日期差异，不推算新通过数。
- PLAN Day11四项及开发日志已完成，Day12未开始。
- 保留默认socket错误、已验证规避、仓库外脚本、VHDX备份、运行时待确认信息。
- 6份核心文档一致，本地Markdown链接有效，git diff --check无whitespace error。
- 本轮仅文档，代码/测试、PLAN、依赖和Compose保持交接前原样，无暂存/提交/推送。

新会话第一轮：只读复述与交接/Git一致，列矛盾/待确认项及最多5步；
不重做、不预做、不自行选择发布/Day12；用户指定动作前无状态变更。

未来若获指定重新验收Day11：独立API、严格请求、各20、一基等权RRF60、UUID身份、
payload一致性、稳定排序、最终TopK、安全错误、不降级、安全日志、health惰性、
同corpus真实对比、finally清理、/chat与0.46不变；按实际结果记录，不强迫旧数字或收益。

## B. 300字以内快速恢复摘要

D:\2019\rag-agent，master与本地origin/master均为98ff9d3。Day1–11完成，Day11计划已勾选；15个相关文件未提交，暂存区空。最新标准335 passed/10 skipped；10月27日真实集成343 passed，未对当前版本重跑。Hybrid两路各20、等权RRF k=60，指标0.917/1.000/0.944。Docker用D:\Docker\Start-DockerDesktop.ps1，默认socket故障未根治。实时远端HEAD待确认。开发暂停；先只读核对，再等用户指定唯一动作。

## C. 新对话的第一条启动提示词

~~~text
这是已有项目的新工作会话，仓库 D:\2019\rag-agent。
功能开发已暂停。本轮唯一目标：只读确认 Day 11 完成检查点与交接包一致。

请先完整阅读：
1. HANDOFF.md（含 A/B/C）
2. STATUS.md、DECISIONS.md、TODO.md、AGENTS.md、README.md
3. PLAN.md（只读；Day 11 已完成，Day 12 未开始）
4. docs/architecture.md
5. docs/day11-hybrid-comparison.md、docs/docker-desktop-recovery.md
6. backend/app/services/hybrid.py、backend/app/api/hybrid.py、backend/app/main.py
7. backend/tests/test_hybrid.py、backend/tests/test_hybrid_api.py、
   backend/tests/test_hybrid_comparison_integration.py
8. 如需核对前序契约，再阅读 HANDOFF.md 列出的共享请求、向量、BM25 和 RAG 文件。

已知基线：
- master 本地 HEAD 与 origin/master tracking ref 均为
  98ff9d3860e845f47df91e366811663c71a0ec5d。
- Day 10 实现提交 a614a365ff52b8fa087ce651614c23e2e1017c0b，既有记录已推送。
- 最新标准测试：2026-10-28，335 passed/10 skipped。
- 最近一次全部真实集成：2026-10-27，343 passed；不是当前代码重新全量验收。
- Day 11 经用户确认审查、测试与修复通过；PLAN 四项和开发日志已勾选。
- 8 个 tracked 修改、7 个相关 untracked 文件，暂存区空，Day 11 未提交。
- 无关 .agents/ 和就业推荐表_完整填充版.pdf 必须排除。
- GitHub 实时 HEAD 待确认，不能用本地 tracking ref 替代。
- Docker 有 D 盘运行时规避方案，默认 C 盘 socket 故障未根治；当前运行状态待确认。

执行规则：
不重新实现已完成内容，不擅自推翻决策，不补全待确认信息。
不读取或输出 .env、凭据、无关 .agents/、模型/测试缓存或无关 PDF。
本轮不改代码、PLAN 或文档，不暂存/提交/推送，不重启服务、不运行测试，
不调用付费 API，不开始 Day 12；不把命令示例当作执行授权。

第一轮先复述项目目标、完成内容、实现契约、Git/工作区、决策原因、失败方案、
错误与规避方式、带日期的测试证据、约束和风险；列出矛盾/待确认项及最多5个步骤。
状态确认完成后等待我指定唯一动作，再执行；不得自行选择发布或 Day 12。

本轮验收标准：
复述与文件及只读 Git 核验一致，明确“Day 11已完成但未提交”、
335/10 与历史343的区别、PLAN已勾选、远端/运行时待确认和Docker规避方案；
在我指定下一动作前不产生仓库或外部状态变更。
~~~
