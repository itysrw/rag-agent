# 项目完整交接包

更新时间：2026-07-15（America/New_York）
仓库：`D:\2019\rag-agent`

当前阶段：Day 1 至 Day 4 已完成并验收，本地提交已准备。推送因规则模式下无法连接
GitHub 而暂未完成；不得自行开始 Day 5。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供后端 API；
- 支持 PDF、Markdown、TXT 的上传、解析、切分和元数据存储；
- 使用 Embedding、Qdrant、BM25、RRF、Rerank 实现检索增强；
- 使用 OpenAI-compatible LLM 生成带来源引用的回答；
- 使用 LangGraph 实现检索决策、工具调用和多轮记忆；
- PostgreSQL 保存业务数据，并以评测数据集量化质量和延迟；
- Streamlit 提供演示界面，最终由 Docker Compose 一键启动；
- 最终形成 README、架构图、评测报告、简历描述和面试材料。

`PLAN.md` 是 25 天范围与顺序的唯一计划基线。计划中的未来能力不能写成已完成事实。

### 2. 新会话必须阅读的资料

按顺序完整阅读：

1. `HANDOFF.md`
2. `STATUS.md`
3. `DECISIONS.md`
4. `TODO.md`
5. `AGENTS.md`
6. `README.md`
7. `PLAN.md`（只读，除非用户另行授权修改）
8. `docs/architecture.md`
9. 与获授权任务直接相关的代码和测试

禁止读取或输出 `.env`，也不要读取无关未跟踪目录 `.agents/` 的内容。

### 3. Git、环境与工作区精确状态

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| Day 4 实现提交 | `623989f2d6934c98500c555bfac0b5ba6f94736d` |
| Day 4 提交摘要 | `623989f feat: complete Day 4 document upload` |
| 前一提交 | `a27a3f5 docs: refresh Day 3 handoff` |
| Day 3 实现提交 | `177ad2b feat: complete Day 3 DeepSeek chat integration` |
| 远端 | `origin https://github.com/itysrw/rag-agent.git` |
| 上游跟踪 | 未配置 |
| 推送状态 | 两次 push 分别因连接重置和 GitHub 443 不可达而失败，远端尚未发布 |
| 首次发布前远端状态 | `git ls-remote --heads origin` 无输出，远端没有已有分支 |
| Python | `3.11.15` |
| 虚拟环境 | `D:\2019\rag-agent\.venv` |
| PostgreSQL | Docker `postgres:16-alpine`；2026-07-15 本次交接核验为 `Up (healthy)` |
| `.env` | 本地存在且被 Git 忽略；未读取、未输出、未提交 |
| `PLAN.md` | Day 4 六项已按用户授权勾选完成；Day 5 未开始 |

发布本交接包时，工作区仍有另一个编辑流程产生的未提交修改，包含配置、依赖和 Day 5
相关文件，以及无关未跟踪目录 `.agents/`。实时清单以 `git status` 为准；这些内容均未纳入
本次发布。不得擅自读取可能含密钥的 `.env.example`，也不得擅自提交、覆盖或删除这些改动。

新会话必须先用以下只读命令复核，实际输出优先于本段文字：

```powershell
git status --short --branch
git log -3 --oneline
git branch -vv
```

### 4. 已完成并提交的阶段

#### Day 1：项目边界和架构

- 建立项目范围、目录、README、Mermaid 目标架构和 GitHub 远端；
- 提交：`751dc40 docs: complete Day 1 project architecture`。

#### Day 2：FastAPI 骨架

- FastAPI 应用、`GET /health`、聊天和上传占位路由；
- 配置、Loguru、请求日志；
- `/health` 真实 HTTP 验收通过；
- 提交：`607645d feat: complete Day 2 FastAPI foundation`。

#### Day 3：DeepSeek 对话

- OpenAI-compatible `LLMClient`；
- 默认模型 `deepseek-v4-flash`，默认关闭思考模式；
- `POST /chat` 支持非流式 JSON 和 SSE；
- 缺少配置返回 `503`，普通上游错误返回 `502`，SSE 流中错误返回通用 error 事件；
- 真实 DeepSeek 非流式/SSE 验收通过；
- 当时 pytest：`12 passed, 1 warning`；
- 实现提交：`177ad2b feat: complete Day 3 DeepSeek chat integration`；
- 交接提交：`a27a3f5 docs: refresh Day 3 handoff`。

#### Day 4：文档上传、解析和 PostgreSQL 持久化

- `POST /documents/upload` 已从占位接口改为 multipart 文件上传；
- PDF/Markdown/TXT 安全存储和解析；
- PDF 页边界保留，空白页不丢失；
- PostgreSQL `documents` 表和同步事务；
- 失败回滚及文件补偿清理；
- 真实 PDF、磁盘和 PostgreSQL 往返验收通过；
- 全量 pytest：`44 passed, 1 warning`；
- 提交：`623989f feat: complete Day 4 document upload`。

### 5. 当前实现状态

#### 5.1 已注册接口

`backend/app/main.py:create_app()` 依次注册：

- `health_router`：`GET /health`；
- `chat_router`：`POST /chat`；
- `documents_router`：`POST /documents/upload`。

Day 4 没有修改 `/health` 或 `/chat` 的契约。

#### 5.2 `POST /documents/upload` 精确契约

请求：

```text
POST /documents/upload
Content-Type: multipart/form-data
字段：file（UploadFile，必填）
```

成功响应 `201`，模型为 `backend/app/api/documents.py:DocumentUploadResponse`：

```json
{
  "id": "UUID",
  "filename": "example.pdf",
  "size": 12345,
  "status": "ready",
  "created_at": "ISO 8601 timestamp"
}
```

不返回 `extracted_text`。

| 场景 | 状态码 |
|---|---|
| 保存、解析、移动和数据库提交成功 | `201` |
| 空文件、损坏/加密/无文本 PDF、PDF 超页数、非 UTF-8 文本、非法文件名 | `400` |
| 实际上传超过 20 MiB | `413` |
| 不支持的扩展名、MIME 或 PDF 内容签名 | `415` |
| 缺少 `file` 字段 | `422` |
| PostgreSQL 配置缺失、连接失败或超时 | `503` |
| 未预期存储或数据库错误 | `500` |

所有客户端错误都是通用安全描述，不返回数据库密码、解析库原始异常或上传正文。

#### 5.3 上传和存储

- 允许扩展名：`.pdf`、`.md`、`.txt`；
- `backend/app/services/document_storage.py:ALLOWED_CONTENT_TYPES` 定义扩展名与 MIME 白名单；
- 原始文件名最多 255 字符，拒绝控制字符、`.`、`..`、POSIX/Windows 路径；
- 服务端以 UUID 生成存储名，扩展名统一小写；
- 临时文件：`data/uploads/{UUID}.part`；
- 最终文件：`data/uploads/{UUID}.pdf|.md|.txt`；
- 使用 `UploadFile.file.read(settings.read_chunk_size)` 同步分块读取；
- 真实字节上限 `20 * 1024 * 1024`，不依赖 `Content-Length`；
- PDF 前 1024 字节必须包含 `%PDF-`；
- `data/` 已被 Git 忽略。

#### 5.4 文本解析和页边界

- `backend/app/services/document_parser.py:PageText(page: int, text: str)` 使用一基页码；
- PDF 由 `pypdf.PdfReader(strict=False)` 逐页 `extract_text()`；
- 空白页保存为对应 `PageText`，只有所有页均为空白才失败；
- PDF 最大 500 页；加密、损坏、扫描版整体无文本 PDF 返回 `400`；OCR 不在当前范围；
- Markdown/TXT 使用严格 UTF-8，`utf-8-sig` 支持 BOM，并视为第 1 页；
- `PAGE_SEPARATOR = "\f"`；页内已有 `\f` 会转换成换行；
- `serialize_pages()` 以 `\f` 写入 `documents.extracted_text`。

#### 5.5 PostgreSQL 模型

模型：`backend/app/models/document.py:Document`，表名 `documents`。

| 字段 | SQLAlchemy 类型/约束 |
|---|---|
| `id` | `Uuid(as_uuid=True)`，主键 |
| `filename` | `String(255)`，非空 |
| `size` | `BigInteger`，非空 |
| `status` | `String(32)`，非空；当前成功值仅 `ready` |
| `created_at` | `DateTime(timezone=True)`，非空，默认 UTC |
| `extracted_text` | `Text`，非空，以 `\f` 保留页边界 |

没有 `storage_path`、`content_type`、`error_message` 字段；失败记录不入库。

数据库不会在 FastAPI lifespan 或 `/health` 中初始化。显式建表入口：

```powershell
.\.venv\Scripts\python.exe -m backend.app.models.init_db
```

#### 5.6 文件和事务顺序

```text
uuid4()
→ validate_upload_metadata()
→ build_upload_paths()
→ save_upload_to_part()
→ parse_document()
→ serialize_pages()
→ session.begin() / add() / flush()
→ promote_upload()（os.replace）
→ commit
```

异常时 `backend/app/api/documents.py:_cleanup_failed_upload()` 回滚数据库并调用
`cleanup_upload_files()` 删除 `.part` 和最终文件。若事务已经实际提交但提交后的钩子抛错，
清理逻辑保留已提交文档的最终文件。进程恰好在文件移动后崩溃仍可能留下孤儿文件，
这是已确认残余风险。

### 6. Day 4 关键代码位置、类和函数

| 文件 | 关键符号 | 作用 |
|---|---|---|
| `backend/app/api/documents.py` | `DocumentUploadResponse` | `201` 响应模型 |
| 同上 | `require_database_session()` | 延迟取得同步 Session；配置错误映射 `503` |
| 同上 | `upload_document(file, session, settings)` | 上传、解析、事务和 HTTP 错误总编排 |
| 同上 | `_cleanup_failed_upload(session, paths, document_id)` | 回滚与文件补偿清理 |
| `backend/app/core/config.py` | `MAX_UPLOAD_SIZE` | `20 * 1024 * 1024` |
| 同上 | `MAX_PDF_PAGES` | `500` |
| 同上 | `READ_CHUNK_SIZE` | `1024 * 1024` |
| 同上 | `DatabaseSettings` / `get_database_settings()` | `POSTGRES_` 配置 |
| 同上 | `DocumentSettings` / `get_document_settings()` | 上传目录与限制配置 |
| `backend/app/core/database.py` | `build_database_url()` | 构造 `postgresql+psycopg` URL，拒绝占位密码 |
| 同上 | `get_engine()` | 延迟缓存 Engine，`pool_pre_ping=True` |
| 同上 | `get_session_factory()` | 同步 Session，`expire_on_commit=False` |
| `backend/app/models/document.py` | `Document` / `utc_now()` | `documents` ORM 模型和 UTC 时间 |
| `backend/app/models/init_db.py` | `main()` | 显式 `Base.metadata.create_all()` |
| `backend/app/services/document_storage.py` | `validate_upload_metadata()` | 文件名、扩展名、MIME 检查 |
| 同上 | `build_upload_paths()` | UUID 路径唯一推导点 |
| 同上 | `save_upload_to_part()` | `xb` 分块保存、实际大小和内容检查 |
| 同上 | `promote_upload()` / `cleanup_upload_files()` | 原子移动和补偿清理 |
| `backend/app/services/document_parser.py` | `PageText` / `parse_document()` | PDF/UTF-8 分页解析 |
| 同上 | `serialize_pages()` | 用 `\f` 序列化页面 |

测试位置：

- `backend/tests/test_documents.py`：接口、HTTP 契约、事务失败和提交后异常；
- `backend/tests/test_document_parser.py`：PDF 页边界、加密/损坏/无文本和 UTF-8；
- `backend/tests/test_document_storage.py`：路径穿越、类型、分块、大小和清理；
- `backend/tests/test_documents_postgres.py:test_upload_round_trip_with_local_postgres()`：真实 PostgreSQL/PDF 往返；
- `backend/tests/pdf_fixtures.py`：测试 PDF 生成辅助函数。

### 7. 已确认技术决策及原因

完整记录以 `DECISIONS.md` 为准，尤其是 D-015 至 D-018：

1. **使用 `pypdf` 而非旧 `PyPDF2` 名称或 `pdfminer.six`**：`pypdf` 是合并后的维护项目；当前只需文本层提取。
2. **保留每一页并用 `\f` 序列化**：Day 5 的 chunk `page` 和 Day 8 的引用需要可靠页码。
3. **同步 SQLAlchemy 2.x + psycopg 3，同步上传路由**：FastAPI 会在线程池运行普通 `def`，适合同步文件、pypdf 和数据库 I/O。
4. **数据库显式初始化**：PostgreSQL 暂时不可用时 FastAPI 和 `/health` 仍应启动并保持原语义。
5. **UUID 主键、`ready` 状态、`extracted_text TEXT`**：满足 Day 4 最小持久化并为分页切分保留文本。
6. **不保存路径和失败记录**：路径集中推导，失败通过事务回滚和文件清理解决，避免擅自扩表。
7. **20 MiB、500 页、1 MiB 块**：同时限制上传字节、PDF 页数和单次内存读取。
8. **`.part → flush → os.replace → commit`**：文件系统与 PostgreSQL不能形成真正原子事务，此顺序配合补偿清理缩小半完成窗口。

### 8. 已否决或未采用的方案

- Day 3 同时接入 DeepSeek、OpenAI 和千问：否决，范围和计费复杂度过大；
- 继续默认使用 `deepseek-chat`：否决，改为 `deepseek-v4-flash`；
- 在 `LLMClient` 中按供应商写分支：否决，保持 OpenAI-compatible；
- Day 4 一次性将整个上传读入内存：否决，大文件会放大内存风险；
- 只检查 `Content-Length`：否决，必须统计实际读取字节；
- 直接用客户端文件名落盘：否决，存在路径穿越和重名覆盖；
- 只信任扩展名或 MIME：否决，PDF 还校验内容签名并实际解析；
- 只保存拼接文本、不保留页边界：否决，会破坏 Day 5 页码和 Day 8 引用；
- 将数据库建表放到应用启动或 `/health`：否决，会改变已验收健康检查语义；
- 在 Day 4 立即引入 Alembic：未采用；首次真正修改已有表结构前再引入；
- 保存 `storage_path`、`content_type`、`error_message` 或失败行：未采用，超出 Day 4 最小范围；
- 在 Day 4 加 OCR、切分、Embedding、Qdrant：禁止，均超出 Day 4。

### 9. 不可违反的约束

- 使用 Python 3.11；
- 后端代码位于 `backend/`；
- 公共函数使用类型标注；
- 使用 pytest，完成开发任务前运行全量测试；
- 不读取、输出或提交 `.env`、API Key、数据库真实密码；
- 不在日志中记录上传正文、数据库密码或原始数据库错误响应；
- 未经用户明确授权不得修改 `PLAN.md`；
- 不得重写或删除已验收的 Day 1 至 Day 4 实现；
- 不得将计划中的 Day 5+ 能力描述为已完成；
- 不得自行推送；`master` 当前无上游跟踪；
- 不得读取、修改或提交无关 `.agents/`；
- 新会话初次只读复核后必须等待用户指定唯一下一动作。

### 10. 当前错误、日志和已尝试但失败的操作

#### 当前阻断错误

无。

#### 当前失败测试

无。最近一次全量 PostgreSQL 集成测试结果：

```text
44 passed, 1 warning in 3.22s
```

本次发布前常规测试未启用 PostgreSQL 集成开关，结果为 `43 passed, 1 skipped, 1 warning in 3.29s`；
被跳过的是本地 PostgreSQL 往返测试，已由上述完整验收覆盖。

唯一持续警告：pytest 无法写入 `.pytest_cache`，日志包含：

```text
PytestCacheWarning: cache could not write path ...
[WinError 5] 拒绝访问
```

根因：待确认。该警告不影响测试结果。

#### 已发生且已解决/规避的问题

1. 受限网络首次安装新依赖失败；获准联网后安装成功，`pip check` 通过。
2. 首轮新增测试使用当前 Starlette 不存在的 413 常量名；已改用兼容常量，测试通过。
3. PostgreSQL 镜像首次拉取两次超时；后台下载最终完成，`postgres:16-alpine` 已启动。
4. Docker 在受限权限下读取 `C:\Users\袁伟鑫\.docker\config.json` 和 named pipe 时出现 `Access is denied`；只读提升权限后 `docker compose ps postgres` 成功，容器为 `healthy`。
5. 本次生成交接包时 `rg.exe` 被系统拒绝执行；改用 PowerShell `Select-String` 完成只读核对。根因待确认，不影响项目。
6. LF/CRLF 提示仍可能出现；`git diff --check` 已通过。是否添加 `.gitattributes`：待确认。

### 11. 已完成验收

- 依赖版本：`pypdf 6.14.2`、`python-multipart 0.0.32`、`SQLAlchemy 2.0.51`、`psycopg 3.3.4`；
- `pip check`：`No broken requirements found.`；
- compileall：通过；
- Docker Compose 配置：通过；
- `git diff --check`：通过；
- 密钥扫描：0 个匹配；
- PostgreSQL：`postgres:16-alpine`，本次复核 `healthy`；
- 显式 `python -m backend.app.models.init_db`：通过；
- 真实三页 PDF（中间空白页）上传返回 `201`；
- 磁盘文件和数据库记录一致；`extracted_text` 含两个 `\f`；
- 测试文件和记录清理成功，验收后 `documents` 行数为 `0`；
- Day 2 `/health` 和 Day 3 `/chat` 回归通过；
- 全量 pytest：`44 passed, 1 warning`。

### 12. 待完成任务

当前没有获授权的开发任务。用户选择之前保持暂停。

`PLAN.md` 的下一个计划阶段是 Day 5“文本切分”，但尚未开始：

- 安装 `langchain-text-splitters`，不安装完整 LangChain；
- 实现 `RecursiveCharacterTextSplitter`；
- Chunk 字段：`doc_id`、`chunk_id`、`content`、`page`、`metadata`；
- 测试 300 / 500 / 800 token 三种 chunk size并记录差异；
- 建立 `chunks` 表并把切分结果写入 PostgreSQL；
- 产出：一个文档能被切成多个 chunks 并入库。

Day 5 开工前仍需确认，禁止自行补全：

- “token”使用哪种 tokenizer/`length_function`；
- `chunk_overlap` 数值；
- `chunk_id` 类型、主键和排序语义；
- `metadata` 的 JSON 结构及数据库类型；
- `chunks.doc_id` 外键、删除策略和索引；
- 新表继续由 `create_all()` 创建，还是在 Day 5 引入迁移工具；
- 300/500/800 的对比语料、指标和记录位置。

其他延后事项：孤儿文件清理任务、Alembic 时机、`.pytest_cache` 权限、`.gitattributes`、
Day 6 Embedding 供应商和 Day 18 千问对比，均为待确认。

### 13. 下一步具体操作（最多 5 步）

1. 新会话完整阅读第 2 节列出的资料以及 Day 4 关键代码和测试。
2. 只读运行 `git status --short --branch`、`git log -3 --oneline`、`git branch -vv`；不读取 `.env` 或 `.agents/`。
3. 向用户复述项目目标、Day 1-4 完成状态、待推送状态、当前 HEAD、工作区差异及所有“待确认”项。
4. 如果实际状态与本交接包不符，先报告差异，不改代码、不提交、不推送。
5. 等用户明确选择：网络恢复后重试推送、授权 Day 5、处理其他待确认项，或继续暂停；只能执行被选中的一项。

### 14. 下一阶段验收标准

#### 当前交接恢复验收

- 精确识别 `master`、当前 HEAD 和 Day 4 实现提交 `623989f2d6934c98500c555bfac0b5ba6f94736d`；
- 确认 Day 1-4 已提交但推送受网络阻断，并区分项目提交和无关 `.agents/`；
- 明确当前尚未发布、未开始 Day 5；
- 不读取 `.env`，不改代码、不提交、不推送；
- 列出矛盾、缺失和待确认项后等待用户指令。

#### 若未来获授权执行 Day 5

- 严格完成 `PLAN.md` Day 5 的五项任务，不进入 Day 6；
- 保留 Day 4 的 PDF `\f` 页边界并为每个 chunk 写入正确 `page`；
- 300 / 500 / 800 的比较可复现并有记录；
- chunks 成功写入 PostgreSQL；
- `/health`、`/chat`、`/documents/upload` 契约不回归；
- 单元测试和真实 PostgreSQL 集成测试通过；
- 更新交接文档；修改 `PLAN.md`、提交和推送仍分别需要用户授权。

### 15. 常用命令

所有命令从 `D:\2019\rag-agent` 执行：

```powershell
# 安装依赖
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt

# 启动 PostgreSQL
docker compose up -d postgres

# 查看 PostgreSQL 状态
docker compose ps postgres

# 显式建表
.\.venv\Scripts\python.exe -m backend.app.models.init_db

# 启动后端
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

# 普通测试；PostgreSQL 集成测试默认跳过
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 启用本地 PostgreSQL 集成测试
$env:RUN_POSTGRES_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 依赖检查
.\.venv\Scripts\python.exe -m pip check
```

## B. 300 字以内快速恢复摘要

仓库 `D:\2019\rag-agent`，分支 `master`，尚未配置上游。Day 1-4 已完成并提交；Day 4 已实现 multipart PDF/MD/TXT 上传、20 MiB/500 页限制、UUID 分块存储、PDF `\f` 分页和 PostgreSQL 持久化。真实 PDF/PostgreSQL 验收为 `44 passed, 1 warning`；本次常规测试为 `43 passed, 1 skipped, 1 warning`。推送因规则模式下 GitHub 443 不可达而失败。工作区另有其他编辑流程产生且未纳入提交的本地修改，实时清单以 `git status` 为准，不得擅自覆盖。Day 5 未授权，先只读复核并等待指令。

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
9. backend/app/api/documents.py
10. backend/app/core/config.py
11. backend/app/core/database.py
12. backend/app/models/document.py
13. backend/app/models/init_db.py
14. backend/app/services/document_parser.py
15. backend/app/services/document_storage.py
16. backend/tests/test_documents.py
17. backend/tests/test_document_parser.py
18. backend/tests/test_document_storage.py
19. backend/tests/test_documents_postgres.py

执行规则：
- 先只读检查，不要立即改代码。
- 不要重新完成已经完成的 Day 1-4。
- 不要擅自推翻 DECISIONS.md 中的技术决策。
- 不要假设未提供的信息；不确定内容标记为“待确认”。
- 不要读取、输出或提交 .env/API Key/数据库真实密码。
- 不要读取或提交无关的 .agents/。
- 不要修改 PLAN.md，除非我明确授权。
- 不要提交或推送，除非我分别明确授权。
- 不要开始 Day 5 或更晚任务。

请先回复：
1. 你理解的项目最终目标和当前实现状态；
2. 已提交、待推送内容，以及当前工作区差异；
3. 已确认技术决策及其原因；
4. 发现的缺失、矛盾、当前错误或风险；
5. 接下来最多 5 个步骤。

预期基线：分支 master 尚未配置上游；Day 4 实现提交为
623989f2d6934c98500c555bfac0b5ba6f94736d；Day 1-4 和交接刷新均已本地提交但尚未发布。
Day 4 真实 PDF/PostgreSQL 验收已通过；pytest 44 passed、1 warning；发布前常规测试为
43 passed、1 skipped、1 warning。工作区另有其他编辑流程产生且未纳入本次发布的本地修改，
实时清单以 git status 为准；不得擅自读取敏感值、覆盖或纳入项目提交。

当前唯一目标：只读确认交接包和 Git 状态，准确复述后等待我指定下一动作。

本轮验收标准：准确识别 Day 1-4 已完成但推送受网络阻断、Day 5 未开始；列出所有待确认项；
不改代码、不读取 .env、不提交、不推送。

复述完成后等待我确认，再从 HANDOFF.md 的“下一步具体操作”开始。
```
