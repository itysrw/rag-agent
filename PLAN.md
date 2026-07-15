# 企业知识库 RAG Agent 系统 — 25 天冲刺计划

**目标**：做出一个能写进简历、能在面试中展开讲的完整项目  
**技术栈**：Python · FastAPI · LangGraph · Qdrant · PostgreSQL · Streamlit · Docker  
**每天安排**：5-6 小时（30 分钟看文档 · 3 小时写代码 · 1 小时调试 · 30 分钟写日志 · 30 分钟背八股）

> 修改说明（对比原版）：
> - LangGraph 从 1 天扩展为 3 天（Day 13-15），你没用过 LangChain，需要缓冲
> - 前端从 React/Vue 改为 Streamlit，节省 2 天，演示效果够用
> - Hybrid search 给 2 天（Day 10-11），调试量大
> - 移除 Redis（原计划中实际没用到）
> - 移除 Elasticsearch，用 `rank_bm25` 库替代
> - 总天数 21 → 25，但每天工作量更合理

---

## 进度总览

| 阶段 | 天数 | 内容 |
|------|------|------|
| 基础搭建 | Day 1-3 | 项目骨架 + FastAPI + LLM 接入 |
| 文档处理 | Day 4-6 | 上传解析 + 切分 + Embedding |
| 检索系统 | Day 7-11 | Qdrant + RAG + Hybrid + Rerank |
| Agent | Day 12-16 | LangGraph + 工具调用 + 多轮记忆 |
| 评测与质量 | Day 17-19 | 数据集 + 评测脚本 + 可观测性 |
| 交付 | Day 20-25 | 前端 + Docker + README + 面试准备 |

---

## 每日任务

### Day 1 — 项目边界与架构

- [x] 初始化本地 Git 仓库和 `.gitignore`
- [x] 关联 GitHub 远端仓库
- [x] 写 README 初稿（项目介绍、技术栈、TODO list）
- [x] 使用 Mermaid 绘制架构图并放入 README
- [x] 明确功能边界：文档上传 · 切分 · 向量检索 · RAG 问答 · Agent 工具调用 · 评测 · Docker 部署
- [x] 建好目录结构（见下方参考）

**产出**：README 有架构图和 TODO，目录结构建好

<details>
<summary>参考目录结构</summary>

```
rag-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由
│   │   ├── core/         # 配置、日志
│   │   ├── services/     # LLM、embedding、检索
│   │   ├── models/       # DB 模型
│   │   ├── agent/        # LangGraph agent
│   │   └── main.py       # FastAPI 应用入口（Day 2 创建）
│   ├── tests/
│   └── requirements.txt  # Python 依赖（Day 2 创建）
├── frontend/             # Streamlit
├── eval/                 # 评测脚本和数据集
├── docker-compose.yml
├── .env.example
└── PLAN.md
```
</details>

---

### Day 2 — FastAPI 后端骨架

- [ ] 初始化 FastAPI 项目，安装依赖（`fastapi` `uvicorn` `python-dotenv` `loguru`）
- [ ] 配置 `.env` 和 `.env.example`
- [ ] 实现基础接口：`GET /health` · `POST /chat` · `POST /documents/upload`（占位）
- [ ] 接入 loguru 日志
- [ ] 写一个简单 pytest 测试验证 `/health`

**产出**：后端能启动，`/health` 返回 `{"status": "ok"}`

---

### Day 3 — 接入大模型 API

- [ ] 选定模型：DeepSeek / 通义千问 / OpenAI（任选，都是 OpenAI-compatible）
- [ ] 封装 `LLMClient`，支持同步和流式输出
- [ ] `/chat` 接口能正常返回模型回答
- [ ] 实现流式输出（SSE 或 streaming response）
- [ ] 写单元测试验证流式和非流式

**产出**：`/chat` 可以对话，支持流式返回

---

### Day 4 — 文档上传与解析

- [ ] 安装依赖：`pypdf2` 或 `pdfminer.six`，`python-multipart`
- [ ] 支持上传 PDF / Markdown / TXT
- [ ] 提取文本内容
- [ ] 用 Docker 启动 PostgreSQL，建 `documents` 表
- [ ] 上传后存储文档元信息（filename、size、status、created_at）
- [ ] 本地保存文件（`/data/uploads/`）

**产出**：上传一个 PDF 后，数据库里能看到文档记录

---

### Day 5 — 文本切分

- [ ] 安装 `langchain-text-splitters`（只用这一个模块，不用完整 LangChain）
- [ ] 实现 `RecursiveCharacterTextSplitter`
- [ ] Chunk 字段：`doc_id` · `chunk_id` · `content` · `page` · `metadata`
- [ ] 测试 300 / 500 / 800 token 三种 chunk size，记录差异
- [ ] 建 `chunks` 表，切分结果存入 PostgreSQL

**产出**：一个文档能被切成多个 chunks，入库

---

### Day 6 — 接入 Embedding

- [ ] 选定 embedding 模型（推荐：`text-embedding-3-small` 或 `BAAI/bge-small-zh-v1.5` 本地）
- [ ] 封装 `EmbeddingClient`
- [ ] 对 chunks 批量生成 embedding（每批 32 条）
- [ ] 加失败重试（最多 3 次，指数退避）
- [ ] 把 embedding 维度记录进配置

**产出**：每个 chunk 都能生成 embedding，打印维度确认

---

### Day 7 — 接入 Qdrant

- [ ] 用 Docker 启动 Qdrant（`docker run -p 6333:6333 qdrant/qdrant`）
- [ ] 创建 collection（指定 embedding 维度和距离函数）
- [ ] 把 chunk + embedding 写入 Qdrant，payload 带 metadata
- [ ] 实现 `POST /retrieval/search`：输入 query，返回 top-k chunks
- [ ] 测试几个问题，看返回结果是否相关

**产出**：输入 query 能返回相关 chunks，结果肉眼合理

---

### Day 8 — 实现基础 RAG

- [ ] `/chat` 接入检索流程：query → 检索 → 构建 prompt → 生成
- [ ] Prompt 模板：system 指令 + context + user question
- [ ] 回答里带引用来源（文档名 + 页码）
- [ ] 无相关文档时回答"知识库中没有相关信息"，不乱答
- [ ] 端到端测试：上传文档 → 问问题 → 看答案

**产出**：能基于上传文档回答问题，带来源引用

---

### Day 9 — 优化检索效果

- [ ] 加 `top_k` 参数（默认 5，支持调整）
- [ ] 加 metadata filter（按 doc_id 过滤，只查特定文档）
- [ ] 对比 chunk size 300 / 500 / 800 对检索质量的影响
- [ ] 记录每次检索返回的 chunks（用于后续评测）
- [ ] 在 README 里写一段"检索优化实验"记录

**产出**：README 里有检索优化记录，能在面试中讲

---

### Day 10 — BM25 关键词检索

- [ ] 安装 `rank_bm25`
- [ ] 对 chunks 内容建 BM25 索引（内存中即可）
- [ ] 实现关键词检索接口
- [ ] 测试：纯向量 vs 纯 BM25，记录各自擅长的场景

**产出**：BM25 检索能独立跑通，有对比记录

---

### Day 11 — Hybrid Search 融合

- [ ] 实现 RRF（Reciprocal Rank Fusion）融合两路结果
- [ ] 融合后统一排序返回 top-k
- [ ] 对比三种检索效果：纯向量 · 纯 BM25 · Hybrid
- [ ] 把对比结果写进 README（这是面试亮点）

**产出**：检索模块支持 hybrid search，有量化对比

---

### Day 12 — Rerank

- [ ] 选择方案：API rerank（Cohere / 硅基流动）或本地 cross-encoder（`BAAI/bge-reranker-base`）
- [ ] 对 top-20 检索结果重排，输出 top-5
- [ ] 记录 rerank 前后排名变化
- [ ] 完整检索链路：query → hybrid search (top-20) → rerank (top-5) → answer

**产出**：三阶段检索链路跑通，rerank 前后有对比

---

### Day 13 — LangGraph 基础学习

- [ ] 看 LangGraph 官方文档：概念（Graph · Node · Edge · State）
- [ ] 跑通官方 quickstart example（不用改，照抄跑通即可）
- [ ] 理解 StateGraph 的 `add_node` / `add_edge` / `compile` 用法
- [ ] 画出你要实现的 Agent graph 节点图（手绘或 draw.io）

> 今天只学，不写自己的代码。跑不通官方 example 先不往下走。

**产出**：官方 example 能跑通，理解 graph 执行流程

---

### Day 14 — 把 RAG 链路迁移进 LangGraph

- [ ] 建 `AgentState`（包含 query、retrieved_docs、answer、tool_calls）
- [ ] 实现节点：`retrieve_node` · `generate_node`
- [ ] 加条件边：判断是否需要检索
- [ ] 用 LangGraph 替换原来的顺序调用链路
- [ ] 测试原有功能不回退

**产出**：RAG 问答走 LangGraph graph，功能和之前一致

---

### Day 15 — Agent 工具调用

- [ ] 定义工具：
  - `search_knowledge_base(query)` — 向量检索
  - `get_document_detail(doc_id)` — 查文档详情
  - `list_documents()` — 列出所有文档
- [ ] 在 graph 里加 `tool_node`，接入工具调用
- [ ] Agent 能根据问题类型选择调用哪个工具
- [ ] 测试：问"有哪些文档？" → 调用 `list_documents`

**产出**：Agent 能根据问题自主选择工具

---

### Day 16 — 多轮记忆

- [ ] 建 `conversations` 表和 `messages` 表
- [ ] 接口支持 `session_id` 参数
- [ ] RAG 时带最近 5 轮上下文（截断防止超 token）
- [ ] 处理指代消解：用 LLM 把"刚才那个文档"改写成完整 query
- [ ] 测试多轮对话是否连贯

**产出**：支持多轮问答，指代问题能正确处理

---

### Day 17 — 评测数据集

- [ ] 手工准备 50 条 QA（基于你上传的文档）
- [ ] 每条字段：`question` · `expected_answer` · `expected_source` · `difficulty`
- [ ] 覆盖四类问题：简单事实 · 跨段落 · 多跳推理 · 知识库外（无答案）
- [ ] 保存为 `eval/eval_dataset.jsonl`

**产出**：`eval_dataset.jsonl`，50 条

---

### Day 18 — 评测脚本

- [ ] 写 `eval/eval.py`，自动跑 50 条问题
- [ ] 记录每条：`answer` · `retrieved_chunks` · `latency` · `source_hit`
- [ ] 用 LLM-as-judge 打分（0-5 分），或用关键词匹配做简单评分
- [ ] 生成 `eval/eval_report.md`，包含整体准确率和各类型得分
- [ ] 在 README 里贴评测结果（面试必问）

**产出**：`eval_report.md`，有具体数字（如 source_hit rate 78%）

---

### Day 19 — 日志与可观测性

- [ ] 每次请求记录：query · retrieved_docs · tool_calls · prompt_tokens · completion_tokens · latency · answer
- [ ] 存入 `request_logs` 表
- [ ] 实现 `GET /admin/traces` 接口，可查最近 N 条 trace
- [ ] 准备面试话术："我通过 trace 发现 chunk size 500 时 source_hit 最高"

**产出**：每次请求有完整 trace，能查询

---

### Day 20 — Streamlit 前端

- [ ] 安装 `streamlit`
- [ ] 实现三区域布局：左侧文档列表 · 中间聊天窗口 · 右侧引用来源
- [ ] 上传文档按钮
- [ ] 显示 Agent 调用了哪些工具（侧边栏展示）
- [ ] 流式输出支持

> 用 Streamlit 而不是 React，一天能做完，演示效果够用。

**产出**：有可视化界面，能录屏演示

---

### Day 21 — Docker Compose

- [ ] 写每个服务的 `Dockerfile`（backend · frontend）
- [ ] 写 `docker-compose.yml`，包含：backend · frontend · postgres · qdrant
- [ ] 加健康检查（`healthcheck`），确保 postgres 起来后 backend 再启动
- [ ] 测试：`docker-compose up` 一条命令启动
- [ ] README 写启动命令

**产出**：一条命令启动完整项目

---

### Day 22 — 打磨 README

- [ ] README 结构：项目背景 · 架构图 · 核心功能 · 技术亮点 · 效果评测 · 启动方式 · 截图
- [ ] 截图：前端界面、评测报告、架构图
- [ ] 技术亮点部分重点写：Hybrid Search 对比 · Rerank 收益 · LangGraph 工作流
- [ ] 检查 README 里没有空 TODO、没有"TODO: 待填写"

**产出**：README 看起来像完整产品文档

---

### Day 23 — 简历话术

- [ ] 写 3 条简历 bullet（用 STAR 格式）：
  - 负责什么（企业知识库 RAG Agent 系统，支持 XX 功能）
  - 用了什么技术（LangGraph · Qdrant · Hybrid Search · Rerank）
  - 指标是多少（source_hit rate XX%，latency XX ms，评测 50 条）
- [ ] 确保每条 bullet 都有数字
- [ ] 把 bullet 发给朋友看，确认表述清晰

**产出**：3 条可以直接贴进简历的描述

---

### Day 24 — 模拟讲解练习

准备 5 分钟项目介绍（不看稿讲清楚）：

- [ ] 项目背景：为什么做这个
- [ ] 系统架构：画图讲
- [ ] RAG 链路：query → hybrid search → rerank → answer
- [ ] Agent 工具调用：什么时候用 Agent，不用固定链式
- [ ] 评测：怎么评，结果是多少
- [ ] 遇到的问题和优化

**产出**：能流畅讲完，不卡顿

---

### Day 25 — 面试常见追问准备

- [ ] 为什么用 RAG，不用微调？
- [ ] 为什么用 LangGraph？优缺点是什么？
- [ ] chunk size 怎么选？你测了哪些？
- [ ] Rerank 有什么收益？用的什么模型？
- [ ] Hybrid search 怎么融合的？RRF 是什么？
- [ ] 怎么防止幻觉？
- [ ] Agent 工具调用失败怎么办？
- [ ] 怎么控制成本和延迟？
- [ ] 如果数据量很大（百万级 chunks）怎么处理？

**产出**：每道题都能答 2-3 分钟，有具体技术细节

---

## 八股学习资源

- GitHub 搜：`LLM Agent 面试题` / `RAG 面试八股`
- 知乎：搜"大模型 Agent 面试 2024 2025"
- 公众号：AI 进化论 · 机器学习算法工程师
- LangGraph 官方文档（必读）：概念 + how-to guides

---

## 开发日志

> 每天写 3-5 行，记录：做了什么 · 卡在哪 · 明天先做什么

| 天 | 完成情况 | 备注 |
|----|---------|------|
| Day 1 | 已完成 | 已完成边界、目录、README、Mermaid 架构图与 GitHub 远端配置 |
| Day 2 | | |
| Day 3 | | |
| Day 4 | | |
| Day 5 | | |
| Day 6 | | |
| Day 7 | | |
| Day 8 | | |
| Day 9 | | |
| Day 10 | | |
| Day 11 | | |
| Day 12 | | |
| Day 13 | | |
| Day 14 | | |
| Day 15 | | |
| Day 16 | | |
| Day 17 | | |
| Day 18 | | |
| Day 19 | | |
| Day 20 | | |
| Day 21 | | |
| Day 22 | | |
| Day 23 | | |
| Day 24 | | |
| Day 25 | | |
