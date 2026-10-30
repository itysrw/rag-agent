# 架构说明

更新时间：2026-10-30（Asia/Shanghai）

当前实现为 Day14 的 LangGraph RAG 编排，复用 Day1–12 的既有业务服务。
2026-10-30 用户确认审查、测试与修复通过并授权同步状态、本地提交。
本提交在 codex/day14-langgraph 收录完整 Day14，精确 HEAD 由 git log -1 核验，
父提交为 Day12 的 3471277；未推送，未开始 Day15。
Day12 分支 3471277/master b68b590 是 2026-10-29 远端实时核验结果，本次未复查。

PLAN Day14 五项和开发日志已按本次要求标记完成；Day1–12 原标记保留，
Day13 及 Day15 以后的内容不变。Day13 仓库外学习证据此前已核验，本轮不重做。
工具调用、会话和记忆仍未实现。

2026-10-30 提交前完整标准 453 passed / 12 skipped（23.34s），
dotenv/外部服务连接均 0，无付费调用。
2026-10-29 真实局部 3 passed（160.84s），最新全部真实仍为 2026-10-28 的
413 passed；本次未重跑真实集成。原 OpenAPI/业务辅助函数一致证据保留日期，
17 个保护文件及已审查代码/测试未变，PLAN 仅更新 Day14 状态。

本地服务/离线模型可用性与临时数据清理均为 10月29验收记录，本次未操作服务或下载模型。
Docker 默认 socket 历史问题仍使用仓库外 D 盘规避。
恢复入口为 [完整交接包](../HANDOFF.md)；具体图、生命周期与验收见
[Day14 迁移报告](day14-langgraph-migration.md)。

## 当前实现架构

~~~mermaid
flowchart LR
    client["调用方 / Swagger UI"] --> api["FastAPI app<br/>backend/app/main.py"]

    api --> health["GET /health"]
    api --> chat["POST /chat"]
    api --> upload["POST /documents/upload"]
    api --> retrieval_api["POST /retrieval/search<br/>top_k 1..20 默认 5 · 可选 doc_id"]
    api --> bm25_api["POST /retrieval/bm25/search<br/>独立关键词检索"]
    api --> hybrid_api["POST /retrieval/hybrid/search"]
    api --> rerank_api["POST /retrieval/rerank/search"]
    rerank_api --> reranked["RerankedRetrievalService<br/>固定Hybrid20→Rerank5"]
    reranked --> hybrid
    hybrid_api --> hybrid["HybridRetrievalService<br/>向量后 BM25 · 各取 20"]
    hybrid --> query_embedding["embed_query()<br/>固定BGE查询instruction"]
    hybrid --> bm25_service
    hybrid --> rrf["chunk_id 聚合 + payload 一致性<br/>等权 RRF k=60 · 稳定排序 · 最终 top_k"]
    rrf --> hybrid_api

    chat --> rag["RAGService.complete / start_stream"]
    rag --> graph["LangGraph<br/>START 条件边 / retrieve_node / generate_node"]
    graph --> reranked
    rrf --> reranker["本地BGE CrossEncoder<br/>CPU / safetensors / Identity logit<br/>完整query / passage-only截断 / Top5"]
    reranker --> gate["生成层证据门<br/>原始vector_score≥0.46"]
    gate -->|"无 Context"| refusal["固定拒答<br/>不调用 LLM"]
    gate -->|"有 Context"| prompt["system 规则 + user JSON Context"]
    prompt --> llm["LLMClient messages<br/>OpenAI-compatible"]
    llm --> deepseek["DeepSeek V4 Flash<br/>仅 LLM"]
    gate --> sources["后端 sources<br/>filename + page"]

    upload --> storage["UUID.part 分块存储"]
    storage --> parser["PDF / Markdown / TXT 解析"]
    parser --> pages["PageText<br/>一基页码"]
    pages --> splitter["split_pages()<br/>o200k_base · 500/100 · 按页"]
    splitter --> chunks["PostgreSQL chunks<br/>有序 · JSONB"]
    pages --> documents["PostgreSQL documents<br/>extracted_text"]

    operator["本地操作者"] --> command["index_document --document-id UUID"]
    operator --> init_qdrant["init_qdrant"]
    command --> ordered["SELECT Document + Chunk<br/>ORDER BY chunk_index"]
    ordered --> embedding["EmbeddingClient"]
    embedding --> snapshot["固定 BGE snapshot<br/>本地缓存优先"]
    snapshot --> tokenizer["BGE tokenizer 预检<br/>包含特殊 token · 禁止截断"]
    tokenizer --> inference["SentenceTransformers CPU<br/>批量 ≤ 32"]
    inference --> vectors["512 维归一化向量"]
    vectors --> qdrant["Qdrant<br/>unnamed 512 / Cosine"]
    init_qdrant --> qdrant
    retrieval_api --> query_embedding
    query_embedding --> qdrant
    qdrant --> results["Top k 结果<br/>payload + score · 无向量<br/>doc_id filter 在 Qdrant 内执行"]

    chunks --> ordered
    chunks --> bm25_loader["ready Chunk 确定性快照<br/>每次请求计算 SHA-256 指纹"]
    bm25_api --> bm25_service["BM25Service<br/>延迟加载 · 进程内快照"]
    bm25_loader --> bm25_tokenizer["NFKC + casefold<br/>中文 unigram/bigram · 复合编号"]
    bm25_tokenizer --> bm25_index["BM25Okapi<br/>全局 IDF · get_scores()"]
    bm25_index --> bm25_results["token overlap → doc_id filter<br/>稳定排序 → Top k"]
    bm25_results --> bm25_api
~~~

关键隔离边界：

- 上传 API 不调用 EmbeddingClient，Day 6 不扩大上传事务。
- Day 6 Embedding 命令仍只读且只产生内存向量；Day 7 另由显式索引命令写 Qdrant。
- 索引命令先关闭 PostgreSQL Session，再执行模型推理和 Qdrant upsert。
- PostgreSQL 与 Qdrant 不伪装成跨存储事务；稳定 Chunk UUID 支持幂等重跑。
- DeepSeek Key 只属于生成链路，不参与 Embedding。
- `/chat` 只复用独立检索服务；上传接口仍不接入 BGE/Qdrant。
- Context 正文只进入 user message，sources 从实际 Context 生成，不依赖模型输出。
- 模型正文中的文件名、页码和 `SNN` 类来源标记在完整/流式输出中清理；客户端只信任
  后端结构化 sources。
- RAG 门槛不进入 `/retrieval/search`；`/chat` 不使用 Day 9 的 top_k/doc_id 参数，
  当前固定Hybrid20→Rerank5，再对原始vector_score使用`0.46`门控。
- 检索日志只记录 query 摘要哈希与结果身份（rank/chunk_id/doc_id/filename/page/score），
  不记录 query 原文、Chunk 正文、metadata 或向量。
- `backend/app/core/logging.py` 用 `JSONL_LOG_MARKER` 区分机器事件：普通 human handler
  排除该标记，独立 `{message}` handler 只处理标记事件，确保完整单行 JSON 且不重复。
- BM25 首次请求才解析数据库；应用启动和 `/health` 不扫描 PostgreSQL 或构建索引。
- BM25 与向量检索是两个独立接口；Day 10 不融合结果、不比较原始 score，也不接入
  `/chat` 或 RAG `0.46` 门控。
- Day 11 以第三个独立接口编排两路，按 rank 融合；任何分支失败整体失败，跨存储同 ID
  payload 冲突安全失败。Day12按独立授权接入/chat；RRF与logit均不进入`0.46`门控。

## 当前 HTTP 接口

| 方法与路径 | 状态 |
|---|---|
| GET /health | 已实现 |
| POST /chat，stream=false | 已实现，返回 answer/model/sources |
| POST /chat，stream=true | 已实现，返回 delta、sources event 与 DONE |
| POST /documents/upload | 已实现，支持 PDF/MD/TXT |
| POST /retrieval/search | 已实现，接收 query、可选严格 top_k（1..20，默认 5）和可选 doc_id，不返回向量 |
| POST /retrieval/bm25/search | 已实现，复用同一请求/响应结构，返回 raw BM25 score，无词项重合为空数组 |
| POST /retrieval/hybrid/search | 已实现，两路固定各取 20，标准 RRF 返回最终 top_k，score 为 RRF score |
| POST /retrieval/rerank/search | 已实现，仅query/doc_id，Hybrid20→Rerank5，返回logit及前后名次 |

应用启动和GET /health均不连接PostgreSQL、Qdrant、BGE、Reranker或LLM。

## 文档上传流程

1. upload_document() 读取 UploadFile.file，每块最多 1 MiB。
2. 验证安全文件名、扩展名、MIME、PDF 签名和实际 20 MiB 上限。
3. 文件先写 UUID.part，PDF 最多 500 页。
4. parse_document() 生成 list[PageText]；PDF 空白页保留原页码。
5. split_pages() 按页使用 o200k_base 和 RecursiveCharacterTextSplitter 切分。
6. Document 第一次 flush，Chunks 第二次 flush。
7. os.replace 提升文件，随后 commit。
8. 失败时回滚数据库并清理临时或已移动文件。

Day 5 已证明不能把 Document 和无 ORM relationship 的 Chunk 只做一次 flush：
真实 PostgreSQL 曾先插入 Chunk 并触发 chunks_doc_id_fkey。当前两次 flush 必须保留。

## Day 6 Embedding 流程

入口：

    .\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>

执行顺序：

1. build_parser() 解析 document_id。
2. embed_document() 获取 Session，按 Chunk.chunk_index 升序读取。
3. 没有 Chunk 时抛出 DocumentChunksNotFoundError，且不创建 Embedding 客户端。
4. get_embedding_client() 读取并缓存 EmbeddingSettings。
5. ensure_model_snapshot() 先检查固定 revision 的本地缓存。
6. 缓存缺失时匿名下载；只重试连接、超时、HTTP 429 和 5xx。
7. load_embedding_model() 使用 local_files_only=True 和 trust_remote_code=False 从 snapshot 加载。
8. validate_model_input_length() 使用 BGE tokenizer，add_special_tokens=True、truncation=False。
9. EmbeddingClient.embed_documents() 以最多 32 条为一批调用模型。
10. embed_chunks() 校验并按输入位置绑定 Chunk UUID。
11. print_summary() 只输出安全元数据；向量随进程结束丢弃。

### 模型与配置固定值

| 项目 | 值 |
|---|---|
| model_name | BAAI/bge-small-zh-v1.5 |
| model_revision | 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4 |
| device | cpu |
| dimension | 512 |
| batch_size | 32，允许配置 1 至 32 |
| normalize_embeddings | 必须为 true |
| cache_dir | data/models，相对仓库根目录 |
| download_max_retries | 最多 3 次重试，即首次尝试加 3 次重试 |
| retry backoff | 1、2、4 秒 |

Day 5 的 o200k_base 与 BGE tokenizer 不可互换。500 个 Day 5 token 不保证少于
BGE 的 max_seq_length，因此必须保留独立的推理前长度检查。

## Day 7 Qdrant 索引与检索流程

初始化入口：

    .\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant

索引入口：

    .\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>

索引顺序：

1. 从 PostgreSQL 读取 Document 和按 chunk_index 排序的 Chunks。
2. 关闭数据库 Session。
3. 创建或验证 unnamed 512/Cosine collection；配置不匹配时失败，不重建。
4. 使用 Day 6 `embed_documents()` 生成文档向量。
5. Point ID 直接使用 chunk_id，payload 携带正文、页码、文件名和 metadata。
6. 每批最多 32 条执行 `upsert(wait=True)`；部分成功后依靠相同 UUID 幂等重跑。

在线检索顺序（Day 9 更新后）：

1. `POST /retrieval/search` 校验请求体：非空 query、可选严格整数 `top_k`（1..20，
   默认 5，拒绝布尔/字符串/浮点）、可选 `doc_id`（UUID 或 null），禁止额外字段。
2. `RetrievalService.search()` 在调用 Embedding 前防御性复验 top_k。
3. `embed_query()` 添加一次固定 BGE 查询 instruction，并包含 instruction 做长度预检。
4. `query_points()` 使用 `limit=top_k`、`with_payload=True`、`with_vectors=False`；
   `doc_id` 非空时附加顶层 `doc_id` 的 `MatchValue(str(doc_id))` 过滤器，在 Qdrant
   查询内部先过滤再取 limit。
5. 校验 Point UUID、payload 必需字段和有限 score；带 filter 时再校验所有结果属于
   请求文档，越界返回安全 502。
6. 每次成功检索（含空结果）输出一条带 `JSONL_LOG_MARKER` 的单行 JSON 日志，字段为
   event/query_sha256/query_len/top_k/filter_doc_id/result_count/results
   （rank/chunk_id/doc_id/filename/page/score）。普通 human handler 排除该标记，独立
   `{message}` handler 只处理标记事件，保证 JSON 完整且不重复。

合法但无匹配的 `doc_id` 返回 200 空数组：检索接口表达"该过滤条件下没有匹配"，
不负责确认 PostgreSQL 文档资源是否存在，因此不引入 404。

Day 7 原始实现不含可调 top_k 和 doc_id filter；Day 9 增加这些参数。Day 10 BM25 与
Day 11 Hybrid 是下文所述独立链路；score threshold 请求参数尚未实现，Rerank已于Day12完成。

## Day 8 基础 RAG 历史流程

下述为Day8基础行为；Day12已将检索替换为Hybrid20→Rerank5并仅保留原始向量证据门，
当前检索规则见Day12章节，编排见Day14章节。Prompt、来源、拒答和JSON/SSE规则保留。

1. `/chat` 校验并规范化 message。
2. `RAGService.prepare()` 调用 Day 7 `RetrievalService.search()`，固定取得最多 5 个结果。
3. 只保留 score `>= 0.46` 的 Chunk；门槛只存在于 RAG 生成层。
4. 无结果时构造固定拒答状态，complete/stream 均不调用 LLM。
5. 有结果时按 filename/page 去重生成 sources，并把 filename/page/content JSON 放入 user message。
6. system message 规定 Context 不可信、禁止执行正文指令、禁止使用外部知识和伪造来源。
7. 普通模式调用 `complete_messages()`，返回 answer/model/sources。
8. 流式模式调用 `stream_messages()`，成功发送 delta → sources → DONE；LLM 失败发送 error 后停止。
9. `_strip_model_source_references()` 与 `_sanitized_model_deltas()` 清理模型自由文本中的来源标记，
   不改变后端从实际 Context 构造的 sources。

`0.46` 来自三条正样本和三条负样本的真实校准：正样本 Top-1 最小 `0.688781`，
负样本 Top-1 最大 `0.326244`。它只对当前受控样本有证据，后续仍需更大评测集复验。

## Day 9 检索优化

- `/retrieval/search` 开放严格 `top_k`（1..20）和单文档 `doc_id` filter；`/chat`
  与 RAG 生成层完全不变。
- top_k 上限 20 与 Day 12 计划（召回 Top 20 再重排 Top 5）对齐。
- 300/500/800 chunk size 使用固定、自撰的 8 页语料和 8 个带 `expected_phrase` 的问题，
  已完成真实 BGE + Qdrant 对比；NFKC + strip 子串匹配是唯一命中判据，成本统一使用
  `o200k_base` 近似口径。三配置 Chunk 数为 40/24/16，Hit@1/Hit@5/MRR@5 均为 1.0，
  Top-5 token 总量为 7986/13590/18576。固定审计标识会被 BGE tokenizer 高度压缩，
  因此结果不能外推到自然长文本；生产默认保持 `500/100`。方法、数据与局限见
  `docs/day9-retrieval-tuning.md`。

## Day 10 BM25 关键词检索

1. `POST /retrieval/bm25/search` 复用 Day 9 的严格 query、top_k、单 doc_id 请求模型和
   Chunk 响应结构；raw BM25 score 不限制在 `0..1`。
2. `get_bm25_service()` 只创建进程内服务，不读取 PostgreSQL。首次包含可搜索 token 的
   BM25 请求才进入刷新流程。
3. 同一刷新锁内 JOIN `Chunk + Document`，只读取 `Document.status == "ready"`，按
   doc_id/chunk_index/chunk_id 排序并在 Session 内转为 DTO；Session 关闭后再分词建索引。
4. 指纹覆盖 chunk_id、doc_id、chunk_index、content、page、filename 和 canonical metadata。
   指纹未变复用 `BM25Okapi`；变化时完整构建后原子替换；读取或构建失败时当前请求失败，
   不静默使用旧数据。
5. Tokenizer 统一执行 NFKC + casefold；中文连续段生成 unigram + bigram；英文、数字和
   `VPN-6203`/`ERR_AUTH_42` 类复合编号保留完整 token 和组成 token。query 有序去重，
   corpus 保留重复词频。
6. 搜索使用 `get_scores()`；先做 token overlap 门控，再做可选 doc_id 过滤，最后按
   `(-score, doc_id, chunk_index, chunk_id)` 稳定排序并截取 top_k。相关负分/零分结果不会
   被误删，无重合不会补齐零分 Chunk。
7. 成功搜索输出带 `JSONL_LOG_MARKER` 的 `bm25_search_completed` 单行 JSON，不记录 query
   原文、query tokens、正文、metadata、SQL 或凭据。

真实对比在同一 24 个 Chunk ID、500/100、Top 5 上进行：向量 Hit@1/Hit@5/MRR@5 为
`0.750/0.917/0.812`，BM25 为 `0.833/1.000/0.882`。详细逐题排名与限制见
`docs/day10-vector-vs-bm25.md`。该实验不包含 Hybrid 或 RRF。

## Day 11 Hybrid/RRF 流程

1. 独立 API 复用严格的 query/top_k/doc_id 模型，服务在调用分支前防御性校验参数。
2. 向量 `search(top_k=20, doc_id=...)` 后调用 BM25 同一参数，不引入线程池或并发。
3. 以 chunk_id 聚合两路并集；分支内重复 ID 拒绝，跨分支共同 ID 的 payload 必须一致。
4. 使用 `Σ 1/(60+rank)`，一基 rank，缺席一路贡献为 0；原始 score 不参与。
5. 按 `(-rrf_score, best_rank, doc_id, chunk_index, chunk_id)` 排序，再截取用户 top_k。
6. 返回统一 Chunk 结构，score 为 RRF score；内部两路 rank 仅用于测试和日志。
7. 输出安全 `hybrid_search_completed` JSONL。成功请求自然产生两条分支日志和一条
   Hybrid 日志；序列化失败只记安全错误，不影响成功结果。

请求非法或 BGE query 超限为 422，BM25 内部索引/计算失败为 500，非法向量结果或
跨存储 payload 冲突为 502，分支服务不可用为 503。任一路失败不返回部分结果。

相同 24 Chunk、候选 20、Top 5 的真实三路对比已完成，Hybrid 指标为
`0.917/1.000/0.944`（Hit@1/Hit@5/MRR@5）。负样本返回率仍为 1.0；此能力不提供
拒答。完整方法、逐题排名与局限见 `docs/day11-hybrid-comparison.md`。

## Day12本地重排与Chat

1. RerankedRetrievalService.search只接受query/doc_id，固定调用Hybrid top_k=20。
2. RerankerService首次使用时取得固定revision的六个安全文件，CPU/safetensors加载；
   空候选不加载模型，配置无效只在请求时安全503。
3. query完整成对预检；PassageOnlyTokenizer只截passage并记录数量，超长query安全422。
4. 显式Identity得到原始logit；候选按位置映射、数量/唯一性/有限性校验，稳定排序取5。
5. RerankOutcome保留全部候选movement与耗时；独立HTTP只公开Top5与名次字段。
6. RAG在Top5上仅以vector_score>=0.46作证据门；BM25-only排除，无通过项固定拒答。
7. 日志不含query/正文/metadata；422/500/502/503分层，任一分支失败不降级。

2026-10-28历史真实同语料Hit@1/Hit@5/MRR@5=0.917/1.000/0.958，3负样本拒答零LLM；CPU热推理约6.29s，
小样本和无关候选升位的局限见[实验报告](day12-rerank-comparison.md)。
原Day11技术决策保留，Day12决策为D-050至D-053。

## Day14 LangGraph RAG 编排

~~~mermaid
flowchart LR
    START --> route{needs_retrieval}
    route -->|True| retrieve_node
    route -->|False：内部已准备| generate_node
    retrieve_node --> generate_node
    generate_node --> END
~~~

实际编译图导出见 [day14-agent-graph.mmd](day14-agent-graph.mmd)。
State 只有 query、retrieved_docs、prepared、answer、tool_calls、needs_retrieval。
Context 只有 response_mode；依赖在工厂闭包中，不进入 State，不使用 reducer。
公共请求固定 True；False 仅支持内部合法 PreparedRAG，缺失则安全失败。

- retrieve_node：既有 Hybrid20→Rerank5，保留原始 Top5 到 retrieved_docs；
  复用原始 vector_score>=0.46 门控、Prompt 与来源函数，写入 prepared 和 needs_retrieval=False。
- generate_node：无 Context 固定拒答且零 LLM；有 Context 复用原 LLMClient、
  完整/跨 delta 引用清理，生成 answer。tool_calls 始终为空。
- 非流式：RAGService.complete(question) → graph.invoke → RAGAnswer → 原 ChatResponse。
- 流式：start_stream 预消费 v2 updates 到 retrieve_node 成功后才创建响应；
  随后继续同一 graph.stream，通过 custom writer 发出 type/delta。
  sources 从 PreparedRAG 取得，成功顺序仍为 delta→sources→[DONE]，失败发送原 error。
- StreamControl 经 Runtime 控制逐 delta 背压与取消；PreparedRAGStream 使用 Context 和锁
  支持不同工作线程预取/消费，结束/异常/断连显式关闭图与上游；没有完整答案预缓冲。
  同步上游正在阻塞时仍受既有 LLM timeout（默认 60s）约束。
- RAGService 的 runner 首次调用才编译并缓存；旧内部 prepare/PreparedRAG 适配复用同一节点，
  不维护第二套检索逻辑。启动/health 不构图或访问外部依赖。
- 每次 invoke/stream 显式禁用 tracing、callbacks=[]；
  内部 updates 不进入 HTTP，错误日志不打印 State 或上游异常正文。
  新内部图错误使用安全 RAGGraphError，既有服务异常与 HTTP 映射保留。

LangGraph 仅替代原顺序式编排；上述 Day8/Day12 的 Prompt、拒答、来源与检索规则继续适用。
没有新增 HTTP 字段、工具、会话或 checkpointer。

## 异常与安全边界

backend/app/services/embedding.py 定义的安全异常：

- EmbeddingError
- ModelDownloadError
- ModelLoadError
- EmbeddingInputError
- EmbeddingInputTooLongError
- ChunkEmbeddingInputTooLongError
- EmbeddingResultError

backend/app/commands/embed_document.py 额外定义：

- DocumentChunksNotFoundError
- EmbeddingConfigurationError

错误分类规则：

- Embedding 配置 ValidationError 转为 EmbeddingConfigurationError，不能误报数据库不可用。
- DatabaseConfigurationError、数据库设置 ValidationError 和 SQLAlchemyError 仍归类为数据库不可用。
- cache_dir.mkdir() 的 OSError 转为不含本机路径的 ModelDownloadError，且不调用 downloader。
- 原始异常用异常链保留；用户输出不包含 Chunk 正文、向量、本机缓存路径、API Key 或数据库密码。

## 配置与依赖边界

- Settings：APP_ 前缀。
- LLMSettings：LLM_ 前缀。
- DatabaseSettings：POSTGRES_ 前缀。
- DocumentSettings：上传资源限制。
- ChunkingSettings：CHUNK_SIZE、CHUNK_OVERLAP、CHUNK_ENCODING_NAME。
- EmbeddingSettings：EMBEDDING_ 前缀；模型名、revision、维度和设备使用 Literal 固定。
- QdrantSettings：QDRANT_ 前缀；本地 REST URL、collection、timeout 和最大 32 条 upsert batch。
- RAGSettings：RAG_ 前缀；生成层固定相关性门槛，范围 `0..1`。
- RerankerSettings：RERANKER_前缀；固定模型/revision、CPU/512、默认batch4、懒加载安全权重。
- sentence-transformers==5.3.0 为 Day 6 新依赖。
- qdrant-client==1.18.0 为 Day 7 固定依赖。
- rank-bm25==0.2.2 为 Day 10 固定依赖。
- langgraph==1.2.16 为 Day14 固定依赖；没有安装完整 langchain。
- 当前环境已解析到 torch 2.13.0、transformers 5.14.0、huggingface-hub 1.23.0。

所有相对上传和模型缓存路径均从仓库根目录解析，不依赖当前工作目录。
数据库仍通过 python -m backend.app.models.init_db 显式建表，应用启动和 GET /health
不初始化或探测 PostgreSQL。

## 尚未实现

- pgvector 或 PostgreSQL 向量字段；
- 自动索引、删除同步、后台队列或 outbox；
- score threshold 请求参数、多 doc_id 列表过滤、Qdrant payload index；
- 加权RRF或故障降级（本地Rerank与Hybrid接入/chat已于Day12完成）；
- Agent 工具选择、ToolNode、会话和记忆；
- 评测、trace、Streamlit 和完整 Docker Compose。

## 最终目标架构

~~~mermaid
flowchart TB
    user["用户"] --> ui["Streamlit"]
    ui --> api["FastAPI"]

    api --> ingest["文档解析与切分"]
    ingest --> postgres["PostgreSQL<br/>文档与 Chunk 元数据"]
    ingest --> embedding["Embedding"]
    embedding --> qdrant["Qdrant"]

    api --> agent["LangGraph Agent"]
    agent --> vector["向量检索"]
    agent --> bm25["BM25"]
    vector --> rrf["RRF"]
    bm25 --> rrf
    rrf --> rerank["Rerank"]
    rerank --> llm["OpenAI-compatible LLM"]
    llm --> api
~~~

## 模块演进规则

- api/ 只处理 HTTP 输入输出和错误映射。
- commands/ 放置显式本地操作入口，不得隐式接入上传链路。
- services/ 封装外部服务与业务能力。
- core/ 负责配置、日志和横切能力。
- models/ 放置数据库模型。
- agent/ 自 Day14 起负责双节点图、State 和执行生命周期，业务能力继续复用 services/。
- 不得为未来 Day 提前引入未验证抽象。
- PLAN.md 未经用户明确授权不得修改。
