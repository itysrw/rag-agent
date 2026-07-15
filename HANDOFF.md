# 项目完整交接包

更新时间：2026-07-15（America/New_York）
仓库：`D:\2019\rag-agent`

当前阶段：Day 4 实现、真实 PDF/PostgreSQL 验收和全量回归已完成；用户已授权同步
`PLAN.md` 并创建本地 Day 4 检查点。检查点尚未推送，禁止未经新授权开始 Day 5。

## A. 详细交接文档

### 1. 项目最终目标

构建一个可写入简历、可在面试中完整讲解的企业知识库 RAG Agent：

- FastAPI 提供后端 API；
- PDF、Markdown、TXT 文档上传、解析、切分和元数据存储；
- Embedding、Qdrant、BM25、RRF、Rerank 检索增强；
- OpenAI-compatible LLM 生成带来源引用的回答；
- LangGraph 实现检索决策、工具调用和多轮记忆；
- PostgreSQL 保存业务数据，评测数据集量化质量和延迟；
- Streamlit 展示，最终由 Docker Compose 一键启动；
- 形成 README、架构图、评测报告、简历描述和面试材料。

`PLAN.md` 是 25 天范围和顺序的唯一计划基线。不得把未完成计划写成事实，也不得未经用户授权修改。

### 2. Git 与环境精确状态

| 项目 | 当前值 |
|---|---|
| 分支 | `master` |
| HEAD | 当前 Day 4 本地检查点；精确哈希使用 `git log -1 --oneline` 查询 |
| Day 3 实现提交 | `177ad2b feat: complete Day 3 DeepSeek chat integration` |
| 远端 | `origin https://github.com/itysrw/rag-agent.git` |
| 上游 | 未配置 |
| 推送状态 | 本地提交尚未推送 |
| Python | `3.11.15` |
| 虚拟环境 | `D:\2019\rag-agent\.venv` |
| PostgreSQL | Docker `postgres:16-alpine`，当前容器健康 |
| `.env` | 存在、被忽略、未跟踪；不得读取、输出或提交真实凭据 |
| `PLAN.md` | 已按用户授权将 Day 4 勾选完成并更新开发日志 |
| 工作区 | Day 4 文件应无剩余差异；无关未跟踪 `.agents/` 保留且不纳入提交 |

提交 `a27a3f5` 只包含此前三份 Day 3 交接刷新：`HANDOFF.md`、`STATUS.md`、`TODO.md`。
该提交按用户授权创建，未推送。Day 4 从这个干净检查点开始。

### 3. 已提交并完成的阶段

#### Day 1

- 项目边界、目录、README、Mermaid 目标架构和 GitHub 远端；
- 关键提交：`751dc40 docs: complete Day 1 project architecture`。

#### Day 2

- FastAPI 应用、`GET /health`、聊天与上传占位路由；
- 应用配置、Loguru、请求日志；
- `/health` 真实 HTTP 验收通过；
- 提交：`607645d feat: complete Day 2 FastAPI foundation`。

#### Day 3

- OpenAI-compatible `LLMClient`；
- `deepseek-v4-flash`，默认关闭思考模式；
- `/chat` 非流式 JSON 和 SSE；
- 缺少配置 `503`、普通上游错误 `502`、SSE 流中错误事件；
- 真实 DeepSeek 非流式/SSE 验收通过；
- 当时 pytest `12 passed, 1 warning`；
- 提交：`177ad2b feat: complete Day 3 DeepSeek chat integration`。

Day 3 后续交接刷新提交：`a27a3f5 docs: refresh Day 3 handoff`。

### 4. Day 4 已确认决策

完整决策见 `DECISIONS.md` 的 D-015 至 D-018。

1. PDF 使用当前维护的 `pypdf`；OCR 不属于 Day 4。
2. 解析层返回一基页码 `PageText`；PDF 空白页也保留。
3. 存库使用标准分页符 `\f` 拼接；Day 5 可按 `\f` 恢复页面后在页内切分。
4. Markdown/TXT 严格 UTF-8，支持 BOM，视为第 1 页。
5. SQLAlchemy 2.x + psycopg 3 + 同步 Session；上传路由使用普通 `def`。
6. PostgreSQL UUID 主键；成功状态为 `ready`；增加 `extracted_text TEXT`。
7. 不增加 `storage_path`、`content_type`、`error_message`；路径由 UUID 和扩展名统一推导。
8. 实际上传上限 20 MiB、PDF 最多 500 页、读取块 1 MiB。
9. 不在应用启动或 `/health` 初始化数据库；使用显式建表命令。
10. 失败不保存数据库记录，回滚并清理临时/最终文件。

### 5. Day 4 已实现内容

#### 5.1 上传和存储

- `POST /documents/upload` 已从 `501` 占位改为 multipart 接口；
- 必填字段：`file: UploadFile`；
- 同步读取 `UploadFile.file.read(1 MiB)`，按真实字节计数；
- 允许扩展名：`.pdf`、`.md`、`.txt`；
- 同时校验安全文件名、扩展名、MIME 和可解析内容；
- POSIX/Windows 路径穿越均被拒绝；
- 服务器生成 UUID 存储名，扩展名统一小写；
- 临时文件：`data/uploads/{UUID}.part`；
- 最终文件：`data/uploads/{UUID}.{ext}`；
- `data/` 已被 Git 忽略。

#### 5.2 解析

- PDF 逐页调用 `extract_text()`；
- 空白页保留为对应 `PageText(page=N, text="")`；
- 只有全部页面均为空白才返回 `400`；
- 扫描版无文本 PDF、加密 PDF、损坏 PDF 返回安全 `400`；
- PDF 超过 500 页返回 `400`；
- TXT/Markdown 使用 UTF-8/UTF-8 BOM；非法编码返回 `400`；
- 页面文本内部的 `\f` 会规范化，数据库中的 `\f` 专用于页边界。

#### 5.3 PostgreSQL

`documents` 表：

| 字段 | 类型/含义 |
|---|---|
| `id` | UUID 主键 |
| `filename` | 原始安全文件名 |
| `size` | 实际上传字节数 |
| `status` | 当前成功值 `ready` |
| `created_at` | 带时区时间 |
| `extracted_text` | 以 `\f` 保留页边界的提取文本 |

数据库不会在 FastAPI lifespan 或 `/health` 中连接或建表。显式命令：

```powershell
.\.venv\Scripts\python.exe -m backend.app.models.init_db
```

#### 5.4 文件与事务顺序

```text
生成 UUID
→ 分块写入 UUID.part
→ 校验实际大小和类型
→ 解析并序列化页文本
→ 开启事务、add、flush
→ os.replace(UUID.part, UUID.ext)
→ commit
```

任意异常都会执行 rollback，并尽力删除 `.part` 和已移动的最终文件。测试覆盖 flush 失败和
`os.replace` 后 commit 失败。进程恰好在移动后崩溃仍可能留下孤儿文件，这是已确认残余风险；
启动清理任务不属于 Day 4。

### 6. HTTP 契约

成功响应：

```json
{
  "id": "UUID",
  "filename": "example.pdf",
  "size": 12345,
  "status": "ready",
  "created_at": "ISO 8601"
}
```

不返回完整 `extracted_text`。

| 场景 | 状态码 |
|---|---|
| 上传、解析、文件移动和数据库提交成功 | `201` |
| 空文件、损坏/加密/无文本 PDF、非 UTF-8 文本 | `400` |
| 实际上传超过 20 MiB | `413` |
| 不支持的扩展名、MIME 或内容 | `415` |
| 缺少 `file` | `422` |
| PostgreSQL 配置缺失或不可用 | `503` |
| 未预期存储或数据库错误 | `500` |

所有错误响应均为通用安全描述，不返回数据库或解析库原始异常。

`GET /health` 和 `/chat` 行为未修改。

### 7. 关键文件

| 文件 | 作用 |
|---|---|
| `backend/app/api/documents.py` | multipart、事务编排和 HTTP 错误映射 |
| `backend/app/core/config.py` | 应用、LLM、PostgreSQL、上传限制配置 |
| `backend/app/core/database.py` | 延迟创建 Engine 和同步 Session |
| `backend/app/models/document.py` | `documents` SQLAlchemy 模型 |
| `backend/app/models/init_db.py` | 显式建表入口 |
| `backend/app/services/document_storage.py` | 文件名校验、分块保存、路径推导和清理 |
| `backend/app/services/document_parser.py` | PDF 分页和 UTF-8 文本提取 |
| `docker-compose.yml` | Day 4 PostgreSQL 服务 |
| `backend/tests/test_documents.py` | 接口、错误契约和补偿测试 |
| `backend/tests/test_document_parser.py` | PDF 页边界与文本编码测试 |
| `backend/tests/test_document_storage.py` | 路径、类型、分块和大小测试 |
| `backend/tests/test_documents_postgres.py` | 真实 PostgreSQL/PDF 集成测试 |

### 8. 验收结果

#### 8.1 依赖与静态检查

- Python `3.11.15`；
- `pypdf 6.14.2`；
- `python-multipart 0.0.32`；
- `SQLAlchemy 2.0.51`；
- `psycopg 3.3.4`；
- `pip check`：`No broken requirements found.`；
- Python compileall：通过；
- Compose 配置：通过；
- `git diff --check`：通过，只有 LF/CRLF 非阻断提示。

#### 8.2 真实 PostgreSQL/PDF 验收

- Docker PostgreSQL：`postgres:16-alpine`；
- 容器状态：`healthy`；
- `python -m backend.app.models.init_db`：成功；
- 真实测试 PDF：3 页，其中 1 页空白；
- `/documents/upload`：`201`；
- 文件内容写入并读回一致；
- PostgreSQL 行可查询；
- `extracted_text` 含两个 `\f`，第一页和第三页文本存在；
- 测试行与文件清理成功；
- 验收后 `documents` 行数为 `0`。

#### 8.3 全量测试

启用 PostgreSQL 集成测试：

```text
collected 44 items
44 passed, 1 warning
```

Day 2 `/health` 和 Day 3 `/chat` 测试全部通过。

唯一警告：pytest 无法写入 `.pytest_cache`，`[WinError 5] 拒绝访问`。根因待确认，不影响测试。

### 9. 本轮遇到的问题

1. 受限网络首次安装新依赖失败，批准联网后成功安装；无需重复处理。
2. 首轮新增测试使用当前 Starlette 不存在的 413 新常量名，已改为兼容常量；最终测试通过。
3. PostgreSQL 镜像首次拉取命令两次超时，但后台下载最终完成；官方镜像已存在并成功启动。
4. Docker CLI 无法读取用户级 `config.json` 的警告不影响 Compose 配置、拉取、启动或测试。
5. pytest 缓存权限警告仍存在，待确认。

### 10. 不可违反的约束

- 使用 Python 3.11；
- 后端代码位于 `backend/`；
- 公共函数使用类型标注；
- 使用 pytest，完成任务前运行全量测试；
- 不提交 `.env`、API Key 或 PostgreSQL 真实密码；
- 不记录上传正文、数据库密码或原始数据库错误；
- 未经用户明确授权不得修改 `PLAN.md`；
- 不得重写或删除已验收的 Day 4 检查点；
- 不得开始 Day 5 或实现切分、chunks 表、Embedding、Qdrant。

### 11. 当前唯一下一步

向用户报告 Day 4 本地提交哈希和最终检查结果，然后等待明确选择：推送、开始 Day 5
或继续暂停。推送和 Day 5 都需要单独授权。

### 12. 常用命令

```powershell
# 启动 PostgreSQL
docker compose up -d postgres

# 显式建表
.\.venv\Scripts\python.exe -m backend.app.models.init_db

# 普通离线测试（集成测试跳过）
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 本地 PostgreSQL 全量验收
$env:RUN_POSTGRES_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# 依赖检查
.\.venv\Scripts\python.exe -m pip check
```

## B. 300 字以内快速恢复摘要

仓库 `D:\2019\rag-agent`，分支 `master`，Day 4 已形成未推送的本地检查点。已实现 multipart PDF/MD/TXT 上传、20 MiB/500 页限制、UUID 分块存储、PDF 空白页保留与 `\f` 分页、SQLAlchemy/psycopg PostgreSQL 持久化和失败补偿。真实三页 PDF/PostgreSQL 验收通过，全量 `44 passed, 1 warning`。`PLAN.md` 已按授权同步；Day 4 文件应无剩余差异，无关未跟踪 `.agents/` 不属于本次提交。下一步等待用户决定推送、开始 Day 5 或继续暂停。

## C. 新会话恢复要求

新会话应完整阅读 `HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`AGENTS.md`、
`README.md`、`docs/architecture.md`、Day 4 代码和测试，然后只读核对 Git 状态。不得读取 `.env`，
不得自行推送、重写检查点或开始 Day 5。
