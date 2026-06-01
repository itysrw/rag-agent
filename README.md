# 企业知识库 RAG Agent 系统

基于 LangGraph 的企业级 RAG 问答系统，支持多文档管理、Hybrid Search、Rerank 和 Agent 工具调用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11 · FastAPI · Uvicorn |
| Agent 编排 | LangGraph |
| 向量数据库 | Qdrant |
| 关系数据库 | PostgreSQL |
| 检索增强 | Hybrid Search (向量 + BM25) · Rerank |
| 前端 | Streamlit |
| 部署 | Docker · Docker Compose |

## 架构图

> TODO: 插入架构图截图

```
用户请求
    │
    ▼
FastAPI 后端
    │
    ├─► LangGraph Agent
    │       ├─► search_knowledge_base
    │       ├─► get_document_detail
    │       └─► list_documents
    │
    ├─► 检索链路
    │       ├─► 向量检索 (Qdrant)
    │       ├─► BM25 关键词检索
    │       ├─► RRF 融合
    │       └─► Rerank
    │
    └─► LLM 生成 (DeepSeek / OpenAI-compatible)

文档处理链路
文件上传 → 文本解析 → Chunk 切分 → Embedding → 写入 Qdrant + PostgreSQL
```

## 核心功能

- **文档管理**：支持上传 PDF / Markdown / TXT，自动解析入库
- **Hybrid Search**：向量检索 + BM25 关键词检索，RRF 融合排序
- **Rerank**：对 top-20 结果重排，输出 top-5，提升精准度
- **RAG 问答**：基于检索结果生成答案，带来源引用
- **LangGraph Agent**：根据问题类型自主选择工具，支持多轮对话
- **评测系统**：50 条 QA 数据集，自动评测 source_hit rate 和答案质量

## 效果评测

> TODO: 填写评测结果

| 指标 | 数值 |
|------|------|
| Source Hit Rate | - |
| 平均延迟 | - |
| 评测集大小 | 50 条 |

## 快速启动

```bash
# 复制环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 一键启动
docker-compose up -d
```

访问 `http://localhost:8501` 打开前端页面。

## TODO

- [x] 项目初始化，目录结构
- [ ] FastAPI 后端骨架
- [ ] 接入 LLM API（流式输出）
- [ ] 文档上传与解析（PDF / MD / TXT）
- [ ] 文本切分（RecursiveCharacterTextSplitter）
- [ ] Embedding 生成（批量 + 重试）
- [ ] Qdrant 向量存储与检索
- [ ] 基础 RAG 链路（检索 → 生成 → 引用来源）
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
