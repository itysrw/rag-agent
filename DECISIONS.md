# 技术决策记录

更新时间：2026-07-16（America/New_York）

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
