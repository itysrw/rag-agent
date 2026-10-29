# 技术决策记录

更新时间：2026-10-29（Asia/Shanghai）

> Day 11 按用户提供的每日规划新增 D-047 至 D-049；D-001 至 D-046 保留原有适用范围。

> D-001至D-049为前序决策，D-050至D-053为Day12实施决策。本次按用户要求收录Day12本地提交，不新增或推翻技术决策。
> 2026-10-29用户确认Day12已完成，PLAN四项和开发日志已勾选；Day12纳入本地提交但未推送，Day13未开始。
> 最近标准为2026-10-29本地提交前重跑的403 passed/12 skipped（15.93s）；最近全真实仍为2026-10-28的413，本次未重跑真实集成。

交接只读观察：ensure_reranker_snapshot当前将httpx.ReadError纳入有限重试；
test_reranker.py包含test_download_retries_read_errors_with_exponential_backoff；
test_rerank_comparison_integration.py包含_assert_quality_acceptance及
test_quality_acceptance_rejects_all_correct_results_falling_to_fifth。
当前质量基线严格检查聚合指标、逐题首次命中、每题20候选/0截断，防止Hit@5掩盖质量回退。
这些实现细节不构成本轮新增决策；后续普通回归已随2026-10-29标准403/12通过，作者/独立审查记录未补查，详见[交接包](HANDOFF.md)。

## D-001：以 25 天计划控制范围

- 状态：已确认
- 决策：`PLAN.md` 是每日范围和顺序的唯一计划基线。
- 原因：避免在早期同时引入数据库、检索、Agent 和前端，确保每个阶段可验收。
- 影响：未经用户明确要求不得跨 Day 实现；未经明确授权不得修改 `PLAN.md`。

## D-002：Day 2 起使用模块化 FastAPI 结构

- 状态：已确认
- 决策：入口位于 `backend/app/main.py`，路由位于 `backend/app/api/`，配置位于
  `backend/app/core/`，服务位于 `backend/app/services/`。
- 原因：后续 LLM、文档、检索和 Agent 可独立演进，避免所有逻辑堆积在 `main.py`。

## D-003：Day 3 只接 DeepSeek

- 状态：已确认
- 决策：Day 3 不同时接入 OpenAI API 或通义千问。
- 原因：用户已有 DeepSeek 额度；一次只验证一个供应商可降低配置、计费和测试复杂度。
- 已否决：Day 3 同时接 DeepSeek 和千问。

## D-004：使用 `deepseek-v4-flash`

- 状态：已确认
- 决策：模型名为 `deepseek-v4-flash`，Base URL 为 `https://api.deepseek.com`。
- 原因：DeepSeek 官方说明 `deepseek-chat` 和 `deepseek-reasoner` 将于北京时间
  2026-07-24 23:59 停用；V4 Flash 成本低、支持兼容接口、流式和工具调用。
- 已否决：继续使用 `.env.example` 原来的 `deepseek-chat`。

## D-005：Day 3 默认关闭 DeepSeek 思考模式

- 状态：已确认
- 决策：`LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}`。
- 原因：Day 3 的目标是普通对话和 SSE；默认思考会增加 `reasoning_content`、解析复杂度、延迟和费用。
- 影响：以后需要推理时可通过配置启用，不应改写客户端。

## D-006：LLM 客户端保持 OpenAI-compatible

- 状态：已确认
- 决策：`LLMClient` 使用 OpenAI Python SDK 的 `chat.completions.create`，只依赖
  API Key、Base URL、model、timeout 和不透明 `extra_body`。
- 原因：未来切换通义千问或 OpenAI-compatible 服务时不重写客户端。
- 禁止：在 `LLMClient` 中根据 `provider == "deepseek"` 编写分支。

## D-007：同一个 `/chat` 支持两种响应模式

- 状态：已确认
- 决策：`stream=false` 返回完整 JSON，`stream=true` 返回 SSE。
- 原因：保持接口数量小，并直接满足 Day 3 的非流式和流式要求。
- SSE 契约：增量为 `data: {"delta":"..."}`，最终为 `data: [DONE]`。

## D-008：同步 SDK 调用运行在 FastAPI 同步路由中

- 状态：已确认
- 决策：`chat()` 使用普通 `def`；FastAPI 在线程池运行同步路由。
- 原因：OpenAI-compatible 同步 SDK 足够满足 Day 3，避免阻塞事件循环，也不提前引入异步客户端双实现。

## D-009：配置和上游错误不得泄露供应商细节

- 状态：已确认
- 决策：缺少 Key 返回通用 `503`；普通上游失败返回通用 `502`；流错误返回通用 SSE error。
- 原因：避免将凭据、供应商响应体或内部异常暴露给调用方。

## D-010：真实 API 与单元测试分离

- 状态：已确认
- 决策：pytest 使用 `StubLLMClient` 和 fake SDK，不消耗外部额度；真实 DeepSeek 调用是独立验收步骤。
- 原因：测试必须稳定、快速、可离线运行，不能依赖账户余额或网络。

## D-011：ChatGPT Plus 不等于 OpenAI API 额度

- 状态：已确认
- 决策：当前 ChatGPT Plus 仅作为开发辅助，不作为项目后端 API 来源。
- 原因：ChatGPT 与 OpenAI API 分开管理和计费；用户尚未确认 OpenAI API 余额。

## D-012：Day 6 Embedding 供应商曾延后决定

- 状态：已被 D-024 取代
- 原候选：OpenAI、阿里云百炼/通义千问、本地 `BAAI/bge-small-zh-v1.5`。
- 当时原因：Day 3 尚无文档语料、运行环境和质量/成本测试，不能提前做可靠选择。
- 当前结论：Day 6 已按 D-024 确认使用固定 revision 的本地 BGE；OpenAI 和千问不进入 Day 6。
- 仍然有效：不得在早于计划的阶段提前实现 Embedding。

## D-013：Day 18 千问对比是可选评测亮点

- 状态：待确认
- 决策候选：在评测阶段增加千问与 DeepSeek 的质量、延迟和成本对比。
- 原因：通义千问在中文、长文本和阿里云模型生态方面有价值，但现在接入会扩大 Day 3 范围。
- 禁止：未到 Day 18 且未获确认前实现该对比。

## D-014：阶段检查点必须写入交接文档

- 状态：已确认
- 决策：每个阶段更新 `STATUS.md`、`HANDOFF.md`、必要时更新 `DECISIONS.md`，并指定唯一下一步。
- 原因：跨会话时不能依赖聊天记忆推断精确项目状态。

## D-015：Day 4 保留 PDF 页边界

- 状态：已确认
- 决策：解析层返回一基页码的 `PageText` 列表；PDF 空白页也必须保留，存库时以 `\f` 拼接。
- 原因：Day 5 需要在页内切分并写入 chunk page，Day 8 需要可靠生成来源页码。
- 文本文件：Markdown/TXT 使用 UTF-8（支持 BOM）并视为第 1 页。
- 失败：只有全部页面均为空白时返回 `400`；扫描 PDF 的 OCR 不属于 Day 4。

## D-016：Day 4 使用同步 SQLAlchemy 2.x 与 psycopg 3

- 状态：已确认
- 决策：上传路由为普通 `def`，使用同步 Session 和 `postgresql+psycopg` 驱动。
- 原因：FastAPI 在线程池执行同步路由，可容纳同步文件 I/O、pypdf 与数据库操作，并为后续表扩展保留 ORM 模型。
- 数据库初始化：仅通过 `python -m backend.app.models.init_db` 显式执行，不得放入应用启动或 `/health`。

## D-017：文档主键、状态和文本字段

- 状态：已确认
- 决策：`documents` 使用 PostgreSQL UUID 主键，成功状态为 `ready`，增加 `extracted_text TEXT`。
- 不增加：`storage_path`、`content_type`、`error_message`。
- 路径：统一由存储服务根据 UUID 与标准化扩展名推导。
- 失败记录：Day 4 不保存；解析或持久化失败时回滚并清理文件。

## D-018：Day 4 上传资源与错误契约

- 状态：已确认
- 限制：实际上传字节最多 20 MiB、PDF 最多 500 页、读取块为 1 MiB。
- HTTP：成功 `201`；无效内容 `400`；超限 `413`；不支持类型 `415`；PostgreSQL 不可用 `503`；未预期存储错误 `500`。
- 一致性：先写 UUID `.part`、解析、数据库 `flush`，再 `os.replace`，最后提交；异常时回滚并删除临时/最终文件。
- 已知残余风险：进程恰好在移动后崩溃可能留下孤儿文件，后续可增加启动清理任务，但不在 Day 4 扩展。

## D-019：Day 5 使用 `o200k_base` 作为可复现 token 基准

- 状态：已确认
- 决策：文本切分和 300/500/800 对比统一使用 `tiktoken` 的 `o200k_base`。
- 原因：默认 `len` 统计字符而不是 token；固定 tokenizer 才能复现实验和验证上限。
- 边界：它不是 DeepSeek 或未来 Embedding 模型精确 tokenizer 的承诺；模型确定后仍需重新评估。
- 特殊文本：使用 `disallowed_special=()`，将类似特殊 token 的字面量作为普通输入处理。

## D-020：Day 5 按页独立切分，生产默认 `500/100`

- 状态：已确认
- 决策：使用独立的 `langchain-text-splitters` 包和 `RecursiveCharacterTextSplitter`；
  每个 `PageText` 单独切分，空白页跳过，后续页码不得压缩。
- 默认：`chunk_size=500`、`chunk_overlap=100`、`keep_separator="end"`。
- 分隔优先级：段落、换行、中英文句末标点、分号、逗号、空格、单字符。
- 原因：Chunk 不跨页才能为 Day 8 保留可靠引用；20% overlap 在语义边界附近保留上下文。
- 禁止：不得将 300/500/800 的结构对比提前描述为检索质量结论。

## D-021：Chunk 使用 UUID、显式顺序和 JSONB 元数据

- 状态：已确认
- 决策：`chunks.chunk_id` 为 UUID 主键；`chunk_index` 在文档内从 0 连续递增；
  `(doc_id, chunk_index)` 唯一，`doc_id` 建索引并外键到 `documents.id`，`ON DELETE CASCADE`。
- 元数据：数据库列名为 `metadata`，ORM 属性名为 `chunk_metadata`，避免与 SQLAlchemy
  Declarative 的 `metadata` 保留属性冲突；PostgreSQL 使用 JSONB，SQLite 测试使用 JSON 变体。
- 原因：UUID 只提供身份，不提供稳定顺序；显式顺序才能恢复文档内 Chunk 次序。

## D-022：Document 与 Chunk 同事务、分两次 flush

- 状态：已确认
- 决策顺序：创建 Document/Chunk 草稿 → `session.add(document)` → 第一次 `flush()` →
  `session.add_all(chunks)` → 第二次 `flush()` → `os.replace` → `commit`。
- 原因：没有 ORM relationship 时，一次 flush 不能依赖对象添加顺序。真实 PostgreSQL 验收曾先插入
  Chunk 并触发 `chunks_doc_id_fkey` 外键失败；先 flush Document 可显式保证父行存在。
- 一致性：两次 flush 仍处于同一个事务中；第二次 flush、文件移动或 commit 失败都会整体回滚并清理文件。
- 已否决：仅将 Document 和 Chunk 加入 Session 后执行一次 flush，并假设 SQLAlchemy 会自动按外键排序。

## D-023：Day 5 仅创建新表，不回填也不引入迁移工具

- 状态：已确认
- 决策：`backend.app.models.init_db` 注册 `Document` 和 `Chunk`，继续用显式
  `Base.metadata.create_all()` 创建缺失的全新 `chunks` 表。
- 原因：Day 5 没有修改既有 `documents` 表；此阶段引入 Alembic 超出范围。
- 限制：`create_all()` 不是迁移工具；首次修改已有表结构前仍需重新确认 Alembic。
- 历史数据：只为新上传文档生成 chunks，不回填 Day 4 已有记录。

## D-024：Day 6 只使用固定版本的本地 BGE 模型

- 状态：已确认
- 决策：文档 Embedding 使用 `BAAI/bge-small-zh-v1.5`，revision 固定为
  `4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4`，默认且仅支持 CPU，输出维度固定为 512。
- 原因：该模型适合中文检索、规模较小、可完全本地运行，并能避免知识库正文发送到外部 API。
- 凭据边界：Embedding 不要求 OpenAI API Key，也不得复用 DeepSeek Key；DeepSeek 仅用于
  已有 LLM 对话链路。千问不进入 Day 6。

## D-025：BGE tokenizer 在推理前独立执行长度检查

- 状态：已确认
- 决策：每个 Chunk 使用 BGE 自己的 tokenizer 计数，包含特殊 token；超过模型
  `max_seq_length` 时在推理前失败，禁止依赖 SentenceTransformers 静默截断。
- 原因：Day 5 的 `o200k_base` 与 BGE 的 BERT tokenizer 不可互换，500 个 Day 5 token
  不能证明一定小于 BGE 的 512 token 上限。
- 安全错误：只包含 Chunk UUID、实际 BGE token 数和上限，不包含 Chunk 正文。

## D-026：Day 6 向量只存在于内存，不进入上传事务

- 状态：已确认
- 决策：按输入顺序每批最多 32 条生成归一化向量，并绑定原 Chunk UUID；不新增数据库
  表或字段，不写 `Chunk.metadata`、PostgreSQL、pgvector 或 Qdrant，也不修改上传接口。
- 原因：向量持久化属于 Day 7；将本地模型推理放入上传事务会扩大失败面并显著延长事务。
- 文本语义：文档 Chunk 直接编码，不添加只属于查询侧的 BGE query instruction。

## D-027：模型下载和加载采用严格失败边界

- 状态：已确认
- 决策：先按固定 revision 查找本地缓存；缺失时下载。只对连接错误、超时、429 和 5xx
  最多重试 3 次，退避为 1、2、4 秒；404、权限、缓存损坏、OOM、设备、维度或本地推理
  错误不重试。
- 加载：下载完成后只从本地 snapshot 加载，`local_files_only=True`、
  `trust_remote_code=False`、匿名访问，并在进程内复用模型。

## D-028：Day 7 使用显式命令完成 Qdrant 索引

- 状态：已确认
- 决策：`index_document --document-id` 先从 PostgreSQL 读取 Document 和有序 Chunk，
  关闭 Session 后再执行本地 Embedding 与 Qdrant upsert；上传接口不自动索引。
- 原因：PostgreSQL 与 Qdrant 不能组成一个真实事务。显式命令可以隔离上传失败面，并允许
  通过稳定 Point ID 幂等重跑。
- 限制：不实现后台队列、outbox、删除同步或上传事务内 Embedding。

## D-029：Qdrant 使用固定的 unnamed 512/Cosine collection

- 状态：已确认
- 决策：Day 7 使用单一 unnamed dense vector，维度固定 512、距离为 Cosine；Point ID
  直接复用 `Chunk.chunk_id`，payload 保存 doc_id、chunk_index、content、page、filename
  和 metadata。
- 原因：该配置与 Day 6 的归一化 BGE 向量一致；复用 UUID 保持跨存储身份一致，并使重复
  upsert 覆盖同一点而不是生成重复数据。
- 安全：已有 collection 必须校验维度和距离；不使用 `recreate_collection()` 自动删除数据。

## D-030：查询向量使用独立 BGE instruction

- 状态：已确认
- 决策：`EmbeddingClient.embed_query()` 仅为查询添加一次
  `为这个句子生成表示以用于检索相关文章：`，并让 instruction 一起参与 BGE tokenizer
  长度预检；`embed_documents()` 继续直接编码 Chunk 正文。
- 原因：BGE 的查询与 passage 编码语义不同，但仍必须保持 512 维、归一化和禁止静默截断。

## D-031：Day 7 检索 API 固定 Top 5 且不返回向量

- 状态：已确认
- 决策：`POST /retrieval/search` 请求体只允许 `query`，内部使用 `query_points()`、
  `limit=5`、`with_payload=True`、`with_vectors=False`。
- 原因：可调 top_k、doc_id filter 和 score threshold 属于 Day 9；当前接口只验证基础向量
  检索链路，并避免泄露或传输完整向量。
- 错误：Query 过长为 422；Embedding/Qdrant 不可用或 collection 不匹配为 503；无效
  Qdrant Point/Payload 为安全 502。

## D-032：Day 8 在生成层使用固定相关性门控

- 状态：已确认
- 决策：`RAGSettings.min_relevance_score` 默认固定为 `0.46`，只过滤送入 Prompt 的
  Day 7 Top 5 结果；不修改 `/retrieval/search`，也不向请求方开放门槛。
- 证据：修复中文 PDF fixture 后，三个正样本 Top-1 为 `0.688781`、`0.734850`、
  `0.814524`；三个负样本 Top-1 为 `0.282149`、`0.326244`、`0.306839`。
- 限制：该值只对当前受控样本有证据，不是概率，也不是后续评测集的最终阈值。

## D-033：RAG 使用结构化 messages，Context 作为不可信 user 数据

- 状态：已确认
- 决策：LLM 请求使用 system + user messages；system 保存 RAG 规则，检索 Context 以 JSON
  放入 user message，仅包含 filename、page、content。
- 原因：知识库正文可能包含 Prompt Injection，不能获得 system 指令优先级；JSON 渲染可稳定
  处理引号、换行和分隔符。
- 兼容：`LLMClient.complete()` 和 `stream()` 继续包装单一 user message。

## D-034：拒答与结构化 sources 由后端控制

- 状态：已确认
- 决策：无通过门槛的 Chunk 时后端精确返回 `知识库中没有相关信息`，不调用 LLM；
  sources 从实际 Context 按 filename/page 去重生成，不从模型答案解析。
- SSE：成功为 delta → sources → DONE；流失败发送 error 后停止，不发送 sources 或 DONE。
- 原因：降低幻觉、费用和延迟，并防止模型伪造来源或页码。

## D-035：检索必须在建立 SSE 响应前完成

- 状态：已确认
- 决策：`RAGService.prepare()` 在构造 `StreamingResponse` 前完成 BGE、Qdrant、门控、
  Prompt 和 sources 准备。
- 原因：Query 超限和检索服务故障应返回真实 HTTP 422/502/503；只有 LLM 已开始流式输出后
  的错误才使用 SSE error event。

## D-036：受控中文 PDF fixture 使用 Type0/CID 字体

- 状态：已确认
- 决策：测试 PDF 使用 Type0 `/STSong-Light`、`/UniGB-UCS2-H` 和无 BOM UTF-16BE hex text。
- 原因：旧 Type1+BOM 方案被 pypdf 提取为带 NUL 的字节映射，无法写入 PostgreSQL，且会
  污染中文检索校准；新方案可精确提取中文并通过真实上传链路。

## D-037：模型正文来源标记不可信并由 RAG 层清理

- 状态：已确认
- 决策：结构化 `sources` 是唯一可信引用。`RAGService.complete()` 使用
  `_strip_model_source_references()` 清理完整答案，`RAGService.stream()` 使用
  `_sanitized_model_deltas()` 跨流式分片清理 `.pdf/.md/.txt`、`page N`、`第 N 页`、
  `SNN` 及包含这些标记的括号引用。
- 原因：模型可能复述 Context 文件名、重复后端来源或伪造页码；引用必须从实际通过门控的
  Context 生成，不能从模型自由文本解析。
- 影响：答案正文与来源展示分离；JSON/SSE 客户端只应读取后端 `sources` 字段/event。

## D-038：真实 DeepSeek 只做显式授权的一次性冒烟

- 状态：已确认
- 决策：真实 DeepSeek 不进入标准 pytest；每次产生费用的调用都需要显式授权，并在完成后停止。
- 原因：网络、账户余额、费用和模型自然语言均不稳定，不能破坏离线测试的可重复性。
- 当前证据：2026-07-16 已覆盖报销 JSON、VPN SSE、Python 门控拒答；一次性脚本未提交。
- 限制：不得把上述三条路径写成“年假”和“月球”也已真实调用；补充调用需新授权。

## D-039：Day 9 top_k 使用严格整数校验，范围 1 至 20

- 状态：已确认
- 决策：`POST /retrieval/search` 的 `top_k` 使用 Pydantic `Field(strict=True, ge=1, le=20)`，
  默认 5；`0`、`21`、`true`、`"5"`、`5.0`、`null` 均返回 422。`RetrievalService.search()`
  在调用 Embedding 前对直接调用方再做一次防御性校验。
- 原因：普通 `int` 会把布尔和可转换字符串静默接受；上限 20 与 Day 12 计划的
  “召回 Top 20 再重排 Top 5”对齐，不提前实现 Rerank。
- 边界：`/chat` 与 RAG 层不使用该参数，Day 8 固定 Top 5 + `0.46` 门控行为不变。

## D-040：doc_id 过滤在 Qdrant 查询内执行并做返回一致性校验

- 状态：已确认
- 决策：`doc_id` 非空时构造顶层 `doc_id` 字段的 `MatchValue(str(doc_id))` 过滤器传给
  `query_points(query_filter=...)`；`doc_id` 为 None 时不传该参数，保持原调用形状。
  解析结果后再校验每条结果属于请求文档，越界抛 `QdrantResultError`（HTTP 502）。
- 原因：搜索后在 Python 过滤会让其他文档挤占 limit 名额；payload `doc_id` 以字符串
  存储，传 UUID 对象无法命中；返回侧校验防止过滤失效时跨文档泄露。
- 语义：合法但无匹配的 doc_id 返回 200 空数组——检索接口不负责确认文档资源存在，
  不引入 404。不建 Qdrant payload index，不修改 collection 初始化契约。

## D-041：检索日志为单行 JSON，只含摘要身份信息

- 状态：已确认
- 决策：每次成功检索（含空结果）恰好输出一条 `retrieval_search_completed` 单行 JSON
  日志，字段为 query_sha256、query_len、top_k、filter_doc_id、result_count 和
  results（rank/chunk_id/doc_id/filename/page/score）。JSON 直接进入 message；
  `backend/app/core/logging.py` 定义 `JSONL_LOG_MARKER`，普通 human handler 排除该标记，
  独立 `{message}` handler 只处理标记事件。序列化失败只记录安全错误，不影响检索请求。
- 原因：仅用 `logger.bind()` 的扩展字段不能保证既有 human formatter 输出完整 JSON；若
  同一事件同时进入 human 与 JSONL handler 又会重复。标记加互斥过滤保证完整单行 JSON、
  不重复，并保留普通日志的人类可读格式，以支持后续评测关联。
- 边界：禁止记录 query 原文、Chunk 正文、metadata、向量或凭据。`query_sha256` 只降低
  直接泄露，不等于匿名化。

## D-042：Day 9 chunk size 实验使用确定性语料与唯一客观判据

- 状态：已确认
- 决策：语料与问题集以纯 Python 常量固定在 `backend/tests/day9_tuning_corpus.py`，内容
  自撰、可公开提交、无随机或联网获取。共 8 页、8 个问题，每题必须有非空
  `expected_phrase`。每页按 `o200k_base`、`disallowed_special=()` 计数大于 800 token，
  300/60、500/100、800/160 必须产生不同 Chunk 数。
- 判据：只执行 NFKC 规整和首尾 strip；Chunk 归一化正文包含归一化 expected_phrase
  才算命中。Hit@1、Hit@5、MRR@5 对全部问题平均，不使用人工“肉眼相关”判断。
- token 口径：平均 Chunk token 和全部问题的 Top-5 上下文 token 总量都使用相同的
  `o200k_base` 口径。它不是 BGE 自有 tokenizer 或 DeepSeek 的精确 tokenizer，只是
  跨配置可比的近似成本单位。
- 执行：三配置均使用真实本地 BGE 与独立一次性 Qdrant collection，固定 Top 5；不使用
  PostgreSQL，不触碰正式 collection，collection 在 finally 中删除。
- 原因：短页会使 500/800 退化为相同 Chunk，填满 800 o200k token 的自然中文又可能
  越过 BGE 512 上限，二者都无法产出三组可比真实指标。因此语料加入固定、自撰的长
  审计标识以稳定 o200k 长度，而 BGE 将其压缩为极少 token；该人工结构必须在报告中
  明确披露，结果不得外推到自然长文本。
- 实测结论：三配置 Chunk 数为 40/24/16，Hit@1、Hit@5、MRR@5 均为 1.0；Top-5
  上下文 token 总量为 7986/13590/18576。受控语料无法区分质量，但显示更大 Chunk
  增加上下文成本。生产默认保持 `500/100`，不宣称任何配置普遍最优。

## D-043：Day 10 使用确定性中英混合 tokenizer

- 状态：已确认
- 决策：BM25 corpus 与 query 共用唯一 tokenizer：Unicode NFKC + `casefold()`；中文连续段
  生成 unigram + bigram；英文和数字按词保留；`VPN-6203`、`ERR_AUTH_42` 类复合标识
  同时保留完整 token 和拆分组成部分。query token 有序去重，corpus token 保留重复词频。
- 原因：`rank_bm25` 不负责分词，中文直接 `.split()` 会把整句视为一个 token；query
  重复词会人为放大权重，而 corpus 去重会破坏 BM25 的 TF 信息。
- 边界：不引入 jieba、停用词、同义词或自定义词典；unigram/bigram 可能产生宽泛单字
  重合，后续必须由更真实评测集复验。

## D-044：BM25 使用延迟 PostgreSQL 全局快照和指纹刷新

- 状态：已确认
- 决策：首次包含可搜索 token 的 BM25 请求才读取 `ready` Document 的全部 Chunk；按
  doc_id/chunk_index/chunk_id 确定性排序，在 Session 内转 DTO，关闭 Session 后分词和
  构建 `BM25Okapi`。每次请求重新扫描并计算 SHA-256 指纹，未变化复用索引，变化时在同一
  锁内完整构建并原子替换。
- 指纹：覆盖 chunk_id、doc_id、chunk_index、content、page、filename 和 canonical
  metadata；新增、修改、删除或响应字段变化均触发重建。
- 失败语义：数据库读取或新索引构建失败时当前请求失败，不静默返回旧快照；旧对象仅保留
  在内存中供后续成功刷新比较。空 corpus 或全无 token corpus 不构建 `BM25Okapi`。
- 限制：每次请求仍扫描 PostgreSQL 计算指纹，多 Uvicorn worker 各持一份索引；这不是
  大规模生产索引方案，也不新增表、磁盘索引或 refresh API。

## D-045：BM25 用 token overlap 门控并在 Top-K 前过滤 doc_id

- 状态：已确认
- 决策：使用 `BM25Okapi.get_scores()`，禁止 `get_top_n()`；只保留 query/document 至少
  一个 token 重合的 Chunk，再应用可选单 doc_id，按
  `(-score, doc_id, chunk_index, chunk_id)` 稳定排序并截取 top_k。
- 原因：`get_top_n()` 会在无关键词重合时补齐无关零分结果；小语料相关结果可能为 0 或
  负分，因此不能使用 `score > 0`。doc_id 在截断后过滤会让其他文档挤占名额。
- 分数边界：BM25 raw score 不是概率、不限制在 `0..1`、随 corpus 变化，不能套用 RAG
  `0.46` 门槛或与 Cosine score 直接比较；所有返回 score 必须转换为有限 float。

## D-046：Day 10 保持独立 BM25 接口并只比较排名指标

- 状态：已确认
- 决策：新增 `POST /retrieval/bm25/search`，复用 Day 9 的严格 query/top_k/doc_id 请求和
  Chunk 响应结构；不为 `/retrieval/search` 增加 mode，不接入 `/chat`，不融合向量与
  BM25。成功检索输出安全 `bm25_search_completed` JSONL。
- 实验：真实 PostgreSQL 与临时 Qdrant 使用相同 24 个 Chunk ID、固定 500/100 和 Top 5，
  对比 12 个预先固定正样本；向量 Hit@1/Hit@5/MRR@5 为 `0.750/0.917/0.812`，BM25 为
  `0.833/1.000/0.882`。三条知识库外英文问题返回率分别为 1.0 与 0.0。
- 限制：只比较 rank 指标，不比较原始 score；该受控小样本不证明 BM25 普遍优于向量，
  也不是 Day 11 Hybrid/RRF 的收益证据。

## D-047：Day 11 使用标准等权 RRF 和固定候选深度

- 状态：已确认并实现
- 决策：向量、BM25 同步顺序调用，各取最多 20；使用一基排名 `1/(60+rank)` 累加，
  最终截取严格 `top_k=1..20`。不向请求方开放候选深度、k、权重或 mode。
- 排序：`(-rrf_score, best_rank, doc_id, chunk_index, chunk_id)`。
- 原因：只使用排名即可避免 Cosine/BM25 分数量纲差异；候选深度与最终返回数分离，
  为融合保留纠错空间，不根据小型评测集调参。
- 分数边界：响应 score 为 RRF score，不是概率或相关性门槛，不适用 RAG `0.46`。

## D-048：Chunk UUID 是融合身份，跨存储冲突安全失败

- 状态：已确认并实现
- 决策：同一分支重复 chunk_id 被拒绝；跨分支相同 ID 必须具有相同 doc_id、
  chunk_index、content、page、filename、metadata，否则返回安全 502。
  metadata 标量类型也必须相同，避免 Python 把 `true`、`1`、`1.0` 判为相等而漏报冲突。
  原始分支 score 不参与比较；只在一路出现的 Chunk 允许参与融合。
- 原因：按正文或 filename/page 去重会合并不同 Chunk；静默选择冲突 payload 会掩盖
  PostgreSQL/Qdrant 不一致。此检查只覆盖两路共同返回的 ID，不等于完整同步校验。
- 失败策略：任一路异常则 Hybrid 整体失败，不静默降级；不引入 outbox、自动同步或表。

## D-049：Hybrid 保持独立 API，日志与评测只表达已验证行为

- 状态：已确认并实现
- 决策：新增 `POST /retrieval/hybrid/search`，复用 Day 9 请求/响应结构；惰性构造，
  应用启动和 `/health` 不访问外部服务。保持 `/chat`、RAG `0.46` 和现有两路 API。
- 日志：成功请求含空结果输出 `hybrid_search_completed`，记录哈希、参数、身份、两路
  rank 和 RRF score；不记录 query、正文、metadata、tokens、向量或原始分支 score。
  复用分支服务会同时产生向量、BM25 两条完成日志；分支日志仍遵守各自既有契约。
- 实测：相同 24 Chunk、候选 20、评估 Top 5、12 个正样本中，Hybrid
  Hit@1/Hit@5/MRR@5 为 `0.917/1.000/0.944`，补回向量 Top 5 漏检 1 题。
  3 个负样本返回率仍为 1.0，RRF 不提供拒答；结论仅限此受控小样本。
- 边界：不实现 Day 12 Rerank，不调用付费 API；实现阶段未修改 `PLAN.md`。
  2026-10-28 用户确认审查、测试与修复通过，单独授权勾选 Day 11 四项任务并更新开发
  日志；该完成标记不授权 Git 发布或开始 Day 12，也不改变上述技术决策。

## D-050：Day12 固定本地CPU模型和安全载入

- 已实现并通过2026-10-28真实验收。固定BAAI/bge-reranker-base revision
  2cfc18c9415c912f9d8155881c133215df768a70，CPU/512 token，默认batch4，范围1..8。
- 复用sentence-transformers==5.3.0；缓存优先、匿名限六个安全文件、safetensors、
  trust_remote_code=False、惰性加载。空候选不加载，瞬时网络错误最多重试3次。
- 原因：数据和模型本地运行、固定版本可复现，不增加供应商Key、依赖或外部费用。

## D-051：固定Hybrid20→Rerank5，分数与名次独立

- 显式Identity保留原始logit，只作排序，不与Cosine/BM25/RRF相加或作拒答阈值。
- 全部至多20候选按位置一一映射；校验数量/唯一性/有限分数；按
  (-logit, hybrid_rank, doc_id, chunk_index, chunk_id)排序后固定取5。
- rank_change=hybrid_rank-rerank_rank。日志记录全部候选名次、logit与耗时，不含正文。
- 原因：不能提前截成5，不能用重复正文作身份，平分必须可复现。

## D-052：完整query预检，只显式截passage

- 使用模型tokenizer成对预检；完整query加特殊token不能为passage留空间则安全422。
- 包装CrossEncoder内部tokenizer，将truncation=True变为only_second/max_length512，
  记录截断数，不静默截query，不通过解码后再编码来猜测长度。
- 原因：本机5.3.0的predict内部固定truncation=True，仅设置max_length不足以保护query。

## D-053：按Day12授权升级Chat并保留向量证据门

- 附件明确授权独立rerank API与/chat接入；D-049“Day11不改/chat”属于历史日范围。
  Hybrid内部保存两路raw score，不参与RRF、不进入Hybrid公共响应。
- RAG在Rerank Top5后仅用vector_score>=0.46；BM25-only不作生成依据。保持固定拒答、
  后端sources与JSON/SSE，承认保守证据门可能损失召回。
- 原因：RRF/logit量纲不可套入0.46；当前未校准BM25-only的可信生成门。
- 2026-10-28同语料指标0.917/1.000/0.958，Hit@1不变、MRR小幅提升；无关候选升位如实记录，
  不据小样本改阈值、模型、权重或切分。当日标准401/12、全真实413，无付费LLM调用；
  不把这组历史结果当作10月29后续变更的重测证据。
- Day11先独立推送b68b590；Day12实现阶段按原附件保留PLAN。2026-10-29用户确认Day12完成，
  单独授权勾选四项任务和更新日志，2026-10-29标准403/12通过；之后按用户要求收录Day12本地提交，提交前重跑403/12（15.93s），未推送，Day13未开始。
