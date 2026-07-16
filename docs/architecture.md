# 架构说明

更新时间：2026-07-15（America/New_York）

本文严格区分：

- 已提交并推送的 Day 1 至 Day 5；
- 当前工作区已实现但未提交的 Day 6；
- 尚未实现的 Day 7 及以后目标。

## 当前实现架构

~~~mermaid
flowchart LR
    client["调用方 / Swagger UI"] --> api["FastAPI app<br/>backend/app/main.py"]

    api --> health["GET /health"]
    api --> chat["POST /chat"]
    api --> upload["POST /documents/upload"]

    chat --> llm["LLMClient<br/>OpenAI-compatible"]
    llm --> deepseek["DeepSeek V4 Flash<br/>仅 LLM"]

    upload --> storage["UUID.part 分块存储"]
    storage --> parser["PDF / Markdown / TXT 解析"]
    parser --> pages["PageText<br/>一基页码"]
    pages --> splitter["split_pages()<br/>o200k_base · 500/100 · 按页"]
    splitter --> chunks["PostgreSQL chunks<br/>有序 · JSONB"]
    pages --> documents["PostgreSQL documents<br/>extracted_text"]

    operator["本地操作者"] --> command["python -m backend.app.commands.embed_document<br/>--document-id UUID"]
    command --> ordered["SELECT Chunk<br/>ORDER BY chunk_index"]
    ordered --> embedding["EmbeddingClient"]
    embedding --> snapshot["固定 BGE snapshot<br/>本地缓存优先"]
    snapshot --> tokenizer["BGE tokenizer 预检<br/>包含特殊 token · 禁止截断"]
    tokenizer --> inference["SentenceTransformers CPU<br/>批量 ≤ 32"]
    inference --> vectors["512 维归一化向量<br/>仅内存"]
    vectors --> summary["安全摘要<br/>不含正文和向量值"]

    chunks --> ordered
~~~

关键隔离边界：

- 上传 API 不调用 EmbeddingClient，Day 6 不扩大上传事务。
- Embedding 命令只读 documents/chunks，不写 PostgreSQL。
- 向量只存在于当前进程内存，不写 Chunk.metadata、pgvector 或 Qdrant。
- DeepSeek Key 只属于已有 LLM 链路，不参与 Embedding。
- FastAPI 当前没有新增 Embedding 或检索 HTTP 接口。

## 当前 HTTP 接口

| 方法与路径 | 状态 |
|---|---|
| GET /health | 已实现 |
| POST /chat，stream=false | 已实现，返回完整 JSON |
| POST /chat，stream=true | 已实现，返回 SSE delta 与 DONE |
| POST /documents/upload | 已实现，支持 PDF/MD/TXT |

Day 6 只有本地命令入口，没有新增 HTTP 路由。

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
- sentence-transformers==5.3.0 为 Day 6 新依赖。
- 当前环境已解析到 torch 2.13.0、transformers 5.14.0、huggingface-hub 1.23.0。

所有相对上传和模型缓存路径均从仓库根目录解析，不依赖当前工作目录。
数据库仍通过 python -m backend.app.models.init_db 显式建表，应用启动和 GET /health
不初始化或探测 PostgreSQL。

## 尚未实现

- Qdrant 容器、collection 和向量持久化；
- pgvector 或 PostgreSQL 向量字段；
- POST /retrieval/search；
- query embedding 和 BGE query instruction；
- BM25、RRF、Rerank；
- RAG prompt 与来源引用；
- LangGraph、Agent 工具和记忆；
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
- agent/ 留给 Day 13 至 Day 16。
- 不得为未来 Day 提前引入未验证抽象。
- PLAN.md 未经用户明确授权不得修改。
