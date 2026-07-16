# 项目完整交接包

更新时间：2026-07-16（America/New_York）
仓库：`D:\2019\rag-agent`

> 本文件是独立交接入口，不依赖历史聊天。当前已暂停功能开发；接手者第一轮只读核验，
> 不得立即修改代码。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供后端 API；
- 支持 PDF、Markdown、TXT 上传、解析、按页切分和元数据持久化；
- 使用本地 BGE、Qdrant、BM25、RRF、Rerank 实现检索增强；
- 使用 OpenAI-compatible LLM 生成带来源引用的答案；
- 使用 LangGraph 实现检索决策、工具调用和多轮记忆；
- PostgreSQL 保存业务数据，Qdrant 保存向量；
- 用评测数据集量化检索质量、答案质量和延迟；
- Streamlit 提供演示界面，最终由 Docker Compose 一键启动；
- 最终形成 README、架构图、评测报告、简历描述和面试材料。

`PLAN.md` 是 25 天范围和顺序的基线。未来目标不得写成已经完成。

### 2. 新会话必须按顺序完整阅读

1. `HANDOFF.md`
2. `STATUS.md`
3. `DECISIONS.md`
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`，只读，除非用户明确授权修改
8. `docs/architecture.md`
9. `docs/day5-chunk-size-comparison.md`
10. `docs/day7-retrieval-smoke.md`
11. `.env.example`；禁止读取 `.env`
12. `backend/requirements.txt`
13. `backend/app/core/config.py`
14. `backend/app/core/database.py`
15. `backend/app/models/document.py`
16. `backend/app/models/chunk.py`
17. `backend/app/api/documents.py`
18. `backend/app/api/retrieval.py`
19. `backend/app/services/text_splitter.py`
20. `backend/app/services/embedding.py`
21. `backend/app/services/qdrant_store.py`
22. `backend/app/services/retrieval.py`
23. `backend/app/commands/embed_document.py`
24. `backend/app/commands/init_qdrant.py`
25. `backend/app/commands/index_document.py`
26. `backend/tests/test_embedding.py`
27. `backend/tests/test_embedding_integration.py`
28. `backend/tests/test_documents_postgres.py`
29. `backend/tests/test_index_document.py`
30. `backend/tests/test_qdrant_store.py`
31. `backend/tests/test_qdrant_integration.py`
32. `backend/tests/test_retrieval.py`

禁止读取或输出 `.env`、API Key、数据库真实密码。不要读取无关 `.agents/` 内容，
不要把 `.agents/` 或 `data/models/` 纳入项目提交。

### 3. 项目阶段与已完成内容

#### Day 1 至 Day 6：已提交

- Day 1：项目边界、目录、README、目标架构和 Git 远端。
- Day 2：FastAPI 骨架、`GET /health`、路由、配置和请求日志。
- Day 3：OpenAI-compatible `LLMClient`、DeepSeek 普通 JSON 与 SSE 对话。
- Day 4：PDF/Markdown/TXT 上传、解析、文件补偿与 PostgreSQL 文档持久化。
- Day 5：按页 `o200k_base` token 切分，默认 `500/100`；有序 Chunk、JSONB、
  级联删除和同事务持久化。
- Day 6：固定本地 `BAAI/bge-small-zh-v1.5` Embedding，CPU、512 维、归一化、
  批量不超过 32、BGE tokenizer 预检、固定 snapshot、本地缓存优先、瞬时下载重试、
  只读 `embed_document` 命令和两个 P2 修复。

Day 6 最近一次有效提交为：

```text
eefd397db1e20947016c22ffa26d1fefc894949d feat: complete Day 6 local BGE embeddings
```

`PLAN.md` 的 Day 6 五项已在该提交中勾选。用户随后明确授权更新 Day 7；Day 7
五项现已勾选，开发日志已记录实际实现和验收结果，Day 8 及以后未修改。

#### Day 7：已实现、验收并进入授权提交/推送检查点

Day 7 的边界是：通过显式命令把 PostgreSQL Chunk 向量化并写入 Qdrant，
再由独立检索 API 查询。当前完成：

- 固定 `qdrant-client==1.18.0` 与 `qdrant/qdrant:v1.18.1`；
- Qdrant 容器 `rag-agent-qdrant` 仅绑定 `127.0.0.1:6333`；
- 命名卷 `rag-agent-qdrant-data:/qdrant/storage`；
- `documents` collection 为 unnamed dense vector、512 维、Cosine；
- 显式 `init_qdrant` 初始化/校验命令；
- 显式 `index_document --document-id <UUID>` 索引命令；
- 稳定 Point ID 等于 `Chunk.chunk_id`，重复 upsert 幂等覆盖；
- 查询侧增加固定 BGE instruction，文档 Chunk 仍直接编码；
- 独立 `POST /retrieval/search`，请求只接受 `query`，固定 Top 5，不返回向量；
- 单元、契约、真实 Qdrant、真实 BGE、受控三页中文 PDF 相关性测试均已通过；
- Qdrant 容器重启后 `documents` collection 持久化校验通过。

Day 8 及以后尚未授权，不得开始。

### 4. Day 7 最终提交前 Git 快照

下表记录本次授权提交前的精确基线；Day 7 最终提交是包含本文件的下一条提交，
其 SHA 必须在新会话中用 `git rev-parse HEAD` 实时读取，不得自行补全。

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| HEAD | `eefd397db1e20947016c22ffa26d1fefc894949d` |
| HEAD 摘要 | `eefd397 feat: complete Day 6 local BGE embeddings` |
| 上游 | `origin/master` |
| 本地跟踪引用 `origin/master` | `eefd397db1e20947016c22ffa26d1fefc894949d` |
| 基于本地跟踪引用的 ahead/behind | `0/0` |
| 暂存区 | 空 |
| Day 7 提交 | 无 |
| Day 7 推送 | 无 |
| GitHub 远端实时 HEAD | 提交前已确认是 `eefd397db1e20947016c22ffa26d1fefc894949d` |

提交前已修改的跟踪文件：

- `.env.example`
- `DECISIONS.md`
- `HANDOFF.md`
- `README.md`
- `STATUS.md`
- `TODO.md`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/services/embedding.py`
- `backend/requirements.txt`
- `backend/tests/pdf_fixtures.py`
- `backend/tests/test_embedding.py`
- `docs/architecture.md`
- `pytest.ini`

提交前 Day 7 新增且未跟踪的文件：

- `backend/app/api/retrieval.py`
- `backend/app/commands/index_document.py`
- `backend/app/commands/init_qdrant.py`
- `backend/app/services/qdrant_store.py`
- `backend/app/services/retrieval.py`
- `backend/tests/test_index_document.py`
- `backend/tests/test_qdrant_integration.py`
- `backend/tests/test_qdrant_store.py`
- `backend/tests/test_retrieval.py`
- `docs/day7-retrieval-smoke.md`

另有一个无关的未跟踪 `.agents/` 文件。它没有被读取、修改或暂存，未来提交必须排除。
`.env` 没有被读取、输出、修改或暂存。`data/models/` 是 Git 忽略的本地模型缓存，
未来提交必须排除。`docker-compose.yml` 没有 Day 7 差异。

### 5. Day 6 精确实现、两个 P2 修复及原因

#### 5.1 固定配置

文件：`backend/app/core/config.py`

- `EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"`
- `EMBEDDING_MODEL_REVISION = "4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4"`
- `EMBEDDING_DIMENSION = 512`
- `EMBEDDING_MAX_BATCH_SIZE = 32`
- `EmbeddingSettings`：只允许 CPU，`normalize_embeddings=True`，批量 `1..32`，
  下载重试 `0..3`，默认退避基数 1 秒。

文件：`backend/app/services/embedding.py`

- 数据结构：`ChunkEmbeddingInput`、`EmbeddedChunk`；
- 核心接口：`ensure_model_snapshot()`、`load_embedding_model()`、
  `validate_model_input_length()`、`EmbeddingClient.embed_documents()`、
  `EmbeddingClient.embed_query()`、`embed_chunks()`、`get_embedding_client()`；
- 文档不加 query instruction；查询固定增加一次：
  `为这个句子生成表示以用于检索相关文章：`；
- 包含特殊 token、禁止截断；结果校验数量、512 维、有限值和单位范数；
- 只重试连接、超时、HTTP 429 和 5xx；最多 3 次重试，退避 1/2/4 秒；
- `local_files_only=True`、`trust_remote_code=False`，只从固定 snapshot 加载。

#### 5.2 P2-1：Embedding 配置错误被误报为数据库不可用

文件：`backend/app/commands/embed_document.py`

- 根因：`client_factory()` 产生的 Pydantic `ValidationError` 与数据库异常共用
  `main()` 捕获分支，导致 Embedding 配置错误被错误归类为数据库不可用。
- 修复：`embed_document()` 在创建 Embedding 客户端的边界把该异常转换为
  `EmbeddingConfigurationError`。
- 保留：`get_session_factory()` 的 `DatabaseConfigurationError`、数据库设置
  `ValidationError` 和 `SQLAlchemyError` 仍归类为数据库不可用。
- 回归测试：
  `test_command_reports_embedding_configuration_error_separately_from_database`。

#### 5.3 P2-2：缓存目录创建错误逃逸下载异常边界

文件：`backend/app/services/embedding.py`

- 根因：`settings.cache_dir.mkdir()` 位于下载异常边界之外；例如缓存路径实际是文件时，
  `FileExistsError` 会未经安全包装直接逃逸。
- 修复：捕获目录创建的 `OSError` 并转换为 `ModelDownloadError`。
- 安全性：用户消息不包含本机缓存路径，原始异常链保留，且失败发生在 downloader 调用前。
- 回归测试：`test_cache_path_file_is_wrapped_before_download`。

两个 P2 已随 `eefd397` 提交。修复后真实 BGE CPU 测试已重新执行并通过，
不再是“待确认”。

### 6. Day 7 精确代码位置、接口和参数

#### 6.1 配置与依赖

文件：`backend/app/core/config.py`

- `QDRANT_MAX_BATCH_SIZE = 32`
- `QdrantSettings`
- `get_qdrant_settings()`
- 默认：`host="localhost"`、`port=6333`、`collection="documents"`、
  `timeout_seconds=10.0`、`upsert_batch_size=32`
- 校验：端口 `1..65535`，host/collection 非空，timeout `>0`，batch `1..32`
- `QdrantSettings.build_url()` 返回无凭据的本地 REST URL。

文件：`backend/requirements.txt`

- `sentence-transformers==5.3.0`
- `qdrant-client==1.18.0`

#### 6.2 Qdrant 适配层

文件：`backend/app/services/qdrant_store.py`

- 常量：`QDRANT_SCHEMA_VERSION = 1`
- 数据结构：`VectorizedChunk`、`RetrievedChunk`
- 异常：`QdrantStoreError`、`QdrantUnavailableError`、
  `QdrantCollectionMismatchError`、`QdrantResultError`
- 服务：`QdrantVectorStore`
- 方法：`initialize_collection()`、`validate_collection()`、`upsert_chunks()`、`search()`
- 工厂：`get_qdrant_vector_store()`
- collection metadata 固定保存 schema version、模型名和 revision；不匹配即失败；
- 禁止用 `recreate_collection()` 隐式删除已有数据；
- payload 精确字段：`chunk_id`、`doc_id`、`chunk_index`、`content`、`page`、
  `filename`、`metadata`；
- `upsert(wait=True)`，每批不超过 32；
- `query_points(..., with_payload=True, with_vectors=False)`；
- 严格校验 vector、UUID、payload 和有限 score。

#### 6.3 显式命令

文件：`backend/app/commands/init_qdrant.py`

- `QdrantInitializationSummary`
- `initialize_qdrant()`
- `print_summary()`
- `main()`

命令：

```powershell
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
```

文件：`backend/app/commands/index_document.py`

- 异常：`DocumentIndexingError`、`DocumentNotFoundError`、
  `DocumentChunksNotFoundError`、`QdrantConfigurationError`
- 数据结构：`IndexSummary`
- 接口：`index_document()`、`print_summary()`、`build_parser()`、`main()`
- 查询按 `Chunk.chunk_index` 升序；PostgreSQL Session 在 BGE 和 Qdrant 工作前关闭；
- 输出只包含安全标识、collection、数量、维度和状态，不输出正文或向量。

命令：

```powershell
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
```

#### 6.4 检索服务与 HTTP API

文件：`backend/app/services/retrieval.py`

- `RETRIEVAL_TOP_K = 5`
- `RetrievalService.search(query)`
- `get_retrieval_service()`

文件：`backend/app/api/retrieval.py`

- `RetrievalSearchRequest`：只允许 `query`，`extra="forbid"`，去除首尾空白，
  长度 `1..4096`；
- `RetrievedChunkResponse`
- `RetrievalSearchResponse`
- `require_retrieval_service()`
- `search_retrieval()`
- 路由：`POST /retrieval/search`

响应：`{"results": [...]}`；每项包含 `chunk_id`、`doc_id`、`chunk_index`、
`content`、`page`、`filename`、`metadata`、`score`，不包含 vector。

错误映射：

- 空白、额外字段或请求过长：Pydantic `422`；
- BGE token 超限：`422`；
- Embedding 不可用、Qdrant 不可用、collection 缺失或不匹配：`503`；
- Qdrant Point/Payload 无效：安全 `502`。

文件：`backend/app/main.py`

- `create_app()` 注册 `retrieval_router`；
- 应用启动和 `GET /health` 仍不连接 PostgreSQL 或 Qdrant；
- Qdrant、BGE 配置和客户端仅在相关命令或检索路由调用时解析。

### 7. 不可违反的约束与禁止修改的契约

- 使用 Python 3.11；后端代码位于 `backend/`；公共函数使用类型注解；测试用 pytest。
- 不得提前实现 `PLAN.md` 后续 Day；Day 8 及以后未授权。
- 不得修改 `PLAN.md`，除非用户再次明确授权。
- 不得读取、输出、修改或提交 `.env`、API Key、数据库真实密码。
- 不得读取或提交无关 `.agents/`；不得提交 `data/models/`。
- 暂存、commit、push 是三个独立动作；commit 和 push 必须分别获得明确授权。
- 不得自动把上传接入 Embedding/Qdrant；不得把 Qdrant 加入上传事务。
- 不得把 `/chat` 接入检索；不得新增可调 `top_k`、doc filter、score threshold。
- 不得提前实现 BM25、Hybrid/RRF、Rerank、RAG、后台队列、outbox、删除同步。
- 不得用 `recreate_collection()` 自动重建不匹配的 collection。
- `POST /documents/upload` 成功 `201` 响应字段保持：
  `id`、`filename`、`size`、`status`、`created_at`；不得增加正文或向量。
- PDF 页边界和一基页码、`split_pages()` 按页切分、Document 第一次 flush、
  Chunks 第二次 flush、上传失败文件补偿必须保留。
- 文档 Chunk 不加 BGE query instruction；只有 `embed_query()` 添加一次固定 instruction。

### 8. 已确认技术决策及原因

完整决策编号见 `DECISIONS.md`。当前阶段最关键的是：

1. `PLAN.md` 控制范围：避免提前实现未来 Day，确保验收边界可复现。
2. Day 5 按页使用 `o200k_base`、默认 `500/100`：避免跨页并保留引用页码；
   `o200k_base` 与 BGE tokenizer 不可互换。
3. Document 与 Chunk 同事务分两次 flush：真实 PostgreSQL 已证明一次 flush 会先插入
   Chunk 并触发 `chunks_doc_id_fkey`。
4. Day 6 使用固定 revision 的本地 BGE：正文不外发，不需要 Embedding API Key，
   结果稳定可复现。
5. BGE tokenizer 独立预检：防止 SentenceTransformers 静默截断。
6. Day 6 向量仅在内存：不扩大上传事务失败面，持久化留给 Day 7。
7. Day 7 使用显式索引命令：PostgreSQL 与 Qdrant 无法组成真实事务；稳定 UUID 支持幂等重跑。
8. Qdrant 固定 unnamed 512/Cosine：与归一化 BGE 输出一致，避免动态 schema 漂移。
9. 查询使用固定 BGE instruction：符合 query/passage 编码语义，文档侧保持原契约。
10. 检索 API 固定 Top 5 且不返回向量：只验证 Day 7 基础链路，Day 9 参数不得提前进入。

### 9. 已尝试但失败、已修复或明确否决的方案

#### 实际失败后已修复

- Document 与无 ORM relationship 的 Chunk 只做一次 flush：真实 PostgreSQL 触发
  `chunks_doc_id_fkey`；已改为两次 flush。
- Day 6 Embedding 配置 `ValidationError` 与数据库异常共用分支：会误报数据库不可用；
  已以 `EmbeddingConfigurationError` 分离。
- `cache_dir.mkdir()` 位于下载异常边界外：`FileExistsError` 可逃逸；已包装为安全
  `ModelDownloadError`。
- Day 7 首次真实中文 PDF 测试复用了只支持 Latin-1 的最小 PDF fixture，触发
  `UnicodeEncodeError`；已修改 `backend/tests/pdf_fixtures.py`，`_build_text_stream()`
  对 Latin-1 使用 literal string，对中文使用 BOM UTF-16BE hex string，随后真实测试通过。
- 首次拉取 `qdrant/qdrant:v1.18.1` 时 Docker CLI 挂起且 daemon 暂时无响应；
  `Start-Service com.docker.service` 因无法打开服务失败。经明确授权重启 Docker Desktop 后
  daemon 恢复、镜像拉取成功，最终镜像 digest 为
  `sha256:45f8e3ddc2570a4d029877e1b5ec1045c19b3852b4e22a55c7f43b05aea0ca89`。
- GitHub 实时 HEAD 查询曾网络超时；最终提交前已恢复并确认远端 `master` 为 `eefd397`。

#### 明确否决或不在当前范围

- OpenAI Embedding、用 DeepSeek Key 做 Embedding、Day 6 千问 Embedding：否决。
- SentenceTransformers 静默截断：禁止，必须先做 BGE tokenizer 预检。
- 对所有下载/加载/推理错误统一重试：否决，只重试瞬时网络错误。
- 上传事务内 Embedding、自动 Qdrant 索引：否决。
- pgvector、Qdrant 自动重建、可调 Top K、filter、threshold、BM25、Hybrid、Rerank、RAG：
  均不属于 Day 7。
- 修改 `docker-compose.yml` 加入 Qdrant：本轮未采用；Day 7 使用固定本地容器命令。

### 10. 当前验证证据、错误、警告和日志

#### 标准测试

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

最近一次结果：

- Python `3.11.15`
- pytest `9.1.1`
- collected `157`
- `153 passed`
- `4 skipped`
- `1 warning`
- 用时 `16.42s`

四个跳过项：真实 PostgreSQL、真实 BGE、两个显式开关控制的真实 Qdrant 测试。
当前失败测试：无。

持续 warning：`.pytest_cache` 写入出现 `PytestCacheWarning: [WinError 5] Access is denied`。
不影响测试结果，根因待确认。

#### 修复后真实 BGE CPU 测试

```powershell
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_embedding_integration.py -v
```

结果：`1 passed, 1 warning in 16.37s`。使用固定 revision、CPU、512 维归一化向量。

#### 真实 Qdrant + BGE 测试

```powershell
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v
```

结果：`2 passed, 1 warning in 19.59s`。验证：

- collection 创建和严格校验；
- 相同 Chunk UUID 重复 upsert 后无重复 Point；
- payload 返回且 vector 不返回；
- `query_points()` 路径；
- 受控三页中文 PDF 的三个问题分别命中预期页 1、2、3，均为 Top 1；
- 临时 collection 在 `finally` 中清理。

2026-07-16 推送前将真实 BGE 与两个真实 Qdrant 用例合并复验，结果为
`3 passed, 1 warning in 13.55s`。

#### 其他检查

- `pip check`：通过，`No broken requirements found.`
- `compileall -q backend`：通过。
- `git diff --check`：通过；仅出现 LF 将转换为 CRLF 的提示，不是失败。
- Qdrant `/healthz`：通过。
- `documents` collection：容器重启后仍存在且 512/Cosine 校验通过。

### 11. 当前未验证项、文档矛盾和残余风险

- GitHub 提交前实时 `refs/heads/master` 已确认等于 `eefd397`；最终推送后的 SHA 以 Git 实时查询为准。
- `.pytest_cache` 的 WinError 5 权限根因：待确认。
- 本节 Git 表是 Day 7 最终提交前快照；最终提交和推送结果以 Git 实时状态为准。
- `PLAN.md` 已按用户明确授权更新 Day 7 五项和开发日志，Day 8 及以后保持不变。
- Qdrant 当前容器是本机运行状态，不代表新机器已完成部署；新环境复现待确认。
- 本地模型首次下载仍依赖 Hugging Face 网络；代理、磁盘空间、缓存损坏与完全离线部署策略待确认。
- PostgreSQL 与 Qdrant 不具备跨存储事务；索引命令依赖稳定 UUID 幂等重跑，但没有 outbox、
  自动重试、删除同步或一致性修复任务。
- `POST /retrieval/search` 是同步、固定 Top 5 的基础接口，尚无鉴权、限流、filter、threshold、
  BM25、Hybrid、Rerank 或质量评测集。
- 上传文件移动后进程立即崩溃仍可能留下孤儿文件；启动清理任务未实现。
- `_cleanup_failed_upload()` 读取 SQLAlchemy 私有事务 `_state`，升级兼容性待确认。
- Git 持续提示 LF→CRLF；是否增加 `.gitattributes` 待确认。
- 首次修改已有表结构时是否引入 Alembic：待确认。

已清除的旧矛盾：`ecadc329`、Day 6 未提交、`110 passed / 2 skipped / 1 warning`、
“修复后真实 BGE 待确认”都只是 Day 6 交接历史，不再代表当前状态。

### 12. 待完成任务与下一步具体操作（最多 5 步）

1. 新会话第一轮只读核对本文件、`STATUS.md`、`DECISIONS.md`、`TODO.md`、
   `README.md`、`PLAN.md` 和 Git 实时状态；先复述状态，不改代码。
2. 确认 Day 7 检查点提交包含代码、测试、文档和 `PLAN.md` 状态，且远端与本地一致。
3. 明确排除 `.env`、`.agents/` 和 `data/models/`。
4. 等用户指定唯一下一动作。
5. 未经用户明确授权不得开始 Day 8。

当前唯一下一步：Day 7 检查点完成后等待用户授权 Day 8；下一步最小改动为“无”。

### 13. 当前交接验收标准

- 用 Git 实时识别包含本文件的 Day 7 检查点 SHA，不把提交前基线 `eefd397` 当作最终 HEAD；
- 正确识别 Day 1-7 已完成，`PLAN.md` Day 7 五项和日志已更新；
- 确认暂存区为空、本地与远端一致，且只剩被排除的无关 `.agents/` 未跟踪文件；
- 正确复述标准测试 `153 passed / 4 skipped / 1 warning`；
- 正确复述修复后真实 BGE `1 passed`、真实 Qdrant+BGE `2 passed`；
- 正确识别两个已修复 P2 及原因；
- 明确 Day 8 及以后未经授权不得开始；
- 不读取或纳入 `.env`、无关 `.agents/`、`data/models/`。

## B. 300 字以内快速恢复摘要

仓库 `D:\2019\rag-agent`，`master`；`eefd397` 是 Day 7 提交前基线，最终 HEAD 必须用 Git 实时读取。Day 1-7 已完成，Day 7 实现显式 Chunk→BGE→Qdrant 索引和固定 Top 5 API，`PLAN.md` 五项及日志已更新。标准测试 `153 passed/4 skipped/1 warning`，真实 BGE/Qdrant `3 passed`。排除 `.env`、`.agents/`、`data/models/`；新会话先只读核验本地/远端一致后等待 Day 8 授权。

## C. 新对话的第一条启动提示词

```text
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
10. docs/day7-retrieval-smoke.md
11. .env.example
12. backend/requirements.txt
13. HANDOFF.md 列出的 Day 6/7 直接相关代码和测试

执行规则：
- 第一轮只读检查，不要立即改代码。
- 不要重新完成 Day 1-7，不要开始 Day 8。
- 不要擅自推翻 DECISIONS.md。
- 不确定内容标记为“待确认”，禁止自行补全。
- 不要读取、输出或提交 .env、API Key、数据库真实密码。
- 不要读取或提交无关 .agents/，不要提交 data/models/。
- 不要修改 PLAN.md，除非我明确授权。
- 暂存、commit、push 分别需要明确授权。

请先回复：
1. 项目最终目标和 Day 1-7 当前状态；
2. 精确 Git、暂存、未提交和远端核验状态；
3. Day 6 两个 P2 修复，以及 Day 7 技术决策和接口；
4. 当前失败、警告、未验证项、文档矛盾和残余风险；
5. 接下来最多 5 个步骤。

当前唯一目标：
只读确认 Day 7 检查点、交接包、PLAN.md 和本地/远端 Git 状态，准确复述后等待我指定下一动作。

本轮验收标准：
不改代码，不读取 .env 或无关 .agents/，不修改 PLAN.md，不提交、不推送；
通过 Git 实时识别 Day 7 最终 HEAD，确认本地与远端一致、PLAN.md Day 7 已更新、
153 passed/4 skipped/1 warning、真实 BGE/Qdrant 3 passed，并等待 Day 8 授权。
```
