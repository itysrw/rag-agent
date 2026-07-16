# 项目完整交接包

更新时间：2026-07-15（America/New_York）
仓库：D:\2019\rag-agent

当前阶段：Day 1 至 Day 5 已提交并推送；Day 6 本地 BGE Embedding 已在工作区实现，
完成审查和两个 P2 修复，PLAN.md 的 Day 6 状态已获用户授权更新；Day 6 尚未提交或推送。
当前暂停功能开发。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供后端 API；
- 支持 PDF、Markdown、TXT 上传、解析、分页切分和元数据持久化；
- 使用本地 Embedding、Qdrant、BM25、RRF、Rerank 实现检索增强；
- 使用 OpenAI-compatible LLM 生成带来源引用的回答；
- 使用 LangGraph 实现检索决策、工具调用和多轮记忆；
- PostgreSQL 保存业务数据；
- 使用评测数据集量化检索质量、答案质量和延迟；
- Streamlit 提供演示界面，最终由 Docker Compose 一键启动；
- 最终形成 README、架构图、评测报告、简历描述和面试材料。

PLAN.md 是 25 天范围与顺序的唯一计划基线。未来能力不得写成已完成事实。

### 2. 新会话必须完整阅读的资料

按顺序阅读：

1. HANDOFF.md
2. STATUS.md
3. DECISIONS.md
4. TODO.md
5. AGENTS.md
6. README.md
7. PLAN.md，只读，除非用户明确授权修改
8. docs/architecture.md
9. docs/day5-chunk-size-comparison.md
10. .env.example，只包含公开默认值和占位符；禁止读取 .env
11. backend/requirements.txt
12. backend/app/api/documents.py
13. backend/app/core/config.py
14. backend/app/core/database.py
15. backend/app/models/document.py
16. backend/app/models/chunk.py
17. backend/app/models/init_db.py
18. backend/app/services/document_parser.py
19. backend/app/services/document_storage.py
20. backend/app/services/text_splitter.py
21. backend/app/services/embedding.py
22. backend/app/commands/__init__.py
23. backend/app/commands/embed_document.py
24. backend/tests/test_text_splitter.py
25. backend/tests/test_documents.py
26. backend/tests/test_documents_postgres.py
27. backend/tests/test_embedding.py
28. backend/tests/test_embedding_integration.py

禁止读取或输出 .env、API Key、数据库真实密码。不要读取无关 .agents/ 内容。

### 3. 当前检查点

必须同时保留以下四个事实：

1. Day 1 至 Day 5 的功能实现、验收、本地提交和远端推送已完成。
2. Day 6 的工作区实现已完成范围受限二次审查，两个 P2 已修复，没有代码阻断项。
3. Day 6 尚无 Git 提交或推送，所有实现仍是未提交工作区内容。
4. PLAN.md 的 Day 6 五项复选框已勾选，开发日志已标记“已完成”。

因此，“Day 6 已完成计划状态更新”不能被误写为“Day 6 已提交并推送”。

### 4. Git、远端与工作区精确状态

| 项目 | 当前值 |
|---|---|
| 分支 | master |
| HEAD | ecadc3296b038bad169b2bb78238f8ffd77e43d8 |
| HEAD 摘要 | ecadc32 docs: refresh Day 5 handoff |
| Day 5 实现提交 | a989837bbf8bae1cf866beda034130a514152378 |
| 上游 | origin/master |
| 本地跟踪引用 origin/master | ecadc3296b038bad169b2bb78238f8ffd77e43d8 |
| 基于本地跟踪引用的 ahead/behind | 0/0 |
| 暂存区 | 空 |
| Day 6 提交 | 无 |
| Day 6 推送 | 无 |
| PLAN.md 工作区差异 | Day 6 五项已勾选，开发日志已标记完成 |
| 远端实时 HEAD | 待确认 |

远端说明：

- Day 5 交接时已成功确认远端 origin/master 与本地 HEAD 相同。
- 本次交接生成期间，git ls-remote origin refs/heads/master 首次无法连接 GitHub；
  授权后的查询继续超时并被终止。
- 所以本地 origin/master 和 ahead/behind 是精确的本地状态，但 GitHub 此刻的实时 HEAD
  不得自行假定，标记为待确认。

当前已修改的跟踪文件：

- .env.example
- DECISIONS.md
- HANDOFF.md
- PLAN.md
- README.md
- STATUS.md
- TODO.md
- backend/app/core/config.py
- backend/requirements.txt
- docs/architecture.md

当前 Day 6 新增且未跟踪的文件：

- backend/app/commands/__init__.py
- backend/app/commands/embed_document.py
- backend/app/services/embedding.py
- backend/tests/test_embedding.py
- backend/tests/test_embedding_integration.py

另有一个无关的未跟踪 .agents/ 文件。它不是项目功能或交接包的一部分，未读取、未修改、
未暂存，未来提交时必须排除。

.env 未读取、未输出、未修改、未提交。data/models/ 是 Git 忽略的本地模型缓存，
不得提交模型文件。

### 5. 已完成内容

#### Day 1：项目边界与架构

- 建立范围、目录、README、目标架构和 GitHub 远端。
- 提交：751dc40 docs: complete Day 1 project architecture。

#### Day 2：FastAPI 骨架

- FastAPI 应用、GET /health、聊天和上传占位路由。
- 配置、Loguru、请求日志。
- 提交：607645d feat: complete Day 2 FastAPI foundation。

#### Day 3：DeepSeek 对话

- OpenAI-compatible LLMClient。
- 默认 deepseek-v4-flash，默认关闭思考模式。
- POST /chat 支持普通 JSON 和 SSE。
- 配置缺失 503、普通上游失败 502、SSE 流错误为通用 error 事件。
- 实现提交 177ad2b，交接提交 a27a3f5。

#### Day 4：文档上传、解析与 PostgreSQL

- POST /documents/upload 支持 PDF、Markdown、TXT。
- 20 MiB 实际字节上限，PDF 最多 500 页，1 MiB 分块读取。
- UUID.part 临时文件、安全文件名/MIME/PDF 签名验证。
- PDF 空白页和一基页码保留，以 form-feed 序列化到 documents.extracted_text。
- SQLAlchemy 2.x、psycopg 3、同步事务和文件补偿。
- 实现提交 623989f，交接提交 a64a0cc。

#### Day 5：按页 token 切分与 Chunk 持久化

- langchain-text-splitters 1.1.x 与 tiktoken 0.13.x，不安装完整 LangChain。
- ChunkingSettings 默认 500/100/o200k_base。
- split_pages() 逐页切分，禁止跨页；空白页不生成 Chunk，页码不压缩。
- chunks 表使用 UUID 主键、显式 chunk_index、JSONB、外键、索引和级联删除。
- Document 与 Chunks 在同一事务中写入，必须先 flush Document 再 flush Chunks。
- 上传成功响应不增加 chunk_count 或正文。
- 300/500/800 token 结构实验已记录，不等于检索质量结论。
- 实现提交 a989837，交接提交 ecadc32，均已推送。

#### Day 6：本地 BGE Embedding，工作区未提交

- 只使用 BAAI/bge-small-zh-v1.5，不使用 OpenAI Embedding。
- DeepSeek Key 只用于已有 LLM，不得用作 Embedding 凭据。
- revision 固定为 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4。
- 仅 CPU，向量维度固定 512，必须归一化。
- 外层批处理最大 32，保持输入顺序。
- 文档 Chunk 直接编码，不添加查询侧 instruction。
- 使用 BGE tokenizer 包含特殊 token 计数；超长输入在 inference 前失败。
- 缓存优先，固定 snapshot 本地加载，禁止 trust_remote_code。
- 只重试连接、超时、HTTP 429 和 5xx；最多 3 次重试，退避 1/2/4 秒。
- 向量只存在内存，不写数据库、Chunk.metadata、pgvector 或 Qdrant。
- 新增只读命令按 chunk_index 读取指定文档 Chunks，打印安全摘要。
- 未修改 POST /documents/upload，也没有新增 HTTP API。

### 6. Day 6 精确代码位置与接口

#### 6.1 配置

文件：backend/app/core/config.py

常量：

- EMBEDDING_MODEL_NAME = BAAI/bge-small-zh-v1.5
- EMBEDDING_MODEL_REVISION = 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4
- EMBEDDING_DIMENSION = 512
- EMBEDDING_MAX_BATCH_SIZE = 32

类与函数：

- EmbeddingSettings
- EmbeddingSettings.resolve_cache_dir()
- EmbeddingSettings.require_normalized_vectors()
- get_embedding_settings()

环境变量：

- EMBEDDING_MODEL_NAME
- EMBEDDING_MODEL_REVISION
- EMBEDDING_DIMENSION
- EMBEDDING_BATCH_SIZE
- EMBEDDING_DEVICE
- EMBEDDING_NORMALIZE
- EMBEDDING_CACHE_DIR
- EMBEDDING_DOWNLOAD_MAX_RETRIES
- EMBEDDING_RETRY_BASE_DELAY_SECONDS

模型名、revision、维度和 device 使用 Literal 固定。batch_size 只允许 1 至 32；
normalize_embeddings 必须为 true；重试数只允许 0 至 3。

#### 6.2 Embedding 服务

文件：backend/app/services/embedding.py

公开数据结构：

- ChunkEmbeddingInput(chunk_id, content)
- EmbeddedChunk(chunk_id, vector)

公开异常：

- EmbeddingError
- ModelDownloadError
- ModelLoadError
- EmbeddingInputError
- EmbeddingInputTooLongError
- ChunkEmbeddingInputTooLongError
- EmbeddingResultError

公开函数与类：

- ensure_model_snapshot(settings, downloader=..., sleep=...)
- load_embedding_model(model_path, settings)
- validate_model_input_length(model, text)
- EmbeddingClient
- EmbeddingClient.dimension
- EmbeddingClient.embed_documents(texts)
- embed_chunks(chunks, client)
- get_embedding_client()

关键行为：

1. 空输入返回空列表，不解析 snapshot 或加载模型。
2. 空白文本、裸字符串序列、重复 Chunk UUID 会在模型工作前失败。
3. 首次访问先找固定 revision 本地缓存，缓存缺失后才匿名联网。
4. 模型加载只使用本地 snapshot、CPU 和 trust_remote_code=False。
5. 每条文本先以 BGE tokenizer 执行 add_special_tokens=True、truncation=False。
6. 所有文本预检通过后才分批 inference，防止部分输入先产生向量。
7. 结果必须与输入数量相同、每条 512 维、数值有限、范数约为 1。
8. 向量按输入位置绑定 Chunk UUID，不依赖 UUID 排序。

#### 6.3 只读命令

文件：backend/app/commands/embed_document.py

公开结构与函数：

- DocumentChunksNotFoundError
- EmbeddingConfigurationError
- EmbeddingSummary
- embed_document()
- print_summary()
- build_parser()
- main()

命令：

    .\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>

查询：

- Chunk.doc_id == document_id
- order_by(Chunk.chunk_index)

安全输出字段：

- document_id
- model
- revision
- device
- chunk_count
- embedding_dimension
- normalized
- status

命令不打印 Chunk 正文或向量值，不写 PostgreSQL 或 Qdrant。

#### 6.4 两个 P2 修复

P2-1：Embedding 配置错误被误报为数据库不可用。

- 根因：client_factory() 产生的 Pydantic ValidationError 与数据库异常共用 main() 捕获分支。
- 修复：embed_document() 在 Embedding 客户端创建边界将 ValidationError 转换为
  EmbeddingConfigurationError。
- 保留：get_session_factory() 的 DatabaseConfigurationError、数据库配置 ValidationError
  和 SQLAlchemyError 仍归类为数据库不可用。
- 回归测试：
  test_command_reports_embedding_configuration_error_separately_from_database。

P2-2：缓存目录创建错误逃逸异常边界。

- 根因：settings.cache_dir.mkdir() 位于下载异常边界之外。
- 修复：捕获 OSError 并转为 ModelDownloadError。
- 安全性：消息不包含本机缓存路径；异常链保留；失败发生在 downloader 前。
- 回归测试：test_cache_path_file_is_wrapped_before_download。

### 7. 当前依赖与运行命令

Python：3.11.15。

Day 6 requirements 新增：

    sentence-transformers==5.3.0

当前虚拟环境已解析：

- sentence-transformers 5.3.0
- torch 2.13.0
- transformers 5.14.0
- huggingface-hub 1.23.0

安装：

    .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

显式建表：

    .\.venv\Scripts\python.exe -m backend.app.models.init_db

启动后端：

    .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

标准测试：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v

Embedding 单元测试：

    .\.venv\Scripts\python.exe -m pytest backend/tests/test_embedding.py -v

可选真实 BGE：

    $env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_embedding_integration.py -v

### 8. 当前接口与禁止修改的契约

已注册 HTTP 接口：

- GET /health
- POST /chat
- POST /documents/upload

POST /documents/upload 成功 201 响应字段仍严格为：

- id
- filename
- size
- status
- created_at

不得为了 Day 6 增加 chunk_count、embedding、正文或向量字段。

必须保留：

- PDF 页边界和一基页码；
- split_pages() 按页切分；
- Document 第一次 flush、Chunks 第二次 flush；
- 上传失败补偿；
- 应用启动与 GET /health 不依赖 PostgreSQL；
- Day 6 Embedding 与上传事务隔离。

### 9. 已确认技术决策及原因

完整编号以 DECISIONS.md 为准。Day 5 与 Day 6 关键决策：

1. PLAN.md 控制范围，防止提前实现后续 Day。
2. Day 5 使用固定 o200k_base 作为可复现切分计数基准，因为默认 len 是字符数。
3. 每页独立切分，默认 500/100，避免跨页并保留未来引用页码。
4. Chunk UUID 只表示身份，chunk_index 才表示稳定顺序。
5. ORM 属性 chunk_metadata 映射数据库 metadata，避免 SQLAlchemy 保留名冲突。
6. Document 和 Chunks 同事务两次 flush，真实 PostgreSQL 已证明一次 flush 不可靠。
7. Day 5 只创建新表，不回填历史文档，也不提前引入 Alembic。
8. Day 6 选择固定 revision 的本地 BGE，避免正文发送外部服务并消除 Embedding API Key。
9. BGE tokenizer 单独预检，因为 o200k_base 与 BERT tokenizer 不可互换。
10. Day 6 向量只存内存，Qdrant 持久化属于 Day 7。
11. 下载只重试瞬时错误，确定性配置、权限、404、缓存损坏、设备和推理错误不重试。
12. 配置错误、数据库错误、下载错误必须分层分类并对用户输出安全消息。

DECISIONS.md 中原 D-012 的 Day 6 供应商待确认状态已被 D-024 的本地 BGE 决策取代；
不能继续把供应商写成待确认。

### 10. 已尝试但失败、已否决或未采用的方案

实际失败后修正：

- Document 与 Chunks 只做一次 flush：真实 PostgreSQL 触发 chunks_doc_id_fkey，已改为两次 flush。
- Embedding ValidationError 与数据库异常共用分类：配置错误被误报数据库不可用，已修复。
- cache_dir.mkdir() 位于下载异常边界外：FileExistsError 可逃逸，已修复。
- 本次远端实时查询：无法连接 GitHub，授权查询继续超时；实时远端状态待确认。

明确否决或未采用：

- OpenAI Embedding：Day 6 不使用，避免外部依赖和正文外发。
- 使用 DeepSeek Key 做 Embedding：否决；DeepSeek 只承担已有 LLM。
- 千问 Embedding：不进入 Day 6。
- SentenceTransformers 静默截断：禁止，必须先用 BGE tokenizer 检查。
- 对所有下载/加载/推理错误统一重试：否决，只重试瞬时网络错误。
- 把 Embedding 放入 POST /documents/upload 事务：否决，会扩大失败面和事务时长。
- Day 6 写 PostgreSQL、pgvector、Chunk.metadata 或 Qdrant：否决，属于 Day 7。
- Day 6 新增 Embedding HTTP API：未采用，当前只提供本地命令。
- 文档 passage 添加 query instruction：否决，查询指令只属于未来 query 侧。
- 安装完整 LangChain：否决，只使用 langchain-text-splitters。
- 把 300/500/800 结构实验写成检索质量结论：禁止，没有检索评测证据。

### 11. 不可违反的约束

- 使用 Python 3.11，后端代码位于 backend/。
- 公共函数使用类型标注；测试使用 pytest。
- 不得实现超过用户授权的 PLAN.md Day。
- 不得重新完成或破坏 Day 1 至 Day 5。
- 不得擅自推翻 DECISIONS.md。
- 不确定信息必须写“待确认”，禁止自行补全。
- 不得读取、输出或提交 .env、API Key、数据库真实密码。
- 不得读取、修改、暂存或提交无关 .agents/。
- 不得提交 data/models/ 模型缓存。
- 未经明确授权不得修改 PLAN.md。
- commit 和 push 必须分别获得明确授权。
- 不得开始 Day 7，除非 Day 6 检查点完成且用户明确授权。
- 当前用户要求暂停功能开发；交接完成后等待下一指令。

### 12. 测试、当前错误和日志

本次交接刷新实际运行：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v

结果：

- collected 112
- 110 passed
- 2 skipped
- 1 warning
- 26.93 秒

跳过：

- 真实 PostgreSQL 集成测试；
- RUN_LOCAL_EMBEDDING_INTEGRATION 未开启的真实 BGE 测试。

修复报告证据：

- 两个目标回归测试：2 passed。
- backend/tests/test_embedding.py：50 passed，1 warning。
- 完整套件：110 passed，2 skipped，1 warning。
- 真实 PostgreSQL：1 passed，1 warning。
- pip check、compileall、git diff --check：通过。

真实 BGE 证据边界：

- P2 修复前曾通过首次模型下载、CPU 推理和 HF_HUB_OFFLINE=1 缓存重跑。
- P2 修复后未启用真实 BGE 测试。
- 所以修复后真实 BGE 结果为待确认，不能写成当前轮实际通过。

当前失败测试：无。

当前警告：

    PytestCacheWarning: could not create cache path
    D:\2019\rag-agent\.pytest_cache\v\cache\nodeids
    [WinError 5] 拒绝访问

该警告不影响测试通过，根因待确认。

远端查询错误：

    fatal: unable to access GitHub remote:
    Failed to connect to github.com port 443

授权查询随后继续超时并被终止；远端实时 HEAD 待确认。

### 13. 当前错误、缺口和残余风险

- 当前没有代码阻断项或失败测试。
- P2 修复后真实 BGE CPU 集成测试未重跑。
- 当前真实数据库历史扫描曾得到 chunk_count=0，没有可直接用于真实命令验收的现成文档。
- 创建真实验收文档会修改数据库和上传目录，必须另行授权。
- 首次模型下载依赖 Hugging Face；代理、磁盘、缓存损坏和离线部署策略仍需验证。
- .pytest_cache 权限警告持续存在。
- GitHub 远端实时状态当前无法核验。
- o200k_base 首次使用也需要词表缓存；新环境预热策略待确认。
- 文件移动后进程立即崩溃仍可能留下孤儿文件。
- _cleanup_failed_upload() 使用 SQLAlchemy 私有事务 _state，升级兼容性待确认。
- LF→CRLF 提示持续存在，.gitattributes 策略待确认。
- PLAN.md 已按用户授权更新 Day 6；后续不得在没有新授权时继续修改。

### 14. 待完成任务

1. 新会话只读复核交接包、Git 工作区和 PLAN.md 状态。
2. 由用户决定是否重跑 P2 修复后的真实 BGE 集成测试。
3. 如需真实文档命令验收，先由用户授权创建或选择带 Chunk 的 Document。
4. PLAN.md 的 Day 6 状态已更新，无需重复修改。
5. 仅在用户授权后暂存并提交；push 必须另行授权。
6. Day 7 Qdrant 不得在上述检查点完成前开始。

### 15. 接下来最多 5 个具体步骤

1. 只读执行 Git 状态、HEAD、上游、工作区差异和 PLAN.md 核对。
2. 复述“Day 6 已实现且 PLAN.md 已更新，但未提交；修复后真实 BGE 待确认”。
3. 等待用户从真实 BGE 验收、提交或其他只读检查中指定唯一动作。
4. 若用户授权提交，先重新跑标准测试、pip check、compileall 和 git diff --check，
   并明确排除 .env、.agents/、data/models/。
5. commit 与 push 分别等待授权；Day 7 另行等待明确授权。

### 16. 验收标准

Day 6 代码验收：

- 本地固定 BGE，不依赖 OpenAI 或 DeepSeek Embedding Key；
- CPU、512 维、归一化、批量不超过 32；
- BGE tokenizer 推理前检查且不静默截断；
- 瞬时下载错误最多重试 3 次，退避 1/2/4；
- Chunk UUID 与向量顺序绑定正确；
- 命令只读且输出安全摘要；
- Embedding 配置错误不误报数据库不可用；
- 缓存目录创建失败转换为安全 ModelDownloadError；
- 不实现 Qdrant 或向量持久化；
- 完整测试无失败。

交接包验收：

- HANDOFF.md、STATUS.md、DECISIONS.md、TODO.md、README.md、docs/architecture.md 状态一致；
- 精确记录分支、HEAD、工作区、测试结果和未验证项；
- PLAN.md 仅包含本次获授权的 Day 6 状态更新；
- .env、.agents/、data/models/ 不进入范围；
- 不提交、不推送；
- 所有不确定内容标记为待确认；
- 新对话不依赖当前聊天即可继续。

## B. 300 字以内快速恢复摘要

仓库 D:\2019\rag-agent，master，HEAD ecadc329；本地 origin/master 跟踪引用相同，
ahead/behind 0/0，远端实时 HEAD 因网络超时待确认。Day 1-5 已提交推送。
Day 6 已在工作区实现固定本地 BGE：CPU、512 维、归一化、批量 32、tokenizer 预检、
瞬时下载重试、只读内存命令；两个 P2 已修复。标准测试 110 passed/2 skipped/1 warning。
Day 6 未提交、未推送，PLAN.md 的 Day 6 已更新；修复后真实 BGE 测试待确认。排除 .env、.agents/
和模型缓存，先只读复核后等待授权。

## C. 新对话第一条启动提示词

这是一个已有项目的新工作会话，仓库位于 D:\2019\rag-agent。

请先完整阅读：

1. HANDOFF.md
2. STATUS.md
3. DECISIONS.md
4. TODO.md
5. AGENTS.md
6. README.md
7. PLAN.md
8. docs/architecture.md
9. docs/day5-chunk-size-comparison.md
10. .env.example
11. backend/requirements.txt
12. backend/app/core/config.py
13. backend/app/core/database.py
14. backend/app/models/document.py
15. backend/app/models/chunk.py
16. backend/app/api/documents.py
17. backend/app/services/text_splitter.py
18. backend/app/services/embedding.py
19. backend/app/commands/embed_document.py
20. backend/tests/test_embedding.py
21. backend/tests/test_embedding_integration.py
22. backend/tests/test_documents_postgres.py

执行规则：

- 第一轮只读检查，不要立即改代码。
- 不要重新完成 Day 1-5，不要开始 Day 7。
- 不要擅自推翻 DECISIONS.md。
- 不确定内容标记为“待确认”，禁止自行补全。
- 不要读取、输出或提交 .env、API Key、数据库真实密码。
- 不要读取或提交无关 .agents/，不要提交 data/models/。
- PLAN.md 的 Day 6 已更新；不要继续修改 PLAN.md，除非我再次明确授权。
- 不要提交或推送；commit 和 push 必须分别获得明确授权。

请先回复：

1. 项目最终目标和 Day 1-6 当前状态；
2. 精确 Git、暂存、未提交和远端核验状态；
3. Day 6 技术决策、两个 P2 修复及原因；
4. 当前失败、警告、未验证项、文档矛盾和残余风险；
5. 接下来最多 5 个步骤。

当前唯一目标：

只读确认交接包和修复后的 Day 6 工作区，准确复述后等待我指定下一动作。

本轮验收标准：

不改代码，不读取 .env 或无关 .agents/，不继续修改 PLAN.md，不提交、不推送；
准确识别 HEAD ecadc329、PLAN.md 的 Day 6 已更新、Day 6 未提交范围、110 passed/2 skipped/1 warning、
远端实时 HEAD 待确认、修复后真实 BGE 测试待确认，以及两个已修复 P2。
