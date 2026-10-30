# 项目完整交接包

更新时间：2026-10-30（Asia/Shanghai）
仓库：D:\2019\rag-agent

**当前为 Day14 本地提交检查点：用户已确认审查、测试与修复通过，PLAN 五项及日志已勾选，本提交收录完整 Day14，未推送。**
本包 A/B/C 是当前恢复基线；Day12 详细交接全文放在历史附录中，保留原日期和当时状态。
区分功能实现、PLAN 标记、测试范围和 Git 发布，不因其中一项推断其他项。
恢复后等待用户指定唯一动作，不自动修改 PLAN、发布或开始 Day15。

## A. 当前详细交接文档

### 1. 本阶段交付与当前提交

将原顺序式 RAG 迁移为双节点 StateGraph，复用现有业务服务与外部协议。
用户本次确认审查与修复通过；本提交不再改源码、测试或依赖。
交付包括 agent/state、nodes、graph、service，RAGService/API 接入，新增 50 项回归，
完整标准和真实局部验收、实际编译图和文档。
入口：[Day14 迁移报告](docs/day14-langgraph-migration.md)、
[机器记录](docs/day14-langgraph-results.json)、
[图](docs/day14-agent-graph.mmd)、[架构](docs/architecture.md)。

未实现 Day15 工具或 Day16 记忆；没有 ToolNode、会话、checkpointer、LangSmith 导出。
未改变 Hybrid/Rerank/0.46 规则、Prompt、来源或上传/索引业务。
后续自然评测、前端与完整部署仍未完成。

### 2. Git、计划与历史矛盾的处理

| 项目 | 2026-10-30 本地提交检查点 |
|---|---|
| 当前分支 | codex/day14-langgraph |
| 本地 HEAD | 本 Day14 提交；精确哈希提交后用 git log -1 --format=%H 核验，父提交 34712772b3682d174f459da91100b09f8a2493cc |
| Day14 提交范围 | 27 个相关路径：提交前 15 个 tracked 变更（含删除 .gitkeep）、12 个新增；提交后相关改动应为 0、暂存区应为空，未推送 |
| 2026-10-29 实时远端（本次未复查） | GitHub codex/day12-rerank = 3471277；master = b68b590c8262eb568a371c895e4f7033456d045c |
| Day12 发布 | 已发布到远端分支、未合并 master；旧文“未推送”保留为历史 |
| PLAN | 用户本次确认并授权同步 Day14 五项/日志；Day1–12 原标记保留，Day13 与 Day15 以后不改 |
| Day13 | 仓库外学习笔记、图、官方示例和自测证据已核验；未在本轮补做或复制入仓库 |
| 无关文件 | .agents/、就业推荐表_完整填充版.pdf 保留且未读取，不进入交付 |

Day13 学习效果由用户自行确认；文件/运行证据不能代替理解自检。
2026-10-30 用户明确确认 Day14 审查、测试与修复通过并要求提交和修改状态；
本次据此更新 Day14 五项和日志，不补勾 Day13，不扩展到 Day15。
远端只代表本轮查询时点；不能用本地 tracking ref 推断下一会话实时状态。

### 3. 测试日期与范围

| 日期/阶段 | 实际结果 | 边界 |
|---|---|---|
| 2026-10-30 Day14 提交前 | **453 passed / 12 skipped，23.34s** | 完整标准重新通过；dotenv/外部服务连接均 0，无警告或付费调用 |
| 2026-10-29 Day14 迁移前 | 403 passed / 12 skipped，4.11s | 完整标准基线，1 条检查器导入警告 |
| 2026-10-29 Day14 迁移后 | **453 passed / 12 skipped，31.10s** | 完整 backend/tests，最终无警告；dotenv/外部服务连接 0 |
| 2026-10-29 Day14 真实局部 | **3 passed，160.84s** | test_rag_integration + test_rerank_comparison_integration；2 项真实测试和 1 项普通回归 |
| 2026-10-29 Day12 提交前 | 403 passed / 12 skipped，15.93s | 历史标准，含 ReadError 与质量退化普通回归 |
| 2026-10-28 Day12 全部真实 | **413 passed，158.94s** | 最新历史全部真实；本轮没有重跑全部真实 |

真实局部使用 PostgreSQL/Qdrant/本地 BGE/Reranker，LLM 为替身；
真实 LLMClient 有禁止调用守卫，付费尝试和外部连接 0。
本次提交未启动/重启服务、未下载模型；真实局部是 10月29记录。
配置文件在当时局部验收内部只读打开 2 次，
写入 0，凭据没有输出或进入交付。

相同 24 Chunk / 12 正样本 / 3 负样本重新通过严格原基线：
Hybrid Hit@1/Hit@5/MRR@5 为 0.917/1.000/0.944，
Rerank 为 0.917/1.000/0.958；逐题排名、20 候选/0 截断通过。
3 负样本拒答且 LLM 调用 0，没有覆盖 Day12 历史实验 MD/JSON。
不能据此宣称自然长文/表格/多跳的效果或推算新全部真实计数。
临时数据 finally 清理后，独立只读核验 Document/Chunk/临时 collection 均 0。

### 4. 代码位置与精确职责

| 文件/函数 | 当前职责 |
|---|---|
| [state.py](backend/app/agent/state.py)：AgentState、AgentUpdate、AgentContext、initial_agent_state | 六字段 State、局部更新、模式 Context，公共初始状态 True |
| [nodes.py](backend/app/agent/nodes.py)：create_retrieve_node | 单次检索、保留完整 Top5、复用证据门/Prompt/sources、写 PreparedRAG |
| nodes.py：create_generate_node | 固定拒答或 complete/custom stream，复用来源清理、校验非空 |
| nodes.py：StreamControl | Runtime 单次控制，逐 delta 确认/取消，不在 State/Context 中 |
| [graph.py](backend/app/agent/graph.py)：route_retrieval、build_rag_graph | 严格 bool 路由，START→retrieve/generate→END，compile 不调用依赖 |
| [service.py](backend/app/agent/service.py)：RAGGraphRunner.complete/start_stream/stream | invoke、v2 stream 预取、严格事件白名单、安全异常和最终结果映射 |
| service.py：PreparedRAGStream.next_event/cancel/close | 同一 iterator 的 Context/锁、取消和幂等关闭 |
| [rag.py](backend/app/services/rag.py)：RAGService._runner | cached_property 懒编译图；get_rag_service 原 lru_cache 保留 |
| rag.py：prepare/complete/start_stream/stream | 公共问题执行图；旧内部 PreparedRAG 调用复用 retrieve_node/False 分支 |
| [chat.py](backend/app/api/chat.py)：chat、stream_sse、_RAGStreamingResponse | 原 JSON/SSE/错误码、预取后才响应、ASGI 断连清理 |
| [requirements](backend/requirements.txt) | 唯一新增直接依赖 langgraph==1.2.16 |

新增测试：[State](backend/tests/test_agent_state.py)、[节点](backend/tests/test_agent_nodes.py)、
[实际图](backend/tests/test_agent_graph.py)、[执行与关闭](backend/tests/test_agent_service.py)。
既有 [Chat](backend/tests/test_chat.py)、[RAG](backend/tests/test_rag.py)、
[健康检查](backend/tests/test_main.py) 与 [真实 RAG](backend/tests/test_rag_integration.py) 扩展回归；
原有断言保留，真实质量比较测试文件和基线不改。

### 5. 必须保持的契约

State 为 query、retrieved_docs、prepared、answer、tool_calls、needs_retrieval。
Context 仅 response_mode=complete/stream；依赖用工厂闭包，串行局部更新，没有 reducer。
START 按 needs_retrieval 路由：True→retrieve_node→generate_node→END；
False→generate_node→END。公共 /chat 始终 True，HTTP 没有跳过检索参数。
False 无合法 PreparedRAG 则安全失败；tool_calls 始终 ()。

retrieve_node：向量/BM25 各 20 → 等权 RRF60 取20 → 固定 CPU BGE Rerank5 →
原始 vector_score>=0.46 生成证据门。RRF/logit 不作 0.46 门，BM25-only 仍不生成。
无证据精确回复“知识库中没有相关信息”，LLM 零调用。
Prompt 和来源构建复用原函数，sources 只信任后端 metadata，模型伪造引用继续清理。

非流式 graph.invoke 后返回 answer/model/sources。
流式使用 graph.stream(updates+custom, v2)，同一迭代器先预取消费到 retrieve update，
再创建 HTTP 响应；后续只暴露合法 custom delta，内部 updates 不进入 SSE。
成功顺序 delta→sources→[DONE]；LLM 失败仍为原 SSE error 后停止，不发 sources/DONE。
超限 422、内部检索错误 500、非法结果 502、不可用 503 在 SSE 建立前返回；
非流式 LLM 失败 502。未知内部图错误包装固定安全文本，日志不公开 State。

### 6. 流式、惰性与安全决策

D-054：固定版本双节点图，显式条件边与六字段 State/独立 Context，保持 Day14 范围。
D-055：invoke/custom stream，SSE 前预取同一 iterator；否决未检索就响应、完整答案预缓冲、
重复检索和透传内部 update。
D-056：StreamControl 逐 delta 背压与取消，PreparedRAGStream 独立 Context/锁解决跨工作线程，
finally 与 ASGI 取消保护关闭 graph/sanitizer/上游。同步 I/O 阻塞仍受原 60s 默认 timeout 约束。
D-057：每次运行 tracing_context(False)、callbacks=[]；安全异常和日志，不因环境开启导出 State。
D-058：旧内部 prepare/PreparedRAG 复用节点和 False 分支，公共请求始终从 True 运行。

D-001 至 D-053 保留原日范围，不据历史“Day11 不改 Chat”否决后来已授权的 Day12 接入；
全部理由和历史否决见 [DECISIONS](DECISIONS.md)。
get_rag_service 只缓存服务，首次请求才构图；启动和 /health 不构图、不连接服务或加载模型。
没有新增全局运行上下文、持久状态、工具和付费 API 调用。

### 7. 保护文件、依赖与证据位置

2026-10-29 迁移验收：OpenAPI 全 JSON 精确相等，15 个旧模块级 RAG 函数 AST 一致，18 个保护文件起止 SHA256 一致。
2026-10-30 提交整理：PLAN 按用户要求更新，其余 17 项保护文件、16 个已审查实现/测试/依赖文件起止哈希一致。
保护清单和具体哈希见 [机器记录](docs/day14-langgraph-results.json)，包括 PLAN、AGENTS、
main/config、LLM、检索/Embedding/Reranker、独立 rerank API、原 Day12 实验 MD/JSON、
严格质量回归文件和 Compose。
当前 PLAN SHA256 = C1A6DBB5C081C15EA285A2826548D13806B147F2541569EB81017D188FB31099。
原 FDA329ABC06FBDA6B05642832A0386372D06592598106F61270845B0577E9FA1 是 10月29迁移时历史哈希。

Python 3.11.15；langgraph 1.2.16、checkpoint 4.3.1、prebuilt 1.1.1、sdk 0.4.10、
ormsgpack 1.13.0，原有 core 1.4.9/langsmith 0.10.5 未调整。
没有完整 langchain；pip check 输出 No broken requirements found.
依赖包的 checkpoint/prebuilt 名称不代表项目启用了记忆或工具。

Day13 证据目录：
C:\Users\袁伟鑫\AppData\Local\Temp\rag-agent-day13-71af7f75cf91462a8d38247a5b2fa22a；
笔记/图/官方示例 SHA256 见迁移报告。本轮没有重做或永久归档，目录可能被系统清理。
Day14 原日志、检查器、OpenAPI 快照和新实验 JSON：
C:\Users\袁伟鑫\AppData\Local\Temp\rag-agent-day14-feb71aa9c2e74566b33c1213b211cc47；
验收摘要、质量和保护哈希已归档进仓库的 Day14 报告与机器记录。

### 8. 历史失败、规避与尚存边界

2026-10-29 迁移验收没有功能测试失败；当时检查器修正不改变生产契约。
本次提交前完整标准也无失败，以下保留当时检查器问题：
提前 import 导致基线 anyio 重写警告，改为 pytest 后生成 OpenAPI，最终无警告；
临时目录权限错误（PermissionError/WinError 5）通过获准的新独占目录处理；
离线探针曾错误要求 Embedding safetensors/完整 Rerank snapshot，按生产白名单复核后成功；
清理核验曾将 QdrantClient 当 context manager，改为 try/finally close。
图导出先写临时目录再经补丁加入仓库，未放宽权限/模型规则或掩盖测试失败。
更早的 Docker socket、VHDX 与 Day12 下载/ACL 失败原文保留在下方历史附录及
[Docker 恢复记录](docs/docker-desktop-recovery.md)。

尚存：CPU 性能、BM25 全扫描/多 worker、跨库无 outbox/删除同步、
BM25-only 保守门、自然语料评测与同步流 I/O timeout。
没有验证独立后端常驻运行；服务/缓存只在验收时可用，不推断下一会话现状。
GitHub 之后是否变化、Day13 临时包永久归档/计划标记、Day14 推送或合并仍待用户指定。

### 9. 命令、下一步与验收（最多 5 步）

下面仅为入口，不是新会话执行授权。实际本轮使用仓库外隔离检查器，
标准禁用真实集成、dotenv/服务连接，真实局部只允许本地端口与 LLM 替身，
两类均用新独占临时目录、禁用缓存与 LangSmith pytest 插件。

~~~powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pytest backend/tests/test_rag_integration.py backend/tests/test_rerank_comparison_integration.py -v
git --no-optional-locks status --short --branch
git --no-optional-locks rev-parse HEAD
git --no-optional-locks diff --cached --name-only
git --no-optional-locks diff --check
~~~

真实局部需显式 RUN_*_INTEGRATION 五项、HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE；
DAY12_RERANK_REPORT_JSON 只可指向不存在的新路径，不能覆盖历史 JSON。
不把上述裸命令当成具有相同隔离守卫的运行；先按用户动作确认执行范围。

1. 读当前 A/B/C、STATUS/DECISIONS/TODO/AGENTS/README、只读 PLAN、架构与 Day14 报告。
2. 只读核对分支、Day14 提交及其父提交；相关改动应为 0、暂存区应为空，保留排除项和后续用户改动。
3. 对照两节点/预取/关闭与 JSON/SSE，确认 10月30标准 453/12、10月29局部 3、10月28全真实 413 的范围。
4. 复述实现/计划/发布差异、保护哈希、历史附录和未知项，不补全未知事实。
5. 等待用户指定唯一动作；不自动修改 PLAN、安装/测试、操作服务、提交/发布或开始 Day15。

验收：Day14 编排、既有协议与安全门保持，完整标准通过、真实局部通过，
原质量常量和保护文件不变，无付费调用、无凭据/无关文件进入交付；
本提交按用户明确要求收录 Day14，PLAN 五项/日志已勾选；未推送或开始后续日。

## 附录：Day12 历史详细交接（保留当时记录）

> 本附录形成于 Day12 本地提交阶段；其中“当前”“未推送”“Day13 未开始”、旧分支和测试数均指当时。
> Day14 当前状态、远端核验、测试范围和执行规则以本文件 A/B/C 为准；本附录的命令及限制不是本轮执行授权。
> 保留全文是为追溯 D-001 至 D-053、早期失败原文和历史规避，不得据旧文覆盖当前实现或重做已完成内容。

### 1. 项目最终目标与未实现范围

构建用于作品展示、简历和面试的企业知识库RAG Agent：

- FastAPI后端、Streamlit前端；PostgreSQL保存Document/Chunk，Qdrant保存向量。
- 本地BGE Embedding，向量/BM25/Hybrid/RRF/本地CrossEncoder重排。
- OpenAI-compatible LLM生成答案，后端控制可信来源与JSON/SSE。
- 后续LangGraph工具编排、多轮记忆、50条QA评测、trace、前端和完整Docker Compose部署。

当前Day1–12每日任务已完成；Day1–11已形成发布检查点，Day12实现及相关文档纳入本次本地提交，尚未推送。2026-10-29用户确认Day12完成，四项计划和开发日志已标记完成；Day13及以后未开始。LangGraph、记忆、50条自然评测集、trace UI、Streamlit、完整一键部署不能写成已完成。PLAN.md是每日范围基线；其总览把Rerank放在Day7–11/Agent从Day12开始，与逐日Day12 Rerank、Day13 LangGraph有旧表述差异。按逐日安排理解；Day12完成标记已于上一轮按用户授权更新。本次只同步PLAN中Git状态说明，不改已完成标记、总览或后续日程。

### 2. 当前Git与工作区（2026-10-29 Day12本地提交检查点）

| 项目 | 精确状态 |
|---|---|
| 终端/目录 | PowerShell，D:\2019\rag-agent |
| 当前分支 | codex/day12-rerank |
| 最近有效提交/HEAD | 本Day12提交；用git log -1 --format=%H取得精确哈希 |
| 提交说明 | feat: complete Day 12 rerank retrieval |
| 本地origin/master tracking ref | b68b590c8262eb568a371c895e4f7033456d045c |
| 发布历史 | Day11于2026-10-28独立提交、推送并通过GitHub实时查询核验 |
| GitHub现在的实时HEAD | 待确认；2026-10-29未查询，tracking ref不能替代实时远端 |
| Day12发布状态 | 本提交收录完整实现与文档，尚未推送或合并 |
| 暂存区 | 提交完成后应为空，以git diff --cached --name-only核验 |
| 本提交相关文件 | 26项：提交前17个tracked修改、9个相关untracked；提交后相关改动应为0 |
| PLAN | Day1–12任务已勾选；Day12四项及日志于2026-10-29按用户确认标记完成；Day13未开始 |
| PLAN SHA256 | FDA329ABC06FBDA6B05642832A0386372D06592598106F61270845B0577E9FA1 |

近期提交：

~~~text
a614a365ff52b8fa087ce651614c23e2e1017c0b  feat: complete Day 10 BM25 retrieval
98ff9d3860e845f47df91e366811663c71a0ec5d  docs: mark Day 10 complete in plan
b68b590c8262eb568a371c895e4f7033456d045c  feat: complete Day 11 hybrid retrieval
~~~

以下路径相对仓库根目录；不能使用git add .，不能重置既有工作区。

提交前17个tracked修改（均纳入本提交）：

~~~text
DECISIONS.md
HANDOFF.md
PLAN.md
README.md
STATUS.md
TODO.md
backend/app/api/chat.py
backend/app/core/config.py
backend/app/main.py
backend/app/services/hybrid.py
backend/app/services/rag.py
backend/tests/test_chat.py
backend/tests/test_hybrid.py
backend/tests/test_hybrid_api.py
backend/tests/test_rag.py
backend/tests/test_rag_integration.py
docs/architecture.md
~~~

提交前9个相关untracked（均纳入本提交）：

~~~text
backend/app/api/rerank.py
backend/app/services/reranker.py
backend/tests/test_main.py
backend/tests/test_rerank_api.py
backend/tests/test_rerank_comparison_integration.py
backend/tests/test_reranker.py
backend/tests/test_reranker_integration.py
docs/day12-rerank-comparison.md
docs/day12-rerank-results.json
~~~

无关untracked：.agents/、就业推荐表_完整填充版.pdf。只识别为排除项，不读取、打包或提交。.env、凭据、模型和测试缓存也不进入交付。

上一轮完成状态收口已按用户授权更新PLAN与相关状态；随后保存过六份交接文档。当前用户进一步指定本地提交Day12；本次将上述26项一并收录，并同步八份计划/状态/说明文档。源码/测试、依赖、Compose及原实验JSON保持提交整理起点原样。

### 3. 必须保留的证据差异：后续改动与历史验收

**Day12已由用户确认完成；最近标准403/12通过。401/12与413仍是2026-10-28历史记录，当前全部真实组合未重跑。**

本地文件时间（已转换为Asia/Shanghai）晚于2026-10-28实验报告：

| 文件 | 最后修改时间 | 当前可见实现 |
|---|---|---|
| backend/app/services/reranker.py | 2026-10-29 01:17:59 | 瞬时下载重试包括httpx.ReadError |
| backend/tests/test_reranker.py | 2026-10-29 01:02:00 | ReadError中断响应的指数退避回归 |
| backend/tests/test_rerank_comparison_integration.py | 2026-10-29 01:04:33 | 严格质量基线与“全部正确项掉到第5”的退化回归 |
| docs/day12-rerank-results.json | 2026-10-28 17:05:12 | 原24 Chunk/12题实验数据 |

时间戳本身不能证明作者或审查。上述后续回归已随2026-10-29完成状态收口时的标准套件实际通过：403 passed、12 skipped，45.66s。变更作者/独立审查记录未补查；全部真实组合本次未重跑。保留这些既有修复，不推算新的全真实通过数。

2026-10-29交接起点的SHA256，供新会话定位精确快照；这些不是2026-10-28测试版本的历史哈希：

| 文件 | SHA256 |
|---|---|
| backend/app/services/reranker.py | F90B512DC11DA898636C1414111671EEA086393D1BC96DD655FFCD77C0AA4F86 |
| backend/tests/test_rerank_comparison_integration.py | E48B06AC09288E588D9C12A0F2F809AC3406085CF8BA088CDEA02AC5247975DF |
| backend/tests/test_reranker.py | 5D95AF897B0E6F614A958BAA1CE9300676253E307A00B75F0E94C1F91E8202E6 |
| docs/day12-rerank-results.json | 43FC6D0AD73DCA87DEA7E94B3CF15AB2F9D91F9E2D786672897C9247E31C7538 |

### 4. 已完成内容与当前数据流

| 阶段 | 已有实现 |
|---|---|
| Day1–3 | 模块化FastAPI、独立配置/日志、OpenAI-compatible LLM、JSON/SSE |
| Day4–5 | PDF/MD/TXT上传解析、分页token切分、PostgreSQL Document/Chunk同事务持久化 |
| Day6 | 固定本地BGE、CPU、512维归一化、批量≤32、独立BGE tokenizer预检 |
| Day7 | unnamed 512/Cosine Qdrant、UUID幂等显式索引、向量检索 |
| Day8 | 生成层证据门、结构化Prompt、后端sources、拒答、模型伪造引用清理 |
| Day9 | 严格top_k 1..20、Qdrant内单doc_id过滤、JSONL、真实chunk size对比 |
| Day10 | 独立BM25、确定性混合分词、PostgreSQL指纹快照刷新、token overlap门控 |
| Day11 | 独立Hybrid、标准等权RRF60、身份/payload一致性、安全失败、真实三路对比 |
| Day12工作区 | 本地重排、固定Hybrid20→Rerank5、独立接口、Chat接入、名次日志和真实对比 |

当前调用链：

~~~text
POST /chat
 → RAGService.prepare()
 → RerankedRetrievalService.search(query)
 → HybridRetrievalService.search(top_k=20)
     → 向量Top20 → BM25 Top20（同步顺序）
     → 一基排名等权RRF60 → Hybrid Top20
 → RerankerService.rerank()
     → query-passage成对预检 → passage-only截断 → 原始logit → Top5
 → 只保留原始vector_score >= RAG门槛（默认0.46）的生成证据
     → 无证据：固定拒答，不调用LLM
     → 有证据：system规则 + user JSON Context → LLM → 后端sources
 → JSON，或SSE delta → sources → [DONE]
~~~

上传不会自动Embedding/写Qdrant，必须显式索引。PostgreSQL与Qdrant没有跨存储事务、outbox、自动删除同步或一致性修复。启动与GET /health不初始化或探测数据库、Qdrant、BGE、Reranker或LLM。

### 5. 接口、请求与响应契约

| 方法与路径 | 关键输入 | 当前行为 |
|---|---|---|
| GET /health | 无 | 200，{"status":"ok"}，仅进程存活 |
| POST /documents/upload | multipart字段file | PDF/MD/TXT，成功201；20MiB，PDF≤500页 |
| POST /retrieval/search | query/top_k/doc_id | score为Cosine；不返回向量 |
| POST /retrieval/bm25/search | 同共享请求 | score为raw BM25；无token重合为空 |
| POST /retrieval/hybrid/search | 同共享请求 | 两路各20，RRF融合后截取top_k；score为RRF |
| POST /retrieval/rerank/search | 仅query及可选doc_id | 固定Hybrid20→Rerank5；score为原始logit，含前后名次 |
| POST /chat | message/stream | JSON answer/model/sources，或SSE；外部形状保留 |

共享RetrievalSearchRequest位于backend/app/api/retrieval.py：query strip后1..4096字符；top_k为严格整数1..20，默认5；doc_id为单UUID或null；extra="forbid"。拒绝bool、字符串、浮点、null top_k及0/21。

RerankSearchRequest位于backend/app/api/rerank.py：query同样1..4096，doc_id同上，extra="forbid"；不接受top_k、candidate_k、mode、权重或rank常数。

共享Chunk字段为chunk_id、doc_id、chunk_index、content、page、filename、metadata、score。Rerank响应在其上增加hybrid_rank、rerank_rank、rank_change，外层仍为{"results":[...]}。vector_score、bm25_score、hybrid_score及两路内部rank不进入Rerank HTTP；Hybrid HTTP也不暴露新增raw score。合法但无匹配doc_id是200空数组，不引入404。候选≥5时返回5，不足5返回实际数量。

~~~json
{"query":"VPN故障联系谁？","doc_id":null}
~~~

分数不可混用：Cosine、BM25、RRF、logit有不同量纲；原始logit不是概率，不直接用于0.46。BM25-only候选可出现在重排调试API，缺少可靠vector_score时不能作为Chat生成证据。

Rerank安全错误：

| HTTP | 条件 | detail |
|---|---|---|
| 422 | 非法请求、BGE或Reranker query超限 | 模型超限为The rerank query exceeds the model input limit. |
| 500 | BM25内部索引、Hybrid/Reranker内部错误 | The rerank retrieval service failed. |
| 502 | Qdrant/Hybrid/Reranker非法结果、重复ID、payload冲突 | The rerank retrieval service returned an invalid result. |
| 503 | 配置或模型/分支不可用 | The rerank retrieval service is unavailable. |

Chat检索在SSE响应建立前完成。LLM普通失败安全502；已经开始的流失败发送error后停止，不发送sources/[DONE]。成功含固定拒答的流均为delta→sources→[DONE]。sources从实际Context按filename/page去重，不从模型自由文本解析。

### 6. 模型、参数、数据结构与排序

Embedding：BAAI/bge-small-zh-v1.5，revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4，CPU、512维归一化、每批≤32。查询只添加一次instruction：

~~~text
为这个句子生成表示以用于检索相关文章：
~~~

文档直接编码。BGE自己的512 token上限包含特殊token，不能用o200k长度替代预检。

Reranker：BAAI/bge-reranker-base，revision 2cfc18c9415c912f9d8155881c133215df768a70；CPU；max_length=512；默认batch_size=4，允许1..8；RERANKER_配置前缀，布尔batch被拒绝。cache_dir相对PROJECT_ROOT解析，默认data/models；download_max_retries默认3、上限3，退避基准1秒。现有sentence-transformers==5.3.0、qdrant-client==1.18.0、rank-bm25==0.2.2，无Day12新增依赖。Python规则3.11，最近实际测试版本3.11.15。

限定六个下载文件：

~~~text
config.json
model.safetensors
sentencepiece.bpe.model
special_tokens_map.json
tokenizer.json
tokenizer_config.json
~~~

token=False匿名；缓存优先，缺失再按固定revision下载；六文件均需存在且非空。只对当前实现的httpx.ConnectError、httpx.ReadError、httpx.TimeoutException及HfHubHTTPError的429/5xx执行有限重试，永久错误不重试。首次加最多3次重试，默认退避1/2/4秒。空候选不下载或载入。

CrossEncoder仅从本地snapshot加载：local_files_only=True、trust_remote_code=False、model_kwargs={"use_safetensors":True}，设备CPU，activation_fn=Identity()，要求num_labels=1。predict显式Identity、apply_softmax=False、不显示进度条。

完整query的无特殊token长度加成对特殊token数>=512时拒绝，为passage留空间；不通过截query绕过限制。先按无截断成对长度计算truncated_candidate_count；PassageOnlyTokenizer将predict内部truncation=True替换为only_second/max_length512，不使用解码后重编码猜测长度。

Hybrid融合以Chunk UUID聚合，分支内重复ID拒绝；跨路同ID的doc_id、chunk_index、content、page、filename、metadata类型/值必须一致，true/1/1.0不能互换。允许单路独有项，但任一路失败整体失败。等权Σ1/(60+rank)，rank一基；按(-rrf_score, best_rank, doc_id, chunk_index, chunk_id)稳定排序，raw score不参与。

RerankedChunk内部字段：共享Chunk字段及score=logit、hybrid_score、hybrid_rank、rerank_rank、rank_change、vector_score、vector_rank、bm25_rank。RerankOutcome.results为Top5 tuple，movements为所有候选的RankMovement tuple；另有candidate_count、truncated_candidate_count、model_load_seconds、inference_seconds。

重排按(-logit, hybrid_rank, doc_id, chunk_index, chunk_id)排序，rank_change=hybrid_rank-rerank_rank，正数为升位。分数按候选位置映射，不用正文作键；校验数量、ID唯一和有限分数，不修改输入metadata。生产工厂与每实例锁保持惰性、首次装载复用；同实例推理经锁串行。

### 7. 精确代码位置与已涉及函数

行号为2026-10-29只读快照，未来改动后以符号名为准。

| 文件 / 位置 | 函数、类型或修改点 |
|---|---|
| backend/app/services/reranker.py:122 | ensure_reranker_snapshot；_snapshot_complete；下载白名单/缓存/有限重试 |
| backend/app/services/reranker.py:180 | PassageOnlyTokenizer.__call__，显式only_second |
| backend/app/services/reranker.py:196 | load_reranker_model，安全本地CrossEncoder |
| backend/app/services/reranker.py:228 | rank_candidates，位置映射、稳定排序、Top5与完整movement |
| backend/app/services/reranker.py:299 | RerankerService；rerank在319，懒加载、token预检、predict与耗时 |
| backend/app/services/reranker.py:404 | RerankedRetrievalService；search在413，固定20→5与安全JSONL |
| backend/app/services/reranker.py:452 | get_reranked_retrieval_service，lru_cache惰性工厂 |
| backend/app/services/reranker.py:46–104 | RerankerError/Unavailable/Input/ResultError；CrossEncoderModel；RerankedChunk/RankMovement/RerankOutcome |
| backend/app/api/rerank.py:26/48/57 | RerankSearchRequest；require_reranked_retrieval_service；search_reranked；响应模型 |
| backend/app/core/config.py:208 | RerankerSettings/get_reranker_settings，固定revision、CPU、长度、batch与路径 |
| backend/app/services/hybrid.py | HybridRetrievedChunk新增vector_score/bm25_score；_RankedPayload.branch_score、_validated_payload有限校验；reciprocal_rank_fusion保留raw证据；_same_payload仍不比较raw score |
| backend/app/services/rag.py:97/166/472 | select_relevant_chunks改用vector_score；RAGService.prepare读取outcome.results；get_rag_service切换重排工厂；build_sources/build_rag_messages及引用sanitizer保留 |
| backend/app/api/chat.py:107 | chat补齐BM25/Hybrid/Reranker错误；require_rag_service、stream_sse和_source_dict保留外部格式 |
| backend/app/main.py:36 | create_app只注册一次rerank_router；lifespan仍不载模型/探测依赖 |

前序支撑文件：

- backend/app/api/retrieval.py：RetrievalSearchRequest、RetrievedChunkResponse、RetrievalSearchResponse。
- backend/app/services/retrieval.py：RetrievalService.search/get_retrieval_service，TopK默认5、上限20。
- backend/app/services/bm25.py：tokenize_bm25、load_bm25_chunks、build_corpus_fingerprint、build_bm25_snapshot、BM25Service.search/_refresh_snapshot、get_bm25_service。
- backend/app/services/qdrant_store.py：QdrantVectorStore.initialize_collection/validate_collection/upsert_chunks/search、_parse_scored_point。
- backend/app/core/database.py：get_engine/get_session_factory；惰性同步SQLAlchemy。
- backend/app/core/logging.py：JSONL_LOG_MARKER、configure_logging。
- backend/app/commands/index_document.py、init_qdrant.py、embed_document.py、backend/app/models/init_db.py：显式存储/索引操作入口。

### 8. 测试文件、回归与当前质量基线

| 文件 | 关键覆盖 |
|---|---|
| backend/tests/test_reranker.py | 假模型、0/1/4/5/20候选、稳定平局、唯一性、有限值、完整query/显式passage截断、模型复用、安全下载/加载/推理错误与日志 |
| backend/tests/test_rerank_api.py | 固定请求、Top5/名次、doc_id传递、隐藏内部字段、422/500/502/503、OpenAPI |
| backend/tests/test_main.py | 非法Reranker配置不影响health、禁止重复Operation ID |
| backend/tests/test_reranker_integration.py | test_real_pinned_cpu_model_scores_pairs_and_records_truncation；RUN_RERANKER_INTEGRATION=1 |
| backend/tests/test_rerank_comparison_integration.py | test_real_hybrid_rerank_quality_and_chat_contract；同语料真实比较、API/doc_id/空结果、Chat JSON/SSE/拒答和finally清理 |
| backend/tests/test_hybrid.py、test_hybrid_api.py | raw score保留但不影响RRF/HTTP；身份/payload一致性、两路各20、日志 |
| backend/tests/test_rag.py、test_chat.py | 默认工厂新链路；vector_score门、BM25-only排除；来源与SSE、拒答及错误 |
| backend/tests/test_rag_integration.py | 真实上传→显式索引→Hybrid/Rerank→Chat，LLM替身；现增加Reranker真实开关 |
| backend/tests/day9_tuning_corpus.py、day10_bm25_cases.py | 固定自撰语料、COMPARISON_CASES、NEGATIVE_QUESTIONS，不现场改样本 |

本轮额外核对到的后续回归：

1. backend/tests/test_reranker.py:220，test_download_retries_read_errors_with_exponential_backoff。构造LocalEntryNotFoundError后反复httpx.ReadError，断言一次本地+四次在线尝试、退避[1.0,2.0,4.0]、安全错误无私有信息。这是测试构造，不是已获取的真实ReadError故障日志。
2. backend/tests/test_rerank_comparison_integration.py:59，_assert_quality_acceptance。当前严格校验EXPECTED_HYBRID_METRICS、EXPECTED_RERANK_METRICS、EXPECTED_HYBRID_RANKS、EXPECTED_RERANK_RANKS、每题20候选和0截断。
3. 同文件:71，test_quality_acceptance_rejects_all_correct_results_falling_to_fifth。普通回归构造所有正确项掉到第5，尽管Hit@5=1，Hit@1=0/MRR=0.2仍必须失败。真实测试单独用requires_real_stack标记；不能误把普通回归也整模块跳过。

当前常量为Hybrid 0.917/1.000/0.944，Rerank 0.917/1.000/0.958；
Hybrid逐题首次命中(1,1,1,1,3,1,1,1,1,1,1,1)，Rerank为(1,1,1,1,2,1,1,1,1,1,1,1)。
这些是固定受控语料的回归基线，不是重新测量结果。不能降低断言、删除失败问题或换数据来强行通过。上述后续普通回归已随2026-10-29标准套件通过；本次没有复跑真实集成。

### 9. 带日期的测试证据与失败状态

| 日期/版本阶段 | 实际记录 | 边界 |
|---|---|---|
| Day10历史 | 标准264 passed/9 skipped；全真实273 passed | 前序发布证据 |
| 2026-10-27 Day11实现 | 标准333/10；全真实343 passed in 35.42s | 旧版本，不代替Day12 |
| 2026-10-28 Day11收口 | 标准335/10 in 57.73s | 当时阶段记录 |
| 2026-10-28 Day11发布前 | 335/10 in 1333.56s | 之后独立提交并推送b68b590 |
| 2026-10-28 Day12初次定向 | 157 passed，2 errors，1 warning | 临时目录父路径/重复路由，后续已修复 |
| 2026-10-28 Day12最终标准 | 401 passed/12 skipped in 17.93s | 当时标准套件，真实集成关闭 |
| 2026-10-28 Day12全部真实 | 413 passed in 158.94s，无跳过 | PostgreSQL/Qdrant/BGE/Reranker真实，LLM替身 |
| 2026-10-29完成状态更新 | **403 passed/12 skipped in 45.66s** | 标准套件、假模型/假LLM；真实开关关闭，无付费调用 |
| 2026-10-29历史完整交接 | 仅本地Git/文件核对和文档保存 | 当时未重复测试、服务、模型、实时远端或Git写操作 |
| 2026-10-29本地提交首次标准 | 322 passed/12 skipped/81 errors in 47.57s | 新独占临时目录创建WinError5；权限导致setup错误，未改代码 |
| 2026-10-29本地提交前重跑 | **403 passed/12 skipped in 15.93s** | 取得本次临时目录写权限后，新独占目录重跑通过；真实开关全关、模型离线、无付费调用 |

当前标准套件实际结果403 passed/12 skipped，失败0，覆盖两项后续普通回归。最新全真实记录仍是2026-10-28的413；本次未重跑真实组合，不把旧结果写成今日全真实重新通过。

pip check此前通过。2026-10-28全量后独立只读检查Day12临时Document=0、Chunk=0、day12_rerank_compare_* collection=0；今天未连接服务复查。最新标准命令禁用langsmith_plugin隔离无关外部跟踪，anyio保留；初次较慢耗时原因未证实，不把插件断言为唯一根因。

### 10. 历史真实质量、性能与局限

2026-10-28：自撰8页手册、500/100 o200k_base、相同24 Chunk ID/payload、12正样本（精确/语义/混合各4）+3负样本。NFKC+strip后包含固定expected_phrase是唯一命中判据。

| 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---:|---:|---:|
| 向量（Day11） | 0.750 | 0.917 | 0.812 |
| BM25（Day11） | 0.833 | 1.000 | 0.882 |
| Hybrid | 0.917 | 1.000 | 0.944 |
| Hybrid+Rerank | 0.917 | 1.000 | 0.958 |

Rerank的Hit@1未提升，远程接入目标3→2，首位仍错。保留无关候选升位例：query=6203时年假页chunk_index=5从17升到2，正确目标仍在1。不能用首次命中指标声称Top5每条均正确。
3负样本经完整RAG向量证据门后固定拒答率1.0，LLM调用0；这不是重排调试接口自身的拒答能力。

模型新实例首次装载2.8316131s，首次predict6.5616883s，同一首题热predict6.2910249s；12正样本平均6.3918615s。权重/依赖已缓存，同pytest进程，OS页缓存可能预热；不是系统重启后的物理冷启动，不含下载/HTTP全程或LLM。正样本累计截断0；独立真实超长passage测试验证截断1。

完整逐题和原始logit：[Day12报告](docs/day12-rerank-comparison.md)、[机器结果](docs/day12-rerank-results.json)。原实验JSON与下文指标保持2026-10-28原证据；MD仅同步完成/提交状态，不覆盖实验数据。

局限：合成审计标识被BGE特殊压缩；小样本不代表自然长文、表格/多跳。CPU约六秒且同实例串行，未做batch2/4/8、p50/p95/QPS。BM25全扫描/多worker快照、跨库存储无同步仍在；BM25-only生成证据保守排除可能损失召回。未据此更改切分、阈值、模型或权重。

### 11. 已确认决策、原因与已否决方案

DECISIONS.md保留D-001至D-053。本轮不新增或推翻决策。

| 决策 | 结论与原因 |
|---|---|
| D-001/D-014 | 按每日范围、建立文档检查点，防止跨Day与把计划当实现 |
| D-016/D-022 | 同步SQLAlchemy；Document先flush再Chunk flush，避免真实PostgreSQL外键顺序失败 |
| D-019/D-020 | 固定o200k_base、按页500/100，保证可复现token基准和引用页码 |
| D-024/D-025 | 固定CPU BGE；使用自己的tokenizer预检，禁止静默截文档 |
| D-028/D-029 | 显式索引、Point ID=Chunk UUID、512/Cosine；隔离上传失败并支持幂等 |
| D-032–D-037 | RAG生成证据门、system规则/user JSON不可信Context、后端sources/拒答/引用清理 |
| D-039/D-040 | 严格top_k；Qdrant内部先doc_id过滤再取limit、返回再校验 |
| D-041 | JSONL/human互斥，避免截断重复；哈希不等于匿名化 |
| D-043–D-045 | 中英混合分词、query去重/corpus保留TF、指纹原子替换、刷新失败不使用旧快照、token overlap保留真实零/负分 |
| D-046–D-049 | 独立BM25/Hybrid、排名比较/RRF60、UUID与payload冲突失败，不将Cosine和BM25直接混分 |
| D-050 | 固定本地CPU/safetensors Reranker、惰性、安全有限下载，避免额外供应商、文档外发和费用 |
| D-051 | Identity原始logit、全20再取5、稳定排序与完整movement，不提前丢掉纠错候选 |
| D-052 | 包装predict tokenizer仅截passage，保护query；仅max_length不足，解码再编码不可靠 |
| D-053 | Day12独立授权接入Chat，保留原始vector_score证据门；认可BM25-only保守排除的召回代价 |

D-049“Day11不改Chat、不做Rerank”是历史日范围；D-053按用户Day12授权扩展，不能误认为矛盾而回滚新链路。

明确不采用：API Rerank（Cohere/硅基流动）、新增OpenAI/千问Key、默认Sigmoid当概率、RRF/logit套0.46、分数直接相加/归一化相加、加权RRF、统一mode、问题类型路由、静默降级、正文/filename/page去重、Hybrid先截5再重排、静默双边截断、按小样本反复调参。以上含已否决/未选择方案，不声称全部做过失败实验。

### 12. 实际失败尝试、修复与当前错误/日志

已执行但失败/不足的尝试：

| 尝试 | 结果与已知处理 |
|---|---|
| 受限网络安装rank-bm25 | 先失败，获网络允许后成功；不是版本冲突 |
| 用完整复合编号断言BM25只命中一个Chunk | tokenizer保留共享组成token；改用唯一数字验证刷新，未改分词 |
| 默认TEMP/仓库pytest临时目录 | 历史WinError5；使用Public独占basetemp，未修复全局ACL |
| Day12新basetemp父目录未准备 | 两个tmp_path setup为WinError3；先建父目录后最终套件通过 |
| Day12重复注册rerank_router | Duplicate Operation ID警告；移除重复并新增回归 |
| Xet首次下载大权重 | 未及时完成后停止；标准HTTPS+超时下载同一固定safetensors成功；没有完整Xet失败trace，不能认定具体根因 |
| GitHub代理/直连 | 先连接失败/connection reset，2026-10-28后来推送成功；今天连接状态待确认 |
| 仅重命名Docker/run、禁用AI/model-runner、单独升级4.49→4.97 | 仍有另一Secrets Engine socket错误，均非根治 |
| 管理员/cipher /d/WSL目录访问 | 未形成默认路径修复；EFS/中文用户名只是观察，不是已证实根因 |
| 升级后沿用C盘数据盘 | 引擎启动但原容器不可见；恢复D盘CustomWslDistroDir后找回旧数据 |
| 内存Qdrant试验 | 仅初步证据，不代替后来的真实服务验收 |

历史错误原文（不是2026-10-29新采集日志）：

~~~text
fatal: unable to access 'https://github.com/itysrw/rag-agent.git/': Failed to connect to github.com port 443 after 21063 ms: Could not connect to server
fatal: unable to access 'https://github.com/itysrw/rag-agent.git/': Recv failure: Connection was reset
~~~

~~~text
FileNotFoundError: [WinError 3] 系统找不到指定的路径:
'C:\Users\Public\codex-pytest-rag-agent-day12\unit-20261028-01'

UserWarning: Duplicate Operation ID search_reranked_retrieval_rerank_search_post
for function search_reranked at D:\2019\rag-agent\backend\app\api\rerank.py
~~~

~~~text
starting services: initializing Inference manager: listening on unix://C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: remove C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: The file cannot be accessed by the system. (listener: The filename, directory name, or volume label syntax is incorrect.)
~~~

~~~text
starting services: initializing Secrets Engine: listening on unix://C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock: rename C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock.stale: The file cannot be accessed by the system. (listener: The file cannot be accessed by the system.)
~~~

项目日志由backend/app/core/logging.py的configure_logging输出stderr，无固定项目日志文件。
机器事件retrieval_search_completed、bm25_search_completed、hybrid_search_completed、rerank_search_completed按JSONL_LOG_MARKER走专用{message} handler，human handler排除标记。正常新链路可产生两条分支+Hybrid+Rerank共4条完成日志，拒答不意味着没有检索日志。
Rerank事件含query_sha256/query_len、candidate_k/final_k、filter_doc_id、数量/截断、load/inference秒数、movements；不含query、正文、metadata、文件名或raw分支score。旧分支日志仍含各自score/部分来源字段，不能说所有日志均不含raw分数。
序列化安全错误字符串为Rerank search event serialization failed.；它不丢弃成功结果。Hybrid对应Hybrid search event serialization failed.。异常链保留，不向HTTP暴露原始私有错误。

2026-10-29没有新增测试/运行时失败日志报告；当前是否有错误**待确认**，不能由历史成功推断现在健康，也不把外部socket问题归因于Reranker代码。

### 13. Docker规避、外部文件与运行状态

2026-10-28最后确认PostgreSQL running/healthy、Qdrant running，未重启；模型与Chat接口通过TestClient+真实依赖验证。2026-10-29 Docker/容器/独立后端状态均待确认，不探测、不重启。
历史Docker Desktop安装4.97.0.244584、最后验证Engine29.9.2；不是今天重新查版本。

仓库外历史已验证规避（本轮未执行，也未重新查文件）：

- D:\Docker\Start-DockerDesktop.ps1（上次核验2378字节）；启动前须无Docker进程，不强杀。
- 只为新Docker进程设置LOCALAPPDATA=D:\Docker\codex-runtime-20261027，恢复调用shell原值；不改系统/用户环境变量，沿用原Roaming配置。
- 仅在专用路径将全零字节端点的Docker/run和docker-secrets-engine目录重命名保留；有非零文件、子目录或链接则停止，不删除数据。
- 原盘D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx；
  完整停机备份D:\Docker\docker_data.codex-pre-recovery-20261027.vhdx，5,602,541,568字节，恢复前与源盘SHA256一致（历史记录，今天未重算）。
- CustomWslDistroDir=D:\Docker\DockerDesktopWSL已恢复。
- 原配置备份C:\Users\袁伟鑫\AppData\Roaming\Docker\settings-store.codex-backup-20261027.json；
  升级后备份D:\Docker\settings-store.codex-post-upgrade-20261027.json。
- 默认日志目录C:\Users\袁伟鑫\AppData\Local\Docker\log\host；
  规避后D:\Docker\codex-runtime-20261027\Docker\log\host，旧错误曾在com.docker.backend.exe.log。
- 不批量输出日志，不读取Secrets Engine凭据存储，不上传诊断。没有factory reset、WSL unregister、prune或数据库覆盖。
- 脚本/备份不在Git，data/models也被忽略；复制仓库不等于拥有运行时与备份，异机可用性待确认。

详见[Docker恢复](docs/docker-desktop-recovery.md)。默认socket根因未修复，EFS/ReparsePoint/用户名等不能当作已证实根因。

### 14. 启动、索引、测试和核验命令

以下为仓库根目录的恢复参考，**不是暂停阶段的执行授权**。安装、服务、真实验收、付费LLM、Git发布分别由用户指定动作决定。

安装与后端：

~~~powershell
Set-Location -LiteralPath 'D:\2019\rag-agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
~~~

上述后端默认可访问http://127.0.0.1:8000/docs；这不表示当前已有服务启动。LLMKey只用于已有生成链路，不参与本地Embedding/Reranker。禁止直接查看或输出.env。

服务恢复（只有用户指定且确认引擎未在正常运行后）：

~~~powershell
& 'D:\Docker\Start-DockerDesktop.ps1'
docker start rag-agent-postgres-1 rag-agent-qdrant
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' rag-agent-postgres-1 rag-agent-qdrant
~~~

Compose当前只编排PostgreSQL。新环境才显式建表；已有环境只读恢复不建表、不初始化collection：

~~~powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m backend.app.models.init_db
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
~~~

<UUID>替换为用户指定已有文档，不能自动索引所有文档。Embedding-only命令为
.\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>，
只产生内存向量。Qdrant镜像qdrant/qdrant:v1.18.1、本机REST6333、卷rag-agent-qdrant-data；
正式collection默认documents，unnamed512/Cosine，不自动recreate。

AGENTS通用测试：
.\.venv\Scripts\python.exe -m pytest backend/tests -v

本机隔离标准测试模板（新GUID避免清理既有目录，Public父路径可能需运行环境批准）：

~~~powershell
$rerankTestRoot='C:\Users\Public\codex-pytest-rag-agent-day12'
New-Item -ItemType Directory -Path $rerankTestRoot -Force | Out-Null
$rerankTestRun=Join-Path $rerankTestRoot ('verify-' + [guid]::NewGuid().ToString('N'))
$env:RUN_POSTGRES_INTEGRATION='0'
$env:RUN_QDRANT_INTEGRATION='0'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='0'
$env:RUN_RAG_INTEGRATION='0'
$env:RUN_RERANKER_INTEGRATION='0'
$env:LANGSMITH_TRACING='false'
$env:LANGCHAIN_TRACING_V2='false'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=$rerankTestRun -p no:cacheprovider -p no:langsmith_plugin
~~~

若以后唯一任务是核验后续回归，两个定向入口为：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_reranker.py::test_download_retries_read_errors_with_exponential_backoff backend/tests/test_rerank_comparison_integration.py::test_quality_acceptance_rejects_all_correct_results_falling_to_fifth -v --basetemp=$rerankTestRun -p no:cacheprovider -p no:langsmith_plugin
~~~

定向与全量必须使用不同新basetemp；pytest可清理自己的目录，不复用未知路径。不递归删除Public、仓库、模型/测试缓存。上例变量先用同一准备模板但为本次调用生成新GUID。

完整真实验收：准备好本地模型缓存及真实服务，将五个RUN_*开关全部设1，离线标记设1，生成新的独占basetemp后执行全量：

~~~powershell
$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
$env:RUN_RAG_INTEGRATION='1'
$env:RUN_RERANKER_INTEGRATION='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v --basetemp=$rerankTestRun -p no:cacheprovider -p no:langsmith_plugin
~~~

单独真实模型为backend/tests/test_reranker_integration.py；三阶段对比为backend/tests/test_rerank_comparison_integration.py。后者需PostgreSQL/Qdrant/BGE/Reranker四开关；原test_rag_integration.py还需RAG开关。LLM仍为替身，真实DeepSeek不进入标准或全真实pytest，付费冒烟另需用户授权。

2026-10-29最近一次提交前标准回归使用上述隔离模板，basetemp前缀为C:\Users\Public\codex-pytest-rag-agent-day12\commit-20261029-<guid>，实际403/12、15.93s；另显式HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1、PYTHONDONTWRITEBYTECODE=1。此前完成状态收口的status-closeout-20261029-<guid>为403/12、45.66s。

2026-10-28历史标准的实际basetemp为
C:\Users\Public\codex-pytest-rag-agent-day12\standard-final-20261028-04，结果401/12；
全真实为...\all-real-20261028-03，结果413。这里只记录路径，禁止据此读取或清理历史测试缓存。

DAY12_RERANK_REPORT_JSON是显式可选输出：只指向不存在的新JSON路径，测试以open("x")创建，不覆盖docs/day12-rerank-results.json。未设置时仅输出DAY12_RERANK_COMPARISON_RESULT。真实模型测试输出DAY12_RERANKER_MODEL_RESULT。对比创建day12_rerank_compare_<uuid> collection与day12-rerank-comparison-handbook.txt，finally清理并验证，Qdrant清理失败也要执行PostgreSQL清理。

只读Git与静态核验：

~~~powershell
git --no-optional-locks status --short --branch
git --no-optional-locks rev-parse HEAD refs/remotes/origin/master
git --no-optional-locks log -4 --oneline
git --no-optional-locks diff --name-status
git --no-optional-locks diff --cached --name-only
git --no-optional-locks diff -- PLAN.md backend/requirements.txt docker-compose.yml
git --no-optional-locks diff --check
~~~

只有另行指定实时远端动作时才查询git ls-remote origin refs/heads/master；失败标待确认，不用fetch/push或改全局网络设置代替。pip check、compileall是后续指定检查命令，今天未重跑；compileall会写缓存，不能把它当纯只读动作。

### 15. 不可违反的约束与禁止修改的契约

- Python3.11、backend/、公开函数类型提示、pytest，按用户指定Day范围；PLAN修改须单独明确要求。
- 已完成标记保持不变。本次按用户明确要求本地提交Day12，并按AGENTS重跑标准测试。后续未指定动作前不开发、不下载、不操作服务、不推送或合并、不调用付费API、不开始Day13。
- 保留既有修复及三处后续变更；禁止reset --hard、checkout --、prune、自动重建collection、覆盖备份或删除用户数据。
- 不读取/输出/提交.env、Key、数据库密码、Secrets存储；不读取无关.agents/、PDF及模型/测试缓存。
- 后续未有明确变更任务时保护Chat JSON/SSE/sources/引用清理、原始vector_score证据门、检索接口严格请求、既有Hybrid响应、上传/显式索引/Qdrant schema。
- 不使用RRF/logit作为0.46门，不静默降级，不绕过query完整性、safetensors、固定revision或HTTP错误分层。
- 不为通过测试而改语料/expected_phrase/问题顺序/基线、隐藏失败或推算新计数；基线调整必须有独立合理证据与授权。
- PLAN Day12标记已在上一轮按用户授权完成；本次仅同步Git状态说明，不改勾选及后续日程。代码、测试、依赖、Compose、schema和全局设置不改；未来变更仍按用户指定范围，命令样例不是执行许可。

### 16. 当前待完成、待确认与下一步（最多5步）

| 类别 | 项目 |
|---|---|
| 唯一下一步 | 新会话只读恢复当前Day12检查点与历史测试边界 |
| 待用户指定 | Day12推送/合并、按需重新全真实验收或Day13独立任务；本地提交与PLAN完成标记已纳入本检查点 |
| 测试事实 | 后续普通回归已随本次标准403/12通过；作者/独立审查记录未补查，当前全真实组合未重跑 |
| 待确认 | 2026-10-29实时GitHub HEAD、Docker/容器/后端状态、模型缓存可用性、临时资源现状 |
| 完成状态 | Day12功能任务及PLAN四项/日志已完成；本地提交收录26项，尚未推送，Day13未开始 |
| 长期延后 | 自然评测/性能、BM25扩展性、多worker/跨库同步、BM25-only证据、默认socket/ACL |

恢复顺序：

1. 完整阅读本包A/B/C及STATUS/DECISIONS/TODO/AGENTS/README、只读PLAN、架构、实验与指定代码。
2. 只读Git核对本Day12提交/HEAD、Day11 tracking ref、空暂存区与26个提交内文件；相关改动应为0，排除项保留。
3. 对照三处后续改动、当前哈希、历史报告日期和测试基线，未知保持待确认。
4. 复述目标、实现/计划/发布差异、失败与风险，列矛盾及最多5步。
5. 停止并等待用户指定唯一后续动作；再确定最小改动与相应验收，不自行发布或开始Day13。

下一步最小改动：**无代码、计划、Git写入、服务或外部状态变更**。

### 17. 历史完成状态收口记录（2026-10-29，早于完整交接与本地提交）

用户确认Day12已完成，授权勾选PLAN四项任务并更新开发日志。任务完成、Git发布和测试证据分别记录：

- Day1–12任务已完成，Day12四项/日志已勾选；Day13及以后保持未开始。
- 当前codex/day12-rerank，HEAD b68b590，26项相关变更（17 tracked修改/9相关新增），暂存区空；未提交或推送Day12。
- 标准pytest按AGENTS要求实跑403 passed/12 skipped，45.66s；含ReadError重试和质量退化普通回归，无付费API。
- 最近全真实413仍为2026-10-28记录，本次没有操作服务、下载模型或重跑真实集成。
- 本次仅更新八份计划/状态文档；20个受保护文件为17个源码/测试、requirements、Compose、原实验JSON，已核验起止SHA256一致。
- 收尾核对PLAN仅Day12四项、完成确认和日志变化，Day13以后章节不变；文档状态、摘要与启动提示同步，diff与本地链接检查通过。

收尾已核验：八份文档34个本地文件链接无失效；PLAN四项已勾选，Day13及以后任务正文与更新前一致。
此前只读交接阶段曾保留PLAN原样；本次按2026-10-29用户明确授权更新完成标记，历史测试记录保留原日期。

未来若指定重新全真实验收，继续校验固定模型、完整20→5、query/单侧截断、身份/分数/排序、
安全日志、Chat证据门/拒答/来源/JSON/SSE、health惰性、质量基线与临时清理，按实际新结果记录。

### 18. 历史完整交接与验收（2026-10-29，早于本地提交）

以下为本地提交前的历史交接记录，不能替代第2节的当前Git状态。当时仅更新六份核心交接文档，保留PLAN已完成状态和26项相关工作区变更。未重新执行pytest、模型、服务或付费API，未查询实时远端，未暂存/提交/推送，也未开始Day13。

- 本地分支codex/day12-rerank，HEAD与origin/master tracking ref均为b68b590c8262eb568a371c895e4f7033456d045c；17个tracked修改/9个相关新增，暂存区空。
- Day12四项和开发日志已勾选；PLAN SHA256保持038E80307AF66C58C8DB0A4333639DDDC7EA5FAAB61B1F5520E7EC8C4306F25F，Day13未开始。
- 最近标准403/12是2026-10-29完成状态收口时实际执行；最近全真实413是2026-10-28记录，两者没有在本轮交接中再次运行。
- 22个保护文件（17个源码/测试、PLAN、requirements、Compose、实验MD/JSON）起止SHA256一致；不读取凭据、无关.agents/PDF或模型/测试缓存。
- A/B/C、六份状态文档、具体文件/函数/接口/命令、否决原因、失败原文、未知项和最多5步恢复顺序一致；本地文档链接有效。

完成判定：新对话可仅凭本包先准确复述“Day12已完成且已勾选、Git未发布、标准与全真实的日期边界”，未知项不补全，并在用户指定唯一动作前保持仓库和外部状态不变。

### 19. 本次Day12本地提交检查点（2026-10-29）

用户明确要求“提交day12的任务”。本提交收录第2节列出的26个文件，说明为feat: complete Day 12 rerank retrieval；本地提交完成后应没有Day12相关未提交改动，暂存区应为空。精确哈希以git log -1 --format=%H核验，不在提交内容中伪造自身哈希。未推送或合并，未开始Day13。

提交前标准测试403 passed/12 skipped，15.93s。首次受临时目录权限影响的81个setup错误已通过本次测试权限下的新独占目录重跑解决，没有修改代码。原实验JSON和全部源码/测试保持原样；同步八份状态/说明文档。当前全部真实集成仍未重跑，实时远端及运行状态仍待确认。

完成判定：git log显示Day12提交与Day11父提交；本提交路径恰为26项且没有排除项，暂存区为空，相关改动为0；标准403/12和历史全真实413的边界保持清楚。

## B. 300字以内快速恢复摘要

D:\2019\rag-agent，codex/day14-langgraph。本Day14提交收录27项，精确HEAD用git log核验，父3471277；未推送。10月30用户确认审查修复通过，PLAN Day14五项及日志已勾；Day13标记保留。提交前标准453/12（23.34s），10月29真实局部3，全真实仍为10月28的413。双节点图、invoke/stream、SSE前检索与0.46门保留。Day15未开始。相关改动应为0、暂存区应空，排除项保留；只读恢复后等唯一动作。

## C. 新对话的第一条启动提示词

~~~text
这是已有项目的新工作会话，仓库 D:\2019\rag-agent。

当前唯一目标：只读确认 Day14 本地提交检查点与交接包一致；
复述后等待我指定唯一后续动作。下方 Day12 历史附录不是当前状态。

请完整阅读：
1. HANDOFF 当前 A/B/C、STATUS、DECISIONS、TODO、AGENTS、README。
2. PLAN.md（只读）、docs/architecture.md。
3. docs/day14-langgraph-migration.md、day14-langgraph-results.json、day14-agent-graph.mmd。
4. backend/app/agent 下 state/nodes/graph/service/__init__.py，
   backend/app/services/rag.py、backend/app/api/chat.py。
5. 四个 test_agent_*.py、test_chat.py、test_rag.py、test_main.py、test_rag_integration.py，
   只读质量比较测试、Day12 实验 MD/JSON 与 Docker 恢复记录。

已知基线：
- 当前分支 codex/day14-langgraph；本 Day14 本地提交说明为
  feat: complete Day 14 LangGraph RAG migration。
  精确 HEAD 用 git log -1 --format=%H 核验，父提交 34712772b3682d174f459da91100b09f8a2493cc。
- 本提交收录 27 个相关路径，提交前 15 个 tracked 变更/12 个新增；
  提交后相关改动应为 0、暂存区应为空，无关 .agents/ 和 PDF 保留。
- 2026-10-30 用户确认 Day14 审查、测试与修复通过，并明确要求提交代码和同步状态；
  PLAN Day14 五项任务、完成确认和开发日志已更新。Day13 标记和 Day15 以后不改。
- Day14 未推送或合并，Day15 未开始。2026-10-29 曾实时核验 Day12 分支 3471277、
  master b68b590；10月30未复查，下一会话实时远端和运行时状态未知。
- 图为 START 条件 needs_retrieval → retrieve_node/generate_node → END；
  公共 /chat 固定 True、tool_calls=()，没有工具、session、checkpointer 或记忆。
- complete 走 invoke；stream 走 v2 updates+custom，同一迭代器在 retrieve update 后才创建 SSE；
  保留逐段流式、取消关闭、原 HTTP 错误码、JSON/SSE、后端来源和引用清理。
- 底层仍为 Hybrid20→固定 CPU BGE Rerank5→原始 vector_score 0.46；拒答零 LLM。
- 最新标准：2026-10-30 提交前 453 passed/12 skipped（23.34s），无警告，
  dotenv/外部服务连接均 0，无付费 API 调用。
- 最近真实局部：2026-10-29 的 3 passed（160.84s），真实本地检索、LLM 替身；
  同 24 Chunk/12 正样本/3 负样本，Rerank 指标 0.917/1.000/0.958，
  负样本零 LLM，临时 Document/Chunk/collection 当时清理核验均 0。
- 最新全部真实：2026-10-28 的 413 passed（158.94s）；本次提交前未重跑真实集成。
- 迁移时 OpenAPI/15 个原 RAG 函数/18 项保护文件一致的历史证据保留。
  本次 PLAN 按授权更新，其他 17 项保护与 16 个已审查实现/测试/依赖文件未变。
  当前 PLAN SHA256 C1A6DBB5C081C15EA285A2826548D13806B147F2541569EB81017D188FB31099。
- Day13 学习包证据此前已核验，但文件在仓库外临时目录，本次没有重做或永久归档。
  Docker 默认 socket 历史问题未根治，常驻后端和当前服务/缓存未复查。

执行规则：
不重做已完成内容，不擅自推翻 D-001 至 D-058，不推算新全真实结果。
不读取/输出 .env、凭据、无关 .agents/、PDF 或模型/测试缓存。
第一轮不改文件、不安装/测试、不操作服务、不下载、不暂存/提交/推送，
不调用付费 API、不改计划或开始 Day15；命令样例不是执行许可。
先复述目标、完成/PLAN/Git、外部契约、带日期测试、决策与否决、历史规避；
列矛盾或待确认项及最多 5 步，然后等待我指定唯一动作。

验收：
复述与文件及只读 Git 一致；明确 Day14 已勾选、本地已提交但未推送，
区分 10月30标准 453/12、10月29真实局部 3 与10月28历史全真实 413，
保留所有后续用户修改，在我指定动作前不产生仓库或外部状态变更。
~~~
