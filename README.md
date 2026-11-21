> **历史检查点（2026-11-14）**：Day17 冻结题集与六份 PDF、Day18 真实 50 题基线已完成；Day19 请求 trace、不付费向量对照及授权的付费完整 RAG 对照已完成，四项 PLAN 与进度表按实测更新并形成本地提交。本次完整后端测试为 724 passed/14 skipped/0 failed，退出码 0。分支仍为 `codex/day17-eval-dataset`，未推送 Day19 或合并 `master`，Day13 未勾，Day20 未开始。当前 Git 状态见[状态](STATUS.md)。
> 下方 2026-11-02 的分支、HEAD 和“Day17 未开始”属于历史交接快照；运行命令与接口说明按当前源码核对。

---

# 企业知识库 RAG Agent

FastAPI + LangGraph + PostgreSQL + Qdrant，使用本地CPU BGE、BM25/RRF/Rerank和DeepSeek compatible LLM，
提供知识库问答、可信当前来源、单工具选择、短期多轮记忆及请求级 trace。

## Docker Compose 启动（Day21）

Day21 使用 Docker Compose 一次启动 FastAPI、Streamlit、PostgreSQL 和 Qdrant。交付和验收状态见 [HANDOFF.md](HANDOFF.md)。

使用支持 BuildKit 的 Docker 和 Compose 2.17 或更新版本。在仓库根目录运行。首次使用时把 `.env.example` 复制为 `.env`，填写 `POSTGRES_PASSWORD`。已有 PostgreSQL 卷时，使用初始化该卷的数据库名、用户名和密码。需要真实问答时，填写有效的 `LLM_API_KEY` 和供应商支持的 `LLM_MODEL`；只验证启动时可将 `LLM_API_KEY` 留空。

```powershell
docker compose up --build --wait
```

如果本机只提供独立的 Compose 命令，运行 `docker-compose up --build --wait`。启动后访问 [Streamlit](http://127.0.0.1:8501) 或 [FastAPI 文档](http://127.0.0.1:8000/docs)。用 `docker compose ps` 查看健康状态。若原有服务占用端口，在启动前通过 `POSTGRES_PORT`、`APP_PORT`、`STREAMLIT_PORT` 调整宿主机映射。保留旧栈时，选择空闲端口并给所有 Compose 命令加同一个 `-p rag-agent-day21`（放在子命令前），为新栈创建独立的数据卷。使用新卷时，请重新上传并索引需要检索的文档。

后端等待 PostgreSQL 和 Qdrant 就绪后执行已有建表命令，再启动 FastAPI。前端等待 FastAPI 健康检查通过。PostgreSQL、Qdrant 和后端数据各有独立命名卷。后端数据卷保存上传、BGE 模型和分词缓存。首次使用检索或上传功能时可能需要下载模型或分词文件。

上传成功表示文档已解析并入库。将页面显示的文档 ID 传给现有索引命令后，文档才参与向量检索。

```powershell
docker compose exec backend python -m backend.app.commands.index_document --document-id <UUID>
```

完成验证后，`docker compose down` 停止并移除这组容器，保留命名卷。

## Day19 请求 trace

已在本地实现 `POST /chat` 的请求级持久化 trace，以及受独立管理员密钥保护的 `GET /admin/traces?limit=20`。记录同次检索候选与证据门、工具、供应商实际 token 用量、答案、来源、耗时和 JSON/SSE 终态；缺失用量保留为未知。启用前须运行显式建表入口创建 `request_logs`，并在进程环境中设置 `ADMIN_TRACE_TOKEN`；密钥不从项目 `.env` 读取。实现、边界、查询方法见 [Day19 可观测性记录](docs/day19-observability.md)。真实 PostgreSQL 的 Day19 trace 仍未在线验收；本次完整后端测试为 724 passed、14 skipped、0 failed。Day19 代码和文档已形成本地提交，尚未推送。

补充的[离线分块对照](docs/day19-chunk-comparison.md)使用冻结六份 PDF 与本机 BGE：500/100 有 7 个块超过 512-token 上限；可用的 200/40、250/50、300/60 三组纯向量 Top5 全页命中为 21/40、16/40、22/40。它不代表生产 `source_hit`，也不能支持“500 最高”的话术。

另经授权完成[完整 RAG 50 题对照](docs/day19-full-comparison.md)：200/40（o200k token）、300/60（o200k token）、500/100（BGE token）的最终来源命中分别为 7/40、6/40、7/40，150 条结果均正常。500/100 与 200/40 持平，且 BGE-token 方案不是上述超限的原 o200k-token 500/100。记录至少 207 次付费请求，不能据此报精确费用；隔离实验数据已清理，原有 Qdrant collection 保留。

## Day18 真实评测基线

2026-11-08 使用 DeepSeek `deepseek-v4-flash` 在六份英文 PDF（语料 `day17-v1`）上执行 `day17-v1.1` 的 50 道中文单轮问题。评测前后均核对了 PostgreSQL 和 Qdrant 中的 25 个 Chunk 和对应索引点。50 题均正常返回，实际发起 65 次模型请求，预算为 100 次。

| 指标 | 实测 |
|---|---:|
| 整体规则准确率 | 11/50（22.0%） |
| 有答案题候选来源全命中率 | 30/40（75.0%） |
| 有答案题最终引用全命中率 | 6/40（15.0%） |
| 有答案题答案与引用联合通过率 | 3/40（7.5%） |
| 无答案题正确拒答率 | 8/10（80.0%） |
| 有答案题固定拒答率 | 29/40（72.5%） |

延迟覆盖 LangGraph 单轮工具选择、检索、重排和生成，HTTP 与会话落库耗时在计时范围外。首题 97.50 秒，后续 49 题 P50 为 6.82 秒，P95 为 8.39 秒。关键词规则提供近似判分。例如 `qa_022` 已回答物资、药物和宠物准备要求，规则仍将该组标为缺失。这道题也漏答了交通影响。

Day18 提交前完整离线 pytest 为 697 passed、14 skipped（24.59 秒），退出码 0；用户确认审查、测试与修复通过，Day18 五个 PLAN 复选框及进度表已勾，代码与文档形成本地提交。本机正式报告为 `eval/eval_report.md`，逐题记录和运行清单位于 `data/eval/day18/20261108T095705Z-real-625c1f7c53b2/`；这些原始产物被 Git 忽略，未随提交发布。执行命令和指标口径见[评测说明](eval/README.md)，Windows 服务启动见[Docker 恢复记录](docs/docker-desktop-recovery.md)。后续开发动作待指定，精确工作区状态与新会话入口见[当前交接包](HANDOFF.md)。

## 历史档案：2026-11-02 Day16 检查点

下列原始记录保留当时的分支、测试与范围，以上方 Day18 基线及当前交接包为准。

**当前完成到Day16，功能开发暂停，Day17未开始。**
恢复入口是[HANDOFF.md](HANDOFF.md)的完整A/B/C，其次[STATUS.md](STATUS.md)、[DECISIONS.md](DECISIONS.md)、[TODO.md](TODO.md)。
新会话先只读核对/复述，等状态确认和唯一动作；本轮只整理六文档，不重跑测试/服务或提交推送。

## 当前检查点

| 项目 | 状态 |
|---|---|
| 仓库/分支 | D:\2019\rag-agent / codex/day16-conversation-memory |
| HEAD | 115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d，feat: complete Day 16 conversation memory |
| 父提交 | 74949214e8f163fbdfa2e035993a640ab866026e，feat: implement Day 16 conversation memory |
| 完成确认 | Day16五项、完成确认/日志于2026-11-02按用户确认完成；Day14五项、Day15四项/日志已勾 |
| 发布 | Day16及Day15各两提交仅本地、无上游；本轮只读GitHub未见这两分支 |
| master/Day14 | master仍b68b590c8262eb568a371c895e4f7033456d045c；Day14 b76987934663f7d90603dbc4abb2432d52baf91f已发布 |
| PR | 本轮open PR=0；closed/merged历史待确认 |
| 工作区 | 仅上述五份根文档和docs/architecture.md六文档未暂存，暂存区空；无关.agents/和用户PDF保留未读 |
| 最新完整标准 | **652 passed / 14 skipped，45.43s，0失败/0警告，dotenv/服务连接尝试0、付费0** |

Day13学习证据此前已验但四项/日志未勾，不自动补标。[PLAN.md](PLAN.md)本轮只读；开发规则见[AGENTS.md](AGENTS.md)。
后端/Docker/PG/Qdrant、新会话表、词表/模型/缓存、代理及目录外材料当前可用性待确认。
用户确认审查、测试和修复通过不等于真实DeepSeek准确率测量。

## 目录与当前功能

~~~text
backend/app/
  api/                  health / upload / retrieval / chat
  agent/                state / graph / nodes / tools / service
  core/                 config / database / logging
  models/               Document / Chunk / Conversation / ConversationMessage / init_db
  services/             parsing/storage/splitter/embedding/qdrant/bm25/hybrid/reranker
                        llm/rag/document_catalog/conversation_memory
backend/tests/          pytest，默认替身/SQLite，真实集成需显式开关
docs/                   分日验收、JSON原始结果、MMD图、architecture
PLAN.md                 每日任务；未获明确授权不得修改
~~~

当前[架构](docs/architecture.md)：

~~~text
首轮：原问题 -> 选择单工具 -> 执行 -> 生成/拒答
后续：原问题 + 截断历史 -> 独立问题改写 -> 选择单工具 -> 执行 -> 生成/拒答
搜索：Hybrid(vector20+BM25 20，RRF60) -> CPU BGE Rerank5 -> 原vector_score>=0.46
目录：ready安全SQL元数据，50+1/详情chunk_count，不读正文，sources=[]
完成：原始user + 完整assistant + 当前安全sources，同一PG事务
~~~

图注册rewrite_query_node/select_tool_node/tool_node/generate_node四个业务节点。
内部合法PreparedRAG直接进入generate，不读写会话、不改写/选择/执行工具。
无checkpointer、长期记忆、历史总结、向量记忆、循环/并行工具或会话管理HTTP API。

## 环境与启动命令

Python **3.11**；已有.env/.venv不得覆盖，禁止读取、输出或提交凭据。
这些是操作手册，不是暂停状态下的执行许可；新会话第一轮只读。

~~~powershell
Set-Location -LiteralPath 'D:\2019\rag-agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
~~~

默认接口文档http://127.0.0.1:8000/docs；GET /health只表示进程存活，不检查数据库/模型/其他服务。
应用启动和health不建表、不加载模型、不连接PG/Qdrant。
配置字段公开模板见[.env.example](.env.example)；配置前缀APP_/LLM_/POSTGRES_/EMBEDDING_/QDRANT_/RERANKER_/RAG_/MEMORY_。Day19 的 `ADMIN_TRACE_TOKEN` 仅从进程环境读取。
源码默认LLM=https://api.deepseek.com、deepseek-v4-flash、timeout60s；实际进程配置及供应商可用性待确认。
openai包只是compatible SDK，不代表调用OpenAI服务或需要OpenAI Key。
上传/模型相对目录锚定PROJECT_ROOT，默认data/uploads、data/models。

显式服务/建表/索引入口（另获对应任务授权后使用）：

~~~powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m backend.app.models.init_db
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
~~~

当前docker-compose.yml仅PostgreSQL；Qdrant历史镜像qdrant/qdrant:v1.18.1、命名卷rag-agent-qdrant-data，
绑定127.0.0.1:6333，尚未做完整backend/frontend/qdrant一键编排。
init_db显式注册五个模型（含 Day19 的 `request_logs`），只create_all缺失表，不迁移旧表；真实PG中的 Day19 表尚未核验。
上传不自动Embedding或索引；embed_document只产内存结果，index_document才upsert Qdrant。
PG会话在模型推理/upsert前关闭；不自动重建collection，PG/Qdrant不是跨库事务。

## API与多轮用法

| 路径 | 输入/结果 |
|---|---|
| GET /health | 200 {"status":"ok"}，本轮未探测 |
| POST /documents/upload | multipart file，PDF/MD/TXT，成功201；实际≤20MiB、PDF≤500页 |
| POST /retrieval/search | query、strict top_k默认5/1..20、可选单UUID doc_id；原Cosine score |
| POST /retrieval/bm25/search | 同上；原BM25 score，token无重合返回空 |
| POST /retrieval/hybrid/search | 同上；两路各20融合，返回RRF score |
| POST /retrieval/rerank/search | 仅query、可选doc_id；固定20→5，原logit及名次 |
| POST /chat | message、stream默认false、可选session_id UUID/null；JSON/SSE |
| GET /admin/traces | `limit` 默认20、范围1..100；仅持正确 `X-Admin-Token` 可读最近请求 trace，响应禁缓存 |

检索query strip后1..4096字符，extra禁止，top_k不接受bool/字符串/浮点/null。
Rerank不接受top_k/candidate_k/mode。合法doc_id无匹配返回200空结果。
Chat保留extra忽略规则，但不能用needs_*额外字段绕过业务。

首轮：

~~~json
{"message":"有哪些文档？","stream":false}
~~~

完整响应：

~~~json
{"answer":"...","model":"...","sources":[],"session_id":"后端生成的UUID"}
~~~

后续将实际返回的UUID传入session_id，并把message改为新问题；省略/null会创建新会话。
搜索sources为本次结果的filename/page去重，目录sources=[]；不从历史答案复制来源。
SSE通过X-Session-ID返回UUID，响应头Cache-Control=no-cache、X-Accel-Buffering=no。

~~~text
data: {"delta":"..."}

event: sources
data: {"sources":[]}

data: [DONE]
~~~

同一图迭代器在HTTP建立前完成必要改写、选择和工具执行；delta逐段背压，完整成功并保存后才sources/DONE。
流开始后错误用event:error且不发sources/DONE；异常原文/SQL/工具参数/State不公开。
已有会话不存在404、同会话进程内忙409；记忆不可用503/内部500；LLM缺配置503/选择改写生成502。
其他严格错误文案、检索分层、预取关闭边界见HANDOFF第8节。

记忆存于PG conversations/messages：最多5个完整轮次/10条消息；Prompt默认o200k_base/2000 token，
可配128..16000；优先保留最新完整轮，仅最新轮单独超限时裁内容，保留Unicode及完整来源条目。
数据库保留全文，user metadata={}、assistant仅当前安全sources，不存Prompt/工具参数/Chunk/用量/延迟。
有历史才改写：非流式JSON、thinking关闭、SDK retry0、max_tokens=4096；结果仍1..4096字符，不静默降级。
原问题不变、独立问题用于搜索；详情UUID须来自原问题或本次截断历史，不能仅由改写模型生成。

完整轮同事务保存，取消发生在提交前则回滚；同进程跨实例lease互斥409，不是多worker分布式锁或身份认证。
首轮选择/生成/保存异常时尝试删除本次新建且仍为空的会话；已有/非空不删；正常断开不保证空会话清理。
已提交完整轮次后网络失败不能撤回；不宣称DB提交和客户端收到DONE原子。
Prompt把当前工具结果规定为事实依据；实际模型遵循准确率待确认。
公共拒答仍先选择，有历史再有改写，只省最终生成；内部PreparedRAG拒答总LLM0。

## 固定检索与模型参数

- 按页o200k_base切分500/100；BGE另有512 token预检，不能将两个tokenizer口径混用。
- BAAI/bge-small-zh-v1.5，revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4，CPU/512维归一化/batch≤32；
  查询仅一次前缀“为这个句子生成表示以用于检索相关文章：”，文档无此前缀。
- Qdrant默认documents、unnamed 512/Cosine、localhost:6333、timeout10s，显式upsert/wait=True。
- Hybrid顺序两路各20，按chunk UUID等权RRF60；重复/冲突安全失败，任一路失败不降级。
- BAAI/bge-reranker-base，revision 2cfc18c9415c912f9d8155881c133215df768a70，CPU/512、batch默认4/范围1..8；
  safetensors/local_files_only/trust_remote_code=False，query不截断、passage only_second，score为原logit。
- 原始vector_score默认0.46才是搜索生成证据门；BM25-only不生成，RRF/logit不能套用这个阈值。
- 三工具白名单、严格单调用/64KiB/重复键/字段/类型/UUID验证，目录ready安全列/SQL最多51返回50。

固定依赖sentence-transformers==5.3.0、qdrant-client==1.18.0、rank-bm25==0.2.2、langgraph==1.2.16；
Day16无新依赖；安装了checkpoint/prebuilt依赖不等于启用对应运行功能。

## 测试、验收与运行边界

[AGENTS.md](AGENTS.md)标准命令：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
~~~

11月2日实际接受标准通过目录外隔离run_checks.py执行pytest.main：652 passed / 14 skipped（45.43s），
Python3.11.15、0失败/0警告，dotenv/真实连接尝试0、付费0；裸命令不自带这些守卫。
最新见[Day16 MD](docs/day16-conversation-memory.md)与[JSON](docs/day16-conversation-results.json)的completion_checkpoint.standard_test。
JSON顶层644/14、256 token、PLAN未变是11月1日历史；当前改写4096 token、PLAN Day16已完成。
本轮交接不重跑测试，不用历史通过代替服务健康。

默认关闭的7个真实开关：

~~~text
RUN_POSTGRES_INTEGRATION
RUN_QDRANT_INTEGRATION
RUN_LOCAL_EMBEDDING_INTEGRATION
RUN_RAG_INTEGRATION
RUN_RERANKER_INTEGRATION
RUN_LLM_TOOL_SELECTION_INTEGRATION
RUN_CONVERSATION_POSTGRES_INTEGRATION
~~~

14跳过=原12项可选真实+付费选择1+真实PG记忆1。
真实PG记忆入口会显式建新表/写入并清理自建会话，只用进程配置、不读.env；当前未执行。
真实工具选择入口已收录未执行，成功一次3次付费选择，不执行工具/生成；真实DeepSeek选择/改写准确率无结论。
隔离运行器、词表、精确复验命令及单独授权边界见HANDOFF第12–13节，不能在暂停恢复时自动运行。

| 历史范围 | 结果与局限 |
|---|---|
| 11月1日原Day16 | 644/14，18.83s |
| 10月31日Day15完成 / 10月30日实现 | 571/13，34.70s / 563/12，44.52s |
| 10月29日最近真实局部 | 3 passed，160.84s；PG/Qdrant/BGE/Reranker真实，LLM替身 |
| 10月28日历史全部本地真实 | 413 passed，158.94s；Day12历史，LLM替身，不是当前Day16全真实 |

没有当前Day16全真实组合结论，不能加总历史计数。
长独立问题回归含CharacterEncoding/SDK/检索替身，不证明真实DeepSeek/BGE长问题质量或容量。
历史失败、已否决方案、代理/Docker错误原文和恢复文件路径均在HANDOFF，不在此重复操作。

## 历史受控检索实验

以下保留分阶段方法与结果，不代表当前自然语料、50QA、真实模型选择/改写或全链路性能。
其中Day12“拒答LLM零调用”仅指当时生成链路；Day16公共首轮有选择，有历史还有改写。

### 检索优化实验（Day9，历史）

使用随测试提交的 8 页确定性、自撰制度语料和 8 个带 `expected_phrase` 的固定问题，在
真实本地 BGE 与真实 Qdrant 上对比三种 chunk 配置。命中只按 NFKC + strip 后的
`expected_phrase` 子串包含关系判定，固定 Top 5：

| 配置 (size/overlap) | Chunk 数 | 平均 Chunk token | Hit@1 | Hit@5 | MRR@5 | Top-5 context token 总量 |
|---|---:|---:|---:|---:|---:|---:|
| 300/60 | 40 | 199.3 | 1.00 | 1.00 | 1.000 | 7986 |
| 500/100 | 24 | 332.9 | 1.00 | 1.00 | 1.000 | 13590 |
| 800/160 | 16 | 499.9 | 1.00 | 1.00 | 1.000 | 18576 |

关键发现：

- 三种配置产生不同 Chunk 数（40 / 24 / 16），全部通过真实 BGE 预检并完成 Qdrant 检索。
- 三种配置在 8 个单页事实问题上均为满分，当前小型语料无法区分检索质量；上下文近似
  成本随 chunk size 增大，Top-5 token 总量为 7986 / 13590 / 18576。
- 语料用固定长审计标识稳定拉开 `o200k_base` 长度；该标识被 BGE tokenizer 压缩为极少
  token。因此最大 BGE token 仅为 62 / 114 / 213。这是刻意的受控实验设计，不代表自然
  长文本能安全使用 800 token Chunk。
- 生产默认保持 `500/100` 不变；本实验语料受控且规模小，不构成"普遍最优"结论。

完整方法、数据与局限性见 [Day 9 检索优化实验](docs/day9-retrieval-tuning.md)。

### BM25 关键词检索与向量对比（Day 10）

`POST /retrieval/bm25/search` 复用 Day 9 的严格 `query/top_k/doc_id` 请求和 Chunk 响应
结构，但 `score` 是原始 BM25 分数，不是概率、不限制在 `0..1`，也不能与 Cosine score
直接比较。BM25 首次请求才读取 PostgreSQL 中 `ready` 文档的 Chunk；每次请求计算完整
快照指纹，未变化时复用进程内索引，变化时在同一锁内完整构建后替换。刷新失败时当前
请求安全失败，不静默返回旧索引。

Tokenizer 固定执行 NFKC + casefold，中文生成 unigram/bigram，英文、数字和复合企业
编号同时保留完整形式与组成部分。查询 token 有序去重，corpus 保留词频。检索使用
`get_scores()` 和 token-overlap 门控，因此无关键词重合时返回空数组，负分或零分的真实
匹配不会被误删；`doc_id` 在 Top-K 前过滤。

真实 PostgreSQL + 本地 BGE + 临时 Qdrant 使用相同 24 个 Chunk ID、固定 500/100 和
Top 5 对比 12 个正样本：向量 Hit@1/Hit@5/MRR@5 为 `0.750/0.917/0.812`，BM25 为
`0.833/1.000/0.882`。精确编号类 BM25 三项均为 1.0；三条知识库外英文问题的返回率
向量为 1.0、BM25 为 0.0。该小型受控实验不证明 BM25 普遍优于向量，也不包含 Hybrid。

完整逐题排名、方法和局限见
[Day 10 纯向量与纯 BM25 对比](docs/day10-vector-vs-bm25.md)。

### Hybrid 排名融合（Day 11）

`POST /retrieval/hybrid/search` 复用严格的 `query/top_k/doc_id` 请求和 Chunk 响应结构。
先同步执行向量检索，再执行 BM25，两路均固定召回最多 20 条；按 `chunk_id` 聚合并计算
`1/(60+vector_rank) + 1/(60+bm25_rank)`，rank 从 1 开始，缺席一路贡献为零，最后截取
请求的 `top_k`。两路原始 score 不参与融合；响应 `score` 是 RRF score，不能套用 `0.46`。

同一分支重复 ID 或跨分支同 ID 的正文、来源、顺序、metadata 冲突返回安全 502；只在
一路出现的 Chunk 可正常返回。任何一路异常均整体失败，不静默降级。

真实 PostgreSQL、本地 BGE、Qdrant 使用完全相同的 24 个 Chunk ID，候选深度 20、评估
Top 5，12 个正样本得到：

| 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---:|---:|---:|
| 向量 | 0.750 | 0.917 | 0.812 |
| BM25 | 0.833 | 1.000 | 0.882 |
| Hybrid | 0.917 | 1.000 | 0.944 |

Hybrid 补回向量 Top 5 漏掉的 1 题，但三条负样本仍全部返回结果，不能将 RRF 当成拒答
机制，也不能由此小样本宣称普遍优于单路。逐题排名、分组指标和局限见
[完整实验](docs/day11-hybrid-comparison.md)。Day11时`/chat`保留向量检索与生成门控；
Day12已按独立授权升级为Hybrid→Rerank→生成，见下节。

成功请求会自然产生向量、BM25、Hybrid 三条完成日志。`hybrid_search_completed` 仅记录
query 哈希/长度、参数、候选数、结果身份、两路 rank 和 RRF score，不记录 query、正文、
tokens、metadata、向量或原始分支 score。

### 本地 Rerank 与三阶段问答（Day12）

`POST /retrieval/rerank/search`只接受`query`与可选`doc_id`，固定Hybrid Top20→Rerank Top5。
使用CPU `BAAI/bge-reranker-base`，revision为
`2cfc18c9415c912f9d8155881c133215df768a70`；safetensors、禁止remote code、首次请求懒加载。
query完整保留，超出模型容量安全422；只显式截断passage并记录数量。

响应`score`为原始logit，同时返回`hybrid_rank`、`rerank_rank`、`rank_change`；内部向量分数
不公开。`rank_change=hybrid_rank-rerank_rank`，正数表示上升。日志记录所有候选前后排名，
不记录问题或正文。`/chat`已经使用该链路，JSON/SSE和可信来源结构保留。

2026-10-28同一24 Chunk/12正样本历史实验：Hybrid指标0.917/1.000/0.944，Rerank为0.917/1.000/0.958。
远程接入正确目标3→2，Hit@1没有改善；无关候选升位也有记录。3负样本经RAG证据门全部
固定拒答，LLM零调用。实例首次装载约2.83s、热推理约6.29s/20候选，属于已缓存的同进程
测量。完整逐题、至少三个名次变化、测试和局限见[实验报告](docs/day12-rerank-comparison.md)。

## 后续与恢复验收

自然50QA/LLM-as-judge、完整trace、Streamlit、完整Compose、会话管理/身份认证尚未实现。
多worker锁、BM25全扫描、跨库一致性、自然长文/表格/多跳、CPU p50/p95/QPS及Docker根因待后续指定范围。

新会话唯一目标：读HANDOFF A/B/C及相关文件，只读核对Day16已完成/已勾/本地未发布、六文档未暂存/空暂存区、
最新652/14与历史644/14、571/13、563/12、真实3和历史413；复述缺失/矛盾及最多5步，等待状态确认和唯一动作。
下一步最小改动0，不自动测试、发布、补勾Day13或开始Day17。
