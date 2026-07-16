# 企业知识库 RAG Agent 系统

企业级 RAG 问答系统项目。Day 1 至 Day 7 已提交；当前工作区已实现 Day 8 基础 RAG：
`/chat` 复用固定 Top 5 检索，在生成层进行相关性门控，使用结构化 Prompt 调用
OpenAI-compatible LLM，并返回后端生成的文件名/页码来源。Day 8 尚未提交，`PLAN.md`
本轮未修改。真实 DeepSeek 已在授权下完成一次报销 JSON、VPN SSE、Python 门控拒答冒烟；
覆盖边界见验收记录。Hybrid Search、Rerank、LangGraph Agent 等仍属于后续目标。

## 项目状态文档

- [完整交接包](HANDOFF.md)
- [当前状态](STATUS.md)
- [技术决策](DECISIONS.md)
- [后续任务](TODO.md)
- [架构说明](docs/architecture.md)
- [Day 8 RAG 验收记录](docs/day8-rag-smoke.md)

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11 · FastAPI · Uvicorn |
| Agent 编排 | LangGraph |
| 向量数据库 | Qdrant |
| 关系数据库 | PostgreSQL · SQLAlchemy 2.x · psycopg 3 |
| 文本向量 | SentenceTransformers · BAAI/bge-small-zh-v1.5 · CPU |
| 检索增强 | Hybrid Search (向量 + BM25) · Rerank |
| 前端 | Streamlit |
| 部署 | Docker · Docker Compose |

## 架构图

以下是最终目标架构；当前实现进度以“当前接口”和 TODO 为准。

```mermaid
flowchart TB
    user["用户"] --> ui["Streamlit 前端"]
    ui -->|"上传文档 / 发起问答"| api["FastAPI API"]

    subgraph ingest["文档入库链路"]
        parser["PDF / Markdown / TXT 解析"] --> splitter["Chunk 切分"]
        splitter --> embedding["Embedding"]
        embedding --> vector_store["Qdrant 向量索引"]
        splitter --> metadata_store["PostgreSQL 文档与 Chunk 元数据"]
    end

    api --> parser
    api --> agent["LangGraph Agent"]

    subgraph tools["Agent 工具"]
        search_tool["search_knowledge_base"]
        detail_tool["get_document_detail"]
        list_tool["list_documents"]
    end

    agent --> search_tool
    agent --> detail_tool
    agent --> list_tool
    detail_tool --> metadata_store
    list_tool --> metadata_store

    subgraph retrieval["检索与生成链路"]
        vector_search["Qdrant 向量检索"]
        bm25["BM25 关键词检索"]
        rrf["RRF 融合"]
        rerank["Rerank"]
        llm["OpenAI-compatible LLM"]

        vector_search --> rrf
        bm25 --> rrf
        rrf --> rerank
        rerank --> llm
    end

    search_tool --> vector_search
    search_tool --> bm25
    vector_store --> vector_search
    metadata_store --> bm25
    llm -->|"答案、引用来源、工具轨迹"| api
    api --> ui
```

问答链路：用户问题 → Agent 选择工具 → Hybrid Search → Rerank → LLM 生成带引用答案。

入库链路：上传文件 → 文本解析 → Chunk 切分 → 生成 Embedding → 写入 Qdrant 与 PostgreSQL。

## 目标功能

- **文档管理**：支持上传 PDF / Markdown / TXT，自动解析入库
- **Hybrid Search**：向量检索 + BM25 关键词检索，RRF 融合排序
- **Rerank**：对 top-20 结果重排，输出 top-5，提升精准度
- **RAG 问答**：基于检索结果生成答案，带来源引用
- **LangGraph Agent**：根据问题类型自主选择工具，支持多轮对话
- **评测系统**：50 条 QA 数据集，自动评测 source_hit rate 和答案质量

## 效果评测

> TODO: 填写评测结果

Day 5 已完成 300/500/800 token 的结构性对比，结果见
[Chunk Size 结构对比](docs/day5-chunk-size-comparison.md)。该实验不包含检索质量结论。

| 指标 | 数值 |
|------|------|
| Source Hit Rate | - |
| 平均延迟 | - |
| 评测集大小 | 50 条 |

## 快速启动

> 完整的一键启动将在 Day 21 完成。当前只编排 PostgreSQL。

```powershell
Copy-Item .env.example .env
# 编辑 .env，设置 LLM_API_KEY 和本地 PostgreSQL 密码
docker compose up -d postgres
.\.venv\Scripts\python.exe -m backend.app.models.init_db
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

## 本地开发

所有命令均从仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
# 编辑 .env，只把真实 DeepSeek Key 写入 LLM_API_KEY
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/docs` 查看接口文档，运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

## 本地 Embedding 验证

Day 6 使用固定 revision 的 `BAAI/bge-small-zh-v1.5`，不需要 OpenAI API Key，
也不会使用 DeepSeek Key。默认在 CPU 上每批最多处理 32 个 Chunk，输出 512 维归一化
向量。文档 Chunk 会直接编码，不添加查询指令。

首次运行会把模型下载到被 Git 忽略的 `data/models/`。使用已有 Document UUID 执行：

```powershell
.\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>
```

命令按 `chunk_index` 读取 PostgreSQL 中的 Chunk，在推理前使用 BGE tokenizer 检查
512 token 上限，并只打印模型、revision、Chunk 数量、维度和状态。它不会打印正文或完整
向量，也不会写回 PostgreSQL 或 Qdrant。真实模型测试默认跳过，可显式执行：

```powershell
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_embedding_integration.py -v
```

## 本地 Qdrant 索引与检索

Day 7 固定使用 `qdrant/qdrant:v1.18.1` 和 `qdrant-client==1.18.0`。Qdrant 仅绑定
本机 REST 端口 6333，并使用命名卷持久化：

```powershell
docker pull qdrant/qdrant:v1.18.1
docker volume create rag-agent-qdrant-data
docker run -d --name rag-agent-qdrant `
  -p 127.0.0.1:6333:6333 `
  -v rag-agent-qdrant-data:/qdrant/storage `
  qdrant/qdrant:v1.18.1
```

显式初始化 collection，并索引一个已有 PostgreSQL Document：

```powershell
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
```

Collection 使用 unnamed 512 维 Cosine 向量；Point ID 等于 Chunk UUID。索引命令在关闭
PostgreSQL Session 后才执行模型推理和 Qdrant upsert，每批最多 32 条并使用 `wait=True`。
重复运行依靠稳定 UUID 幂等覆盖。真实 Qdrant 测试需显式开启：

```powershell
$env:RUN_QDRANT_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v
```

## 基础 RAG 问答

Day 8 的 `/chat` 先执行 Day 7 固定 Top 5 检索，再在生成层用 `0.46` 门槛过滤 Context。
该值来自三条知识库内问题和三条知识库外问题的真实 BGE/Qdrant 校准，详细分数与限制见
[Day 8 RAG 验收记录](docs/day8-rag-smoke.md)。门槛不是可调 API 参数，也不是概率。

通过门槛的 Chunk 以 JSON 放入 user message，system message 只保存 RAG 安全规则。无相关
Context 时后端直接返回 `知识库中没有相关信息`，不调用 DeepSeek。普通响应包含
`answer`、`model` 和后端生成的 `sources`；SSE 成功流在 delta 后发送 sources event，
再发送 `[DONE]`。模型自由文本中的文件名/页码来源标记会被清理，客户端只应信任结构化
`sources`。上传后仍必须显式执行 `index_document`，不会自动索引。

## 当前接口

| 方法与路径 | 输入 | 当前响应 |
|------------|------|----------|
| `GET /health` | 无 | `200 {"status": "ok"}` |
| `POST /chat` | `{"message": "...", "stream": false}` | RAG JSON：answer、model、sources |
| `POST /chat` | `{"message": "...", "stream": true}` | RAG SSE：delta、sources、`[DONE]` |
| `POST /documents/upload` | `multipart/form-data`，字段 `file` | 成功返回 `201` 文档元数据；支持 PDF / MD / TXT |
| `POST /retrieval/search` | `{"query": "..."}` | 固定返回最多 5 个 Chunk、来源和 score，不返回向量 |

LLM 使用 OpenAI-compatible 接口。当前默认配置为 `deepseek-v4-flash`，
并通过 `LLM_EXTRA_BODY` 关闭思考模式；真实 `LLM_API_KEY` 只写入本地 `.env`。

文档上传按 1 MiB 分块写入临时文件，实际大小上限为 20 MiB；PDF 最多 500 页。
PDF 按页提取并以 `\f` 保存页边界，Markdown/TXT 使用 UTF-8 并视为第 1 页。
每个非空页面使用 `o200k_base` tokenizer 独立切分，默认上限为 500 token、overlap 为
100 token；空白页不生成 Chunk，后续页面保留原页码。Document 与有序 Chunk 在同一
事务中写入 PostgreSQL，上传成功响应字段保持不变。
数据库表必须通过 `python -m backend.app.models.init_db` 显式创建，应用启动和
`GET /health` 不依赖 PostgreSQL、Qdrant、BGE 或 LLM。搜索 Query 使用 BGE 查询
instruction；文档 Chunk 保持直接编码。当前检索接口不支持可调 top_k、doc_id filter 或
score threshold；RAG 门槛只在服务内部使用。

## TODO

- [x] 项目初始化，目录结构
- [x] FastAPI 后端骨架
- [x] 接入 LLM API（流式输出）
- [x] 文档上传与解析（PDF / MD / TXT）
- [x] 文本切分（RecursiveCharacterTextSplitter）
- [x] 本地 Embedding 生成（BGE · 批量 · 下载重试 · 不持久化）
- [x] Qdrant 向量存储与检索（显式索引 · 固定 Top 5）
- [x] 基础 RAG 链路（固定 Top 5 → 门控 → 生成 → 结构化来源）
- [ ] 检索优化（top_k · metadata filter · chunk size 对比）
- [ ] BM25 关键词检索
- [ ] Hybrid Search（RRF 融合）
- [ ] Rerank（cross-encoder 或 API）
- [ ] LangGraph Agent 编排
- [ ] Agent 工具调用（search / detail / list）
- [ ] 多轮对话记忆
- [ ] 评测数据集（50 条 QA）
- [ ] 评测脚本（LLM-as-judge）
- [ ] 请求日志与可观测性
- [ ] Streamlit 前端
- [ ] Docker Compose 一键部署
- [ ] README 完善 + 简历话术

## 开发日志

见 [PLAN.md](PLAN.md)
