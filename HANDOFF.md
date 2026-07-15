# 项目完整交接包

更新时间：2026-07-15（America/New_York）
仓库：`D:\2019\rag-agent`

当前阶段：Day 1 至 Day 5 的功能实现、验收和本地提交已完成。Day 5 实现提交为
`a989837bbf8bae1cf866beda034130a514152378`；当前暂停开发，不得自行推送或开始 Day 6。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供后端 API；
- 支持 PDF、Markdown、TXT 上传、解析、分页切分和元数据持久化；
- 使用 Embedding、Qdrant、BM25、RRF、Rerank 实现检索增强；
- 使用 OpenAI-compatible LLM 生成带来源引用的回答；
- 使用 LangGraph 实现检索决策、工具调用和多轮记忆；
- PostgreSQL 保存业务数据，以评测数据集量化质量和延迟；
- Streamlit 提供演示界面，最终由 Docker Compose 一键启动；
- 最终形成 README、架构图、评测报告、简历描述和面试材料。

`PLAN.md` 是 25 天范围与顺序的唯一计划基线。未来能力不得写成已完成事实。

### 2. 新会话必须阅读的资料

按顺序完整阅读：

1. `HANDOFF.md`
2. `STATUS.md`
3. `DECISIONS.md`
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`（只读，除非用户明确授权修改）
8. `docs/architecture.md`
9. `docs/day5-chunk-size-comparison.md`
10. `backend/app/api/documents.py`
11. `backend/app/core/config.py`
12. `backend/app/core/database.py`
13. `backend/app/models/document.py`
14. `backend/app/models/chunk.py`
15. `backend/app/models/init_db.py`
16. `backend/app/services/document_parser.py`
17. `backend/app/services/document_storage.py`
18. `backend/app/services/text_splitter.py`
19. `backend/tests/test_text_splitter.py`
20. `backend/tests/test_documents.py`
21. `backend/tests/test_documents_postgres.py`

禁止读取或输出 `.env`，也不得读取无关未跟踪目录 `.agents/` 的内容。

### 3. Git、环境与工作区精确状态

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| Day 5 实现提交 | `a989837bbf8bae1cf866beda034130a514152378` |
| Day 5 提交摘要 | `a989837 feat: complete Day 5 text chunking` |
| 当前交接提交 | 本文档刷新提交，是 `a989837` 的直接后继；完整 HEAD 以 `git rev-parse HEAD` 为准 |
| Day 4 实现 | `623989f feat: complete Day 4 document upload` |
| Day 4 交接 | `a64a0cc docs: refresh Day 4 handoff` |
| Day 3 交接 | `a27a3f5 docs: refresh Day 3 handoff` |
| Day 3 实现 | `177ad2b feat: complete Day 3 DeepSeek chat integration` |
| 远端名称 | `origin` |
| 上游跟踪 | 未配置 |
| 本地远端跟踪引用 | 无 |
| 远端实时状态 | 待确认；本轮未 fetch、未 push |
| Python | `3.11.15` |
| 虚拟环境 | `D:\2019\rag-agent\.venv` |
| PostgreSQL | 可连接；显式建表和真实集成测试通过 |
| 暂存区 | 空 |
| Day 5 | 已提交到本地 `a989837` |
| `PLAN.md` | 经用户明确授权更新 Day 5 复选框和开发日志；Day 6 未修改 |

并发说明：Day 5 开始时 HEAD 为 `623989f`，三份交接文档存在未提交刷新。开发期间，
本轮之外的流程创建了 `a64a0cc`，提交范围为 `HANDOFF.md`、`STATUS.md`、`TODO.md`，
并将 HEAD 移到该提交。之后用户明确授权提交 Day 5 和更新 `PLAN.md`，本地创建了
`a989837`；新会话仍必须以实际 Git 输出为准再次检查。

Day 5 实现提交包含：

- 修改：`.env.example`、`README.md`、`DECISIONS.md`、`PLAN.md`、`docs/architecture.md`、
  `backend/requirements.txt`、`backend/app/api/documents.py`、
  `backend/app/core/config.py`、`backend/app/models/init_db.py`、
  `backend/tests/test_documents.py`、`backend/tests/test_documents_postgres.py`；
- 新增：`backend/app/models/chunk.py`、`backend/app/services/text_splitter.py`、
  `backend/tests/test_text_splitter.py`、`docs/day5-chunk-size-comparison.md`；
- 后续交接提交：`HANDOFF.md`、`STATUS.md`、`TODO.md`；
- 排除：`.agents/` 是无关目录；未读取、未修改、未纳入提交；
- `.env` 未查看、未输出、未修改；真实数据库命令由应用配置层读取现有配置。

### 4. 已完成阶段

#### Day 1：项目边界和架构

- 建立范围、目录、README、目标架构和 GitHub 远端；
- 提交：`751dc40 docs: complete Day 1 project architecture`。

#### Day 2：FastAPI 骨架

- FastAPI 应用、`GET /health`、聊天和上传占位路由；
- 配置、Loguru、请求日志；
- 提交：`607645d feat: complete Day 2 FastAPI foundation`。

#### Day 3：DeepSeek 对话

- OpenAI-compatible `LLMClient`；
- 默认 `deepseek-v4-flash`，默认关闭思考模式；
- `POST /chat` 支持非流式 JSON 和 SSE；
- 缺少配置返回 `503`，普通上游失败返回 `502`，SSE 流错误返回通用 error 事件；
- pytest 与真实 DeepSeek JSON/SSE 验收通过；
- 实现提交：`177ad2b`；交接提交：`a27a3f5`。

#### Day 4：文档上传、解析和 PostgreSQL

- `POST /documents/upload` 支持 multipart PDF/Markdown/TXT；
- 20 MiB 实际字节上限、500 页 PDF 上限、1 MiB 分块存储；
- UUID `.part` 临时文件、安全文件名/MIME/PDF 签名验证；
- PDF 空白页和一基页码保留，以 `\f` 序列化到 `documents.extracted_text`；
- SQLAlchemy 2.x + psycopg 3，同步事务和失败补偿；
- 真实 PDF、磁盘与 PostgreSQL 往返通过；
- 实现提交：`623989f`；Day 4 交接提交：`a64a0cc`。

#### Day 5：分页 token 切分和 Chunk 持久化

- 安装独立 `langchain-text-splitters 1.1.2` 与 `tiktoken 0.13.0`，未安装完整 LangChain；
- 新增 `ChunkingSettings`，默认 `500/100/o200k_base`；
- 新增纯函数 `split_pages()`，逐页切分，禁止跨页；
- 空白页不生成 Chunk，后续页码不压缩；
- 新增 `chunks` 表及 UUID/顺序/JSONB/外键/索引/级联约束；
- 新上传 Document 与全部 Chunk 在同一事务中写入；
- 上传成功响应未增加 `chunk_count` 或其他字段；
- 300/500/800 token 结构实验已实际执行并记录；
- 标准与真实 PostgreSQL 全量测试通过；
- 本地实现提交：`a989837 feat: complete Day 5 text chunking`。

### 5. 当前接口与实现状态

#### 5.1 已注册接口

`backend/app/main.py:create_app()` 注册：

- `GET /health`
- `POST /chat`
- `POST /documents/upload`

Day 5 未修改 `/health` 或 `/chat` 契约，也没有新增查询、删除、回填或重切分 API。

#### 5.2 `POST /documents/upload` 契约

请求：

```text
POST /documents/upload
Content-Type: multipart/form-data
字段：file（UploadFile，必填）
```

成功 `201`，`DocumentUploadResponse` 字段仍严格为：

```json
{
  "id": "UUID",
  "filename": "example.pdf",
  "size": 12345,
  "status": "ready",
  "created_at": "ISO 8601 timestamp"
}
```

不返回 `extracted_text`、`chunk_count` 或 Chunk 正文。

| 场景 | 状态码 |
|---|---|
| 文档、Chunks、文件全部成功 | `201` |
| 空文件、损坏/加密/无文本 PDF、超页数、非 UTF-8、非法文件名 | `400` |
| 实际上传超过限制 | `413` |
| 扩展名、MIME 或 PDF 签名不支持 | `415` |
| 缺少 `file` | `422` |
| PostgreSQL 连接、flush 或 commit 不可用 | `503` |
| 切分、存储或其他未预期错误 | `500` |

所有错误使用通用安全描述，不返回正文、tokenizer 原始错误、数据库密码或原始数据库响应。

#### 5.3 Day 5 切分配置

文件：`backend/app/core/config.py`

```text
ChunkingSettings
chunk_size = 500
chunk_overlap = 100
chunk_encoding_name = "o200k_base"
```

环境变量：`CHUNK_SIZE`、`CHUNK_OVERLAP`、`CHUNK_ENCODING_NAME`。

验证：`chunk_size > 0`、`chunk_overlap >= 0`、`chunk_overlap < chunk_size`、编码名非空。
`get_chunking_settings()` 使用 `lru_cache` 返回配置。

#### 5.4 纯切分服务

文件：`backend/app/services/text_splitter.py`

- `JSONScalar = str | int | float | bool | None`
- `ChunkDraft(chunk_index, content, page, metadata)`
- `TextSplittingError`
- `split_pages(pages, *, chunk_size, chunk_overlap, encoding_name)`

行为：

1. 校验配置；
2. `tiktoken.get_encoding(encoding_name)`；
3. token 计数使用 `encoding.encode(text, disallowed_special=())`；
4. 构造 `RecursiveCharacterTextSplitter`；
5. 每个 `PageText` 独立切分；
6. 空白页跳过，但 `page` 使用原一基页码；
7. `chunk_index` 在整个文档内从 0 连续递增；
8. 每个 Chunk 再次验证 `token_count <= chunk_size`；
9. 没有非空 Chunk 时抛 `TextSplittingError`。

分隔符顺序：

```text
\n\n → \n → 。 → ！ → ？ → . → ! → ? → ； → ; → ， → , → 空格 → 单字符
```

使用 `keep_separator="end"`。

metadata 精确结构：

```json
{
  "chunk_size": 500,
  "chunk_overlap": 100,
  "length_unit": "token",
  "encoding_name": "o200k_base",
  "token_count": 487
}
```

#### 5.5 `chunks` 数据模型

文件：`backend/app/models/chunk.py`，表名：`chunks`。

| 字段 | 类型与约束 |
|---|---|
| `chunk_id` | UUID，主键，默认 `uuid4()` |
| `doc_id` | UUID，非空，外键 `documents.id`，`ON DELETE CASCADE` |
| `chunk_index` | Integer，非空，检查 `>= 0` |
| `content` | Text，非空，切分服务保证非空白 |
| `page` | Integer，非空，检查 `>= 1` |
| `metadata` | PostgreSQL JSONB；SQLite 使用 JSON 变体；非空 |

额外约束：

- `(doc_id, chunk_index)` 唯一：`uq_chunks_doc_id_index`
- `doc_id` 索引：`ix_chunks_doc_id`
- ORM 属性名 `chunk_metadata` 映射到数据库列 `metadata`

不依赖 UUID 排序。Day 5 不更新、不重切分、不回填历史数据。

#### 5.6 上传和事务顺序

```text
uuid4()
→ validate_upload_metadata()
→ build_upload_paths()
→ save_upload_to_part()
→ parse_document() -> list[PageText]
→ split_pages() -> list[ChunkDraft]
→ 构造 Document 与 Chunk ORM 对象
→ session.begin()
→ add(Document) / flush()
→ add_all(Chunks) / flush()
→ promote_upload()（os.replace）
→ commit
→ 原 DocumentUploadResponse
```

必须保留两次 flush。真实 PostgreSQL 已证明单次 flush 在没有 ORM relationship 时可能先插入
Chunk，触发 `chunks_doc_id_fkey`。两次 flush 仍属于同一事务；第二次 flush 失败会回滚第一
次 flush 的 Document。

`_cleanup_failed_upload(session, paths, document_id)` 继续负责数据库回滚和 `.part`/最终文件清理。
提交已实际成功但提交后钩子抛错时保留已提交 Document、Chunks 和最终文件。

#### 5.7 显式数据库初始化

文件：`backend/app/models/init_db.py`

`main()` 导入 `Document` 和 `Chunk` 注册模型，再执行：

```python
Base.metadata.create_all(bind=get_engine())
```

命令：

```powershell
.\.venv\Scripts\python.exe -m backend.app.models.init_db
```

该命令只创建缺失表，不迁移既有表。应用启动和 `/health` 仍不依赖 PostgreSQL。

### 6. Day 5 关键代码和测试位置

| 文件 | 符号 | 作用 |
|---|---|---|
| `backend/app/core/config.py` | `ChunkingSettings` | 默认参数及边界验证 |
| 同上 | `get_chunking_settings()` | 缓存切分配置 |
| `backend/app/services/text_splitter.py` | `ChunkDraft` | 纯切分输出 |
| 同上 | `TextSplittingError` | 安全切分异常 |
| 同上 | `split_pages()` | 按页 token 切分 |
| `backend/app/models/chunk.py` | `Chunk` | `chunks` ORM 模型 |
| `backend/app/models/init_db.py` | `main()` | 显式注册并创建新表 |
| `backend/app/api/documents.py` | `upload_document()` | 上传、切分、两表事务和响应编排 |
| 同上 | `_cleanup_failed_upload()` | 回滚与文件补偿 |
| `backend/tests/test_text_splitter.py` | `representative_text()` | 可复现实验语料 |
| 同上 | 13 个测试 | 配置、页码、token 上限、确定性、特殊文本、模型约束 |
| `backend/tests/test_documents.py` | 17 个测试 | API 成功、响应不变、切分/flush/commit 补偿 |
| `backend/tests/test_documents_postgres.py` | `test_upload_round_trip_with_local_postgres()` | 真实 JSONB、页码、顺序和级联 |
| `docs/day5-chunk-size-comparison.md` | 实验报告 | 300/500/800 结构数据 |

### 7. 已确认技术决策及原因

完整记录以 `DECISIONS.md` 为准。关键决策：

1. `PLAN.md` 控制范围；避免提前引入未来组件。
2. FastAPI 使用模块化结构；路由只编排 HTTP，服务封装业务能力。
3. Day 3 只接 DeepSeek，客户端保持 OpenAI-compatible，默认关闭思考模式。
4. 上游与配置错误不泄露供应商或凭据细节。
5. Day 4 使用 `pypdf` 并以 `\f` 保留每个 PDF 页面边界。
6. 同步 SQLAlchemy 2.x + psycopg 3；数据库显式初始化，不耦合启动和 `/health`。
7. 文件和数据库采用补偿式一致性，不声称真正跨系统原子事务。
8. Day 5 使用 `o200k_base`，因为默认 `len` 是字符计数而不是 token。
9. 按页独立切分，默认 `500/100`；保证 Day 8 引用页码可靠。
10. Chunk 使用 UUID 身份和独立 `chunk_index` 顺序；UUID 不可用于恢复原文顺序。
11. `chunk_metadata` 映射数据库列 `metadata`，避免 SQLAlchemy 保留属性冲突。
12. 同一事务分两次 flush，显式保证外键父行先存在。
13. Day 5 只创建全新 `chunks` 表，继续 `create_all()`；不回填、不引入 Alembic。
14. 结构实验不等于检索质量实验；检索结论留到 Day 9。

### 8. 已否决或未采用方案

- 安装完整 LangChain：否决；只安装 `langchain-text-splitters`。
- 使用默认 `len` 并称为 token 切分：否决；字符数与 token 数不是同一指标。
- 先拼接整篇 `extracted_text` 再切分：否决；会造成 Chunk 跨页和错误引用。
- 让 Chunk UUID 同时表示顺序：否决；UUID 排序不稳定。
- ORM 属性直接命名 `metadata`：否决；与 SQLAlchemy Declarative 保留属性冲突。
- Document 与 Chunks 一次 flush 并假设自动外键排序：已尝试且否决；真实 PostgreSQL 外键失败。
- 给上传响应增加 `chunk_count`：否决；会改变已验收契约。
- 回填 Day 4 历史文档：未采用；超出 Day 5。
- Day 5 引入 Alembic：未采用；只新增表，没有修改既有表。
- 根据结构实验声称 500 token 检索最好：禁止；没有检索评测证据。
- Embedding、Qdrant、BM25、RRF、Rerank、RAG、LangGraph：禁止，均属于未来 Day。

### 9. 不可违反的约束

- 使用 Python 3.11；后端代码位于 `backend/`；公共函数使用类型标注。
- 使用 pytest；完成开发任务前运行全量测试。
- 不读取、输出或提交 `.env`、API Key、数据库真实密码。
- 不在日志中记录上传正文、tokenizer 原始错误、数据库密码或原始数据库响应。
- 未经用户明确授权不得修改 `PLAN.md`。
- 不得重写或删除已验收的 Day 1 至 Day 5 实现。
- 不得将 Day 6+ 能力描述为已完成。
- 不得读取、修改或提交无关 `.agents/`。
- commit 与 push 必须分别获得明确授权。
- 新会话先只读恢复并等待用户指定唯一动作。

### 10. 已尝试但失败的操作、当前错误和日志

#### 当前阻断错误

无。

#### 当前失败测试

无。

#### 持续警告

```text
PytestCacheWarning: could not create cache path ...
[WinError 5] 拒绝访问
```

根因待确认；不影响测试通过。

#### Day 5 已发生并解决/规避的问题

1. 首次安装新依赖时受限网络返回 `[WinError 10013]`；授权联网后安装成功。
2. `tiktoken` 首次加载 `o200k_base` 时需要下载词表，受限网络导致 5 个切分测试失败；
   授权下载并缓存后正常离线运行。
3. 授权环境运行 tokenizer 测试时，pytest 临时目录出现 `[WinError 5]`，结果为
   `10 passed, 1 error`；移除测试中未使用的 `tmp_path` 后普通权限通过。
4. 首次标准全量测试有 1 个测试失败，因为测试 monkeypatch 的 `Session.flush` 在断言查询时仍生效；
   在查询前 `monkeypatch.undo()` 后通过。这是测试隔离问题，不是生产逻辑问题。
5. 首次真实 PostgreSQL 上传返回 `500`，日志只记录 `IntegrityError`。安全诊断得到：

   ```text
   sqlstate=23503
   constraint=chunks_doc_id_fkey
   table=chunks
   ```

   原因是单次 flush 先插入 Chunk。改为同一事务内先 flush Document、再 flush Chunks 后通过。
6. `docker compose ps postgres` 普通权限读取 Docker config/named pipe 时 `Access is denied`；
   授权后 30 秒和 60 秒查询均超时。直接显式建表和真实 PostgreSQL 测试成功，因此不阻断 Day 5。
7. Git 持续提示 LF 未来可能转换为 CRLF；`git diff --check` 退出码为 0。
8. Day 5 开发期间外部并发流程创建 `a64a0cc` 并移动 HEAD；本交接已按实际状态重写。

#### 已知残余风险

- 新环境首次使用 `o200k_base` 可能需要网络下载；预热/离线缓存策略待确认。
- 文件移动后进程立即崩溃仍可能留下孤儿文件。
- `_cleanup_failed_upload()` 读取 SQLAlchemy 私有事务 `_state`；未来升级需验证兼容性。
- `.pytest_cache`、Docker 查询权限和行尾规范仍待确认。

### 11. 已完成验收

最终实际命令：

```powershell
# 显式创建缺失表
.\.venv\Scripts\python.exe -m backend.app.models.init_db

# 标准全量测试；PostgreSQL 测试跳过
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 真实 PostgreSQL 全量测试
$env:RUN_POSTGRES_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 依赖检查
.\.venv\Scripts\python.exe -m pip check

# 编译检查
.\.venv\Scripts\python.exe -m compileall -q backend

# 差异格式检查
git diff --check
```

最新结果（2026-07-15 提交前复跑）：

- 标准：`60 passed, 1 skipped, 1 warning in 5.26s`
- 真实 PostgreSQL：`61 passed, 1 warning in 4.67s`
- `pip check`：`No broken requirements found.`
- compileall：通过
- `git diff --check`：通过；只有 LF→CRLF 提示
- 新表注册和创建：通过
- 上传响应字段不变：通过
- PDF 空白第 2 页、Chunk 页码 `[1, 3]`：通过
- Chunk 顺序 `[0, 1]`：通过
- JSONB metadata：通过
- Document 删除级联删除 Chunks：通过
- 切分、第二次 flush、commit 失败补偿：通过

旧交接中的 `58 passed` / `59 passed` 是新增两个切分兜底测试前的数字；本轮收集到 61 个测试项，
标准环境跳过 PostgreSQL 用例，真实 PostgreSQL 环境全部通过。

### 12. 300/500/800 结构实验

报告：`docs/day5-chunk-size-comparison.md`。

语料：`backend/tests/test_text_splitter.py:representative_text()`，30 个确定性中英文/Markdown 小节，
原文 `1,980` token。

| chunk/overlap | Chunk 数 | 平均 token | 最大 token | token 总和 | 冗余率估算 | 空块 | 超限 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 300/60 | 8 | 247.50 | 264 | 1,980 | 0.00% | 0 | 0 |
| 500/100 | 5 | 448.80 | 462 | 2,244 | 13.33% | 0 | 0 |
| 800/160 | 3 | 748.00 | 792 | 2,244 | 13.33% | 0 | 0 |

只能得出结构差异；哪一种检索质量最好仍为待确认。

### 13. 待完成任务

当前没有获授权的开发任务。

最近的项目操作候选：

1. 只读复核本交接和最新 Git 状态；
2. 用户另行决定是否检查远端、配置上游和推送；
3. 用户另行授权后才可开始 Day 6。

Day 6 Embedding 仍待确认：

- 供应商/模型：OpenAI、阿里云百炼/通义千问、或本地 `BAAI/bge-small-zh-v1.5`；
- Embedding 维度；
- 批量大小和重试细节是否沿用计划默认；
- API 成本、网络和本地资源；
- tokenizer 与 Day 5 `o200k_base` 的关系。

其他待确认：远端实时状态、上游/推送、tokenizer 词表预热、孤儿文件清理、Alembic 时机、
pytest/Docker 权限、`.gitattributes`、Day 18 千问对比。

### 14. 下一步具体操作（最多 5 步）

1. 新会话完整阅读第 2 节资料。
2. 只读运行 `git status --short --branch`、`git log -3 --oneline`、`git branch -vv`；
   不读取 `.env` 或 `.agents/`。
3. 确认历史包含 `a989837 feat: complete Day 5 text chunking`，并核对工作区是否为空。
4. 若状态不符，先报告差异并暂停，不改代码、不提交、不推送。
5. 等用户指定唯一动作：处理远端、授权 Day 6、执行其他操作或继续暂停。

### 15. 下一阶段验收标准

#### 当前交接恢复验收

- 识别 Day 1 至 Day 5 已完成；Day 5 本地实现提交为 `a989837`。
- 识别 `a64a0cc` 是并发流程创建的 Day 4 交接提交，也是 Day 5 实现提交的基线。
- 明确 `.agents/` 未读取、未修改、未提交。
- 明确 `PLAN.md` 的 Day 5 状态已更新、Day 6 未开始。
- 准确复述标准/真实 PostgreSQL 测试结果和唯一持续警告。
- 不读取 `.env`，不改代码、不提交、不推送，除非用户另行授权。

#### 若未来授权 Day 6

- 先确认 Embedding 供应商、模型和维度；
- 严格只完成 `PLAN.md` Day 6，不进入 Day 7；
- 不破坏 Day 5 页码、顺序、metadata 和上传事务契约；
- `PLAN.md`、提交、推送仍分别需要授权。

### 16. 常用命令

所有命令从 `D:\2019\rag-agent` 执行：

```powershell
# 安装依赖
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# 显式建表
.\.venv\Scripts\python.exe -m backend.app.models.init_db

# 启动后端
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

# 标准测试
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 真实 PostgreSQL 测试
$env:RUN_POSTGRES_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 依赖检查
.\.venv\Scripts\python.exe -m pip check
```

## B. 300 字以内快速恢复摘要

仓库 `D:\2019\rag-agent`，`master`；Day 5 本地实现提交 `a989837`。Day 1-5 已完成，支持按页 `o200k_base` token 切分、默认 500/100、有序 UUID Chunks、JSONB、级联删除及 Document/Chunks 同事务持久化，上传响应不变。标准测试 60 passed/1 skipped，真实 PostgreSQL 61 passed，均有 1 个既存缓存权限警告。`PLAN.md` 已更新 Day 5，Day 6 未开始，尚未推送。先只读复核并等待指令。

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
10. backend/app/api/documents.py
11. backend/app/core/config.py
12. backend/app/models/chunk.py
13. backend/app/models/init_db.py
14. backend/app/services/text_splitter.py
15. backend/tests/test_text_splitter.py
16. backend/tests/test_documents.py
17. backend/tests/test_documents_postgres.py

执行规则：
- 先只读检查，不要立即改代码。
- 不要重新完成已完成的 Day 1-5。
- 不要擅自推翻 DECISIONS.md 中的技术决策。
- 不确定内容标记为“待确认”，禁止自行补全。
- 不要读取、输出或提交 .env/API Key/数据库真实密码。
- 不要读取或提交无关 .agents/。
- 不要修改 PLAN.md，除非我明确授权。
- 不要提交或推送，除非我分别明确授权。
- 不要开始 Day 6 或更晚任务。

请先回复：
1. 项目最终目标和当前实现状态；
2. 已提交、未提交和远端待确认内容；
3. Day 5 已确认技术决策及原因；
4. 缺失、矛盾、当前错误或风险；
5. 接下来最多 5 个步骤。

预期基线：master；历史包含 Day 5 实现提交
a989837bbf8bae1cf866beda034130a514152378，当前 HEAD 是其交接刷新后继。
Day 1-5 已完成并本地提交。标准测试 60 passed、1 skipped、1 warning；
真实 PostgreSQL 61 passed、1 warning。PLAN.md 已更新 Day 5，Day 6 未开始，尚未推送。

当前唯一目标：只读确认交接包、最新 HEAD、干净工作区和远端待确认状态，准确复述后等待我指定下一动作。

本轮验收标准：不改代码、不读取 .env/.agents、不提交、不推送；准确识别 Day 5 提交、
PLAN.md 状态、测试证据、远端待确认项和所有残余风险。
```
