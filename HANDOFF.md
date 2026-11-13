# 当前检查点：Day19 已确认完成并本地提交

更新时间：2026-11-14（Asia/Shanghai）。仓库 `D:\2019\rag-agent`，分支 `codex/day17-eval-dataset`。用户已确认 Day19 审查、测试与修复通过，授权更新完成状态并本地提交；提交的父提交为 `a3f791bbc5c8116db2b67c7e0b6719c2513b39c0`，当前 HEAD 以 `git rev-parse HEAD` 为准，未推送或合并。`POST /chat` 请求级 trace、`request_logs`、受保护的 `GET /admin/traces`、不付费向量对照及授权的完整 50 题 RAG 对照已完成；Day19 `PLAN.md` 四项与进度表按真实结果更新。本次完整后端 pytest 为 724 passed / 14 skipped / 0 failed，退出码 0。完整对照的最终来源命中依次为 200/40（o200k）7/40、300/60（o200k）6/40、500/100（BGE token）7/40，后者不独占最高、也不是超限的原 o200k 方案；至少 207 次付费请求，精确费用未知。隔离实验数据已清理，原有 Qdrant collection 保留。真实 PostgreSQL 的 Day19 trace 建表和在线运行、服务健康及远端实时状态未在本轮验证。Day13 未勾、Day18 冻结评测未改，Day20 未开始。两项无关未跟踪条目保留。部署要求和边界见 [Day19 可观测性记录](docs/day19-observability.md)，实验见[完整 RAG 对照](docs/day19-full-comparison.md)，当前状态见 [STATUS.md](STATUS.md)。

下方 Day18 A/B/C 和 Day17/Day16 交接保留为历史检查点；旧文“Day19 未开始”只描述当时状态。

用户补充指定不付费离线分块对照，已用冻结六份 PDF 和本地 BGE 完成；原 o200k-token 500/100、800/160 分别有 7、6 个块超输入上限，合格组 200/40、250/50、300/60 的纯向量 Top5 全页命中为 21/40、16/40、22/40。脚本和限制见 [离线分块对照](docs/day19-chunk-comparison.md)。该指标不是完整 RAG `source_hit`；随后另获授权运行完整 RAG 对照，结果与限制见上文。`PLAN.md` 中原本不成立的“500 最高”已改为事实表述。

---

# 历史交接包：Day18 已确认完成并本地提交

更新时间：2026-11-09（Asia/Shanghai）。仓库 D:\2019\rag-agent。本节 A/B/C 是当时的 Day18 恢复入口；下方 Day17 和 2026-11-02 Day16 交接也是历史档案。

## A. 详细交接文档

### 1. 项目最终目标与已完成范围

最终目标是企业知识库 RAG Agent，使用 Python 3.11、FastAPI、LangGraph、PostgreSQL、Qdrant、本地 CPU BGE、BM25/RRF/Rerank 和 DeepSeek compatible LLM，最终交付自然 QA 评测、完整请求 trace、Streamlit 和完整 Docker Compose。PLAN.md 是 25 天范围基线。后端已有上传/分页分块/显式索引、混合检索、单工具问答、PG 业务会话与最近五轮短期记忆。

Day1–12、Day14–18 的相应功能已实现。Day17 已冻结六份 FEMA Ready.gov 英文原版 PDF 与 day17-v1.1 的 50 条人工中文 QA，四类数量为 18/12/10/10；本机六文档 ready、PostgreSQL 25 个 Chunk 与 Qdrant documents 集合 25 个 Point 对应。Day17 四项与完成日志已勾，两次提交已推送。Day13 四项与日志仍未勾。

Day18 已实现评测执行器、人工关键词规则、50 题模拟与真实基线。用户确认审查、测试与修复通过，并授权更新完成状态及本地提交；PLAN.md 的 Day18 五个复选框、完成确认及进度表已更新。Day19 trace 与后续前端/部署未开始，后续开发动作待指定。

### 2. Git、工作区和发布状态

| 项目 | Day18 本地提交检查点 |
|---|---|
| 分支 / HEAD | codex/day17-eval-dataset / 当前本地提交以 `git rev-parse HEAD` 为准 |
| 父提交 | 6f252c24dd42bdd1fc52e4dc7f7beb822ec999de（已推送的 Day17 检查点；其父为 d947eaa31f1789ef112572bcef7241bdbc6b57bb） |
| 本地上游引用 | origin/codex/day17-eval-dataset 仍为 6f252c24dd42bdd1fc52e4dc7f7beb822ec999de；Day18 本地分支领先 1 个提交，本轮未联网确认远端实时头 |
| 本地 master | b68b590c8262eb568a371c895e4f7033456d045c；Day17/18 未合并 |
| 本地提交中的既有文件 | PLAN.md、HANDOFF.md、STATUS.md、DECISIONS.md、TODO.md、README.md、docs/architecture.md、eval/README.md，共 8 份 |
| 本地提交中的新增文件 | eval/eval.py、eval/agent.py、eval/real.py、eval/scoring.py、eval/answer_rubric.json、backend/tests/test_eval_runner.py，共 6 份 |
| 其他未跟踪条目 | 另有 2 项与本任务无关，未读取、未处理 |
| 暂存与发布 | 上述 14 份文件已形成本地提交，暂存区为空；Day18 未推送、建 PR 或合并 |

PLAN.md 只改 Day18 五个勾选、实测引用指标、完成确认和进度表；Day13 与 Day19 状态未改。eval/eval_dataset.jsonl、eval/corpus_manifest.json、eval/corpus/ 和 backend/app/ 相对 Day17 父提交未变。eval/eval_report.md 与 data/eval/day18/ 被 Git 忽略，未随本地提交收录；新对话如不在同一机器，原始基线文件存在性待确认。Day17 已推送的证据来自历史核对及当前本地上游引用。

### 3. 当前实现与精确代码位置

| 文件与符号 | 当前作用 |
|---|---|
| eval/scoring.py:197 load_inputs、:210 score_observation | 校验题集、清单、六份 PDF 与 answer_rubric.json，按事实组、候选和最终页评分 |
| eval/agent.py:40 RequestBudget | 在实际 HTTP 发起前计数，硬上限 100；:88 _Capture 从同次 RerankedRetrievalService.search() 采集 Top 5；:164 EvalAgent 调用 RAGGraphRunner.complete(question, history=()) |
| eval/real.py:90 verify_corpus | 只读核全部 ready PG 文档、上传 PDF 哈希、25 个 Chunk 的 300/60 元数据与全部 Qdrant Point/载荷；:184 open_real_run 在预检后构造检索、模型和真实客户端，结束时复核语料 |
| eval/real.py:159 _open_sdk | 仅允许 DeepSeek 官方端点，SDK max_retries=0，预算按 HTTP 请求尝试计 |
| eval/eval.py:90 summarize、:155 render_report、:263 run_evaluation、:327 main | 逐题 JSONL、固定分母、报告和 CLI；完整真实运行才更新 eval/eval_report.md |
| backend/tests/test_eval_runner.py | 数据校验、图内证据采集、评分、预算、失败与模拟隔离回归 |
| backend/app/agent/graph.py:37 build_rag_graph、backend/app/agent/service.py:112 RAGGraphRunner | 生产单轮图由评测复用；生产 POST /chat JSON/SSE、会话与检索实现未改 |

在仓库根目录运行。真实命令需要已提供项目环境变量及新的明确付费范围；本次进程临时载入既有本机配置，未输出凭据。以下为恢复入口说明，不构成暂停状态下的执行许可。

~~~powershell
& 'D:\Docker\Start-DockerDesktop.ps1'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
.\.venv\Scripts\python.exe -m eval.eval --mode mock
.\.venv\Scripts\python.exe -m eval.eval --mode real --allow-paid --max-llm-requests 100
.\.venv\Scripts\python.exe -m pytest backend/tests -v
~~~

评分规则 day18-rubric-v1 对 40 道有答案题要求选知识检索、命中全部事实组；最终来源须覆盖全部必需的精确 (filename,page)。10 道无答案题要求固定拒答“知识库中没有相关信息”且 sources=[]。候选命中与最终引用分别算；执行错误和未运行题仍留在固定分母中。延迟覆盖图内工具选择、检索、重排与生成，不含 HTTP、会话落库、评分和报告写入。

### 4. 真实基线、测试证据与判分限制

正式运行 ID 20261108T095705Z-real-625c1f7c53b2。冻结题集 day17-v1.1，语料 day17-v1，模型 deepseek-v4-flash；Embedding BAAI/bge-small-zh-v1.5 revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4，Reranker BAAI/bge-reranker-base revision 2cfc18c9415c912f9d8155881c133215df768a70，原向量证据门 0.46。运行清单 status=complete，qa_001–qa_050 各一条，50 题正常返回、执行错误 0、未运行 0、DeepSeek 请求尝试 65/100。

| 指标 | 实测 |
|---|---:|
| 整体关键词规则准确率 | 11/50（22.0%） |
| 候选来源全部命中 | 30/40（75.0%） |
| 最终引用全部命中 | 6/40（15.0%） |
| 答案与引用联合通过 | 3/40（7.5%） |
| 无答案题正确拒答 | 8/10（80.0%） |
| 有答案题固定拒答 | 29/40（72.5%） |
| 分类规则通过 | simple_fact 2/18、cross_paragraph 0/12、multi_hop 1/10、unanswerable 8/10 |
| 延迟 | 首题 97.50 秒；后续 49 题 P50 6.82 秒、P95 8.39 秒 |

eval/eval_report.md 与 data/eval/day18/20261108T095705Z-real-625c1f7c53b2/eval_report.md 字节一致。已独立复算逐题 ID、状态、候选/引用页集合、分类分母、汇总分子、P50/P95、题集/清单/规则 SHA-256。人工抽查 qa_003 正常通过；qa_020 漏转移时机与方向；qa_049 返回带句号的拒答且有来源，不符合固定契约。qa_022 答案已有物资、药物、宠物要点，规则却将该组判缺失；该题同时漏答交通影响，整题仍未通过。关键词评分是近似指标，后续规则更正须保留此基线并独立版本化。

提交前完整离线 pytest 日志 data/eval/day18/pytest-day18-commit-20261108.log 记录 697 passed、14 skipped（24.59 秒）、退出码 0，当前已知失败用例 0。先前隔离测试 data/eval/day18/pytest-day18-verified.log 为 Python 3.11.15、696 passed、14 skipped、退出码 0，且该次 .env 读取与外部连接尝试均为 0；不要将这项隔离观测误用于最新测试。模拟 50 题记录在 data/eval/day18/20261108T090519Z-mock-b1bb2d117809/。Day17 交接期间曾遇 pytest 临时目录权限错误 WinError 5，后续完整测试退出 0；失败经过见下方历史档案。

### 5. 已确认决策及原因、失败方案

复用 build_rag_graph 与 RAGGraphRunner.complete(..., history=())，保留真实单轮工具选择；从同一次 search() 包装器采集证据，否决二次检索补记来源。冻结人工关键词规则与 40/10 分母，保留原始答案以便审查；本轮不调用 LLM-as-judge。千问对比仍为待确认的另行范围。

真实运行先核 PG 全部 ready、Qdrant 目标 collection、上传文件哈希、Chunk/Point 身份与固定模型缓存，然后才建立付费客户端。BM25 会读取所有 ready 文档，故仅更换 Qdrant collection 不能隔离污染。发现数据漂移即停止，不能以自动清库或重索引掩盖。每题至多一次工具选择与一次生成，预算至多 100 次请求尝试，SDK 自动重试 0。Day19 全局 token/trace、request_logs 与 /admin/traces 尚未实现。

该批英文 PDF 临时采用 300/60，因为默认 500/100 会使部分块超过本地 BGE 512 token 预检，该批预检最大 414；原默认值未变。生产原向量门 0.46 保留。候选 30/40、最终引用 6/40 是当前真实质量表现，不事后调参或改真值。DECISIONS.md 的 D-001–D-070 原正文保留，D-071 属 Day17 时点，其“Day18 未实现”是历史陈述；Day18 和 Docker 恢复决策从 D-072 追加。

### 6. 当前错误、日志与 Docker 恢复

首次真实尝试 data/eval/day18/20261108T091447Z-real-ca4b5e40bf70/ 在第 0 题预检中止，stop_reason=corpus_preflight_unavailable，写出 0 题、DeepSeek 尝试 0。异常链为 EvalStop → sqlalchemy.exc.OperationalError → psycopg.errors.ConnectionTimeout；当时 PG 5432 与 Qdrant 6333 无监听。

默认 Docker Desktop 4.97.0 启动的后端日志 C:\Users\袁伟鑫\AppData\Local\Docker\log\host\com.docker.backend.exe.log 报 initializing Secrets Engine: engine.sock → engine.sock.stale: The file cannot be accessed by the system。旧 engine.sock 为 0 字节 reparse point，普通和管理员权限删除或改名失败，从 Codex 上下文改名其父目录也失败。Windows 实际路径解析显示该逻辑 AppData 目录落在 Codex 应用私有缓存盘；Docker 日志还报 The system cannot move the file to a different disk drive。这里记录的是路径重定向和具体错误，底层 socket 生命周期根因仍待确认。默认启动、直接清理文件和管理员改名目录均未恢复该入口。

使用既有 D:\Docker\Start-DockerDesktop.ps1 后 Docker Engine 29.9.2 启动。脚本仅为新进程设置 LOCALAPPDATA=D:\Docker\codex-runtime-20261027，复用 Roaming 设置 CustomWslDistroDir=D:\Docker\DockerDesktopWSL 与原数据盘。原有 rag-agent-postgres-1（postgres:16-alpine，卷 rag-agent_postgres_data）和 rag-agent-qdrant（qdrant/qdrant:v1.18.1，卷 rag-agent-qdrant-data）已启动。2026-11-08 18:19 左右只读复核 PG 容器 healthy，Qdrant /readyz HTTP 200；真实评测前后核对六文档和 25 点。独立 FastAPI 进程健康及新会话时的服务健康均待确认。D 盘启动的日志位于 D:\Docker\codex-runtime-20261027\Docker\log\host\。管理员已将 C 盘 Docker\run 原目录改名留存，原 docker-secrets-engine 目录未清理。操作日志在被忽略的 data/eval/day18/docker-repair-20261108-175141-541.log，历史恢复细节见 docs/docker-desktop-recovery.md。

### 7. 不可违反的约束、待完成事项、唯一下一步

遵循 AGENTS.md：Python 3.11，后端代码在 backend/，公开函数使用类型注解，任务完成前跑 pytest，不提交 .env 或 API key，未经明确要求不改 PLAN.md。本轮用户已明确授权更新 Day18 计划并本地提交。新对话首轮只读，不改文件、不运行测试或服务、不付费重跑、不暂存提交推送。既有付费授权已用于本次 65 请求；之后的真实重跑需明确范围与预算。

生产 POST /chat JSON {answer,model,sources,session_id}、SSE X-Session-ID 及 delta→保存→sources→[DONE]、最近五轮、单工具、当前来源边界、固定拒答、原向量门 0.46 与上传/索引接口不得因为低分擅改。Day13 未勾，Day19 未开始，不按评测分数改冻结 QA 或原版 PDF。不得读取或输出凭据、无关 .agents/ 或根目录用户 PDF。若状态漂移，先报告，不覆盖工作区或清理数据。

待用户独立指定的事项包括 Day18 误差归因与规则版本更正、推送或发布 Day18 本地提交、Day13 遗留项、Day19 trace、前端与部署。千问对比、LLM-as-judge、默认 Docker socket 根治和其他机器数据导入均待确认。真实基线已建立，质量低分本身不抹去该事实；质量改进另开版本和验收。

唯一下一步是新对话只读核对当前 A/B/C、Git、冻结输入、50 条真实结果与报告，复述状态，列矛盾或缺失及最多五步，再等待用户确认并指定一个动作。下一步最小代码改动为 0。本轮验收要求本地 HEAD 的父提交为 6f252c2、14 份指定文件在一个提交中、暂存区空且仅 2 项无关未跟踪条目；报告 complete、50/50 正常与 65/100 请求及 11/50 等指标可复算；Day18 五项已勾，冻结数据与生产代码未变，链接和 git diff --check 通过。

## B. 300 字以内快速恢复摘要

D:\2019\rag-agent，codex/day17-eval-dataset。Day18 已确认完成并本地提交（父 6f252c2，未推送或合并）；PLAN 五项已勾。DeepSeek 50/50 题正常，65/100 请求；规则准确率 11/50，候选来源 30/40，最终引用 6/40，拒答 8/10。完整 pytest 697 passed/14 skipped、退出 0。原始报告与逐题记录仅在本机 Git 忽略目录。Day13 未勾，Day19 未开始；暂存区空，仅 2 项无关未跟踪。后续动作待指定。

## C. 新对话的第一条启动提示词

这是已有项目的新工作会话。仓库 D:\2019\rag-agent。本轮唯一目标是只读核对 Day18 已完成的真实 50 题基线、交接包及当前 Git/文件状态，复述后等待我确认并指定唯一动作。不要依赖旧聊天。

请完整阅读 HANDOFF.md 最上方当前 A/B/C、STATUS.md、DECISIONS.md、TODO.md、README.md、AGENTS.md、只读 PLAN.md、docs/architecture.md、docs/docker-desktop-recovery.md、docs/day17-eval-completion.md、eval/README.md、eval/eval_dataset.jsonl、eval/corpus_manifest.json、eval/answer_rubric.json、eval/eval.py、eval/agent.py、eval/real.py、eval/scoring.py、backend/tests/test_eval_runner.py。下方 Day17/Day16 交接均为历史档案。

已知检查点：分支 codex/day17-eval-dataset，Day18 本地提交的父提交为 6f252c24dd42bdd1fc52e4dc7f7beb822ec999de，当前 HEAD 请只读运行 git rev-parse HEAD 核对；本地上游仍为该父提交，未推送或合并 master。Day17 四项与 Day18 五项 PLAN 均已勾，Day13 未勾，Day19 未开始。真实运行 20261108T095705Z-real-625c1f7c53b2 为 50/50 正常、65/100 请求尝试、规则准确率 11/50，正式报告在 eval/eval_report.md，原始记录在本机被忽略的 data/eval/day18/；这两处未随提交收录。提交前完整离线 pytest 为 697 passed/14 skipped、退出 0。Docker 默认启动故障仍在，D 盘脚本曾恢复本机服务。Day18 代码、计划与交接文档共 14 份形成本地提交；暂存区空，仅 2 项无关未跟踪；远端实时状态与新会话服务健康待确认。

第一轮只读，不改文件、不安装或测试、不操作服务、不暂存、提交或推送、不调用付费 API，不改 PLAN.md 或开始 Day19。不得读取或输出 .env、凭据、无关 .agents/ 或根目录用户 PDF。若状态不一致，先报告，不恢复或覆盖工作区。

请复述最终目标、已完成内容、当前实现、提交与工作区、真实基线及测试范围；列出矛盾或缺失，给出最多 5 步，然后等待我确认状态并指定唯一后续动作。

---
# 历史档案：2026-11-08 Day17 交接

# 完整交接包：Day17 已完成并推送，功能开发暂停

更新时间：2026-11-08（Asia/Shanghai）。仓库：`D:\2019\rag-agent`。
**以本页当前 A/B/C 为恢复入口；文末 2026-11-02 Day16 交接仅作为历史档案，里面的“Day17 未开始”“Day16 未推送”和旧 HEAD 不再是当前事实。**
本轮只维护交接文档，不继续功能开发，不改 `PLAN.md`，不暂存、提交、推送、创建 PR 或操作业务服务。

## A. 当前详细交接文档

### 1. 项目最终目标、当前完成点与范围

目标：交付可展示的企业知识库 RAG Agent，后端为 Python 3.11 / FastAPI / LangGraph / PostgreSQL / Qdrant，采用本地 CPU BGE、BM25/RRF/Rerank 与 DeepSeek compatible LLM；最终还需 50 题答案评测、请求 trace、Streamlit 前端和完整 Docker Compose。`PLAN.md` 是 25 天范围基线。

**已完成到 Day17**：Day17 的冻结评测语料和 50 条 QA 已通过用户确认的审查、测试与修复，四项任务及完成日志已勾；两次 Day17 提交已经推送至远端 `codex/day17-eval-dataset`。Day13 四项及日志仍未勾；Day18 的执行脚本、打分与报告尚未开始。当前任务只是交接，不代表获准开始 Day18。

Day1–3：模块化 FastAPI、compatible LLM、`POST /chat` JSON/SSE 与安全错误。Day4–5：PDF/MD/TXT 上传、按页解析与 PostgreSQL Document/Chunk。Day6–9：固定本地 BGE、显式 Qdrant 索引、检索与来源清理。Day10–12：BM25、等权 RRF60、CPU Reranker、Hybrid20→Rerank5 与原向量分数 0.46 证据门。Day14：LangGraph 编排；Day15：严格单工具；Day16：PG 业务会话、最近 5 个完整轮次与独立问题改写。Day17：冻结语料、50 条手工 QA、离线结构校验和本机入库索引。Day13 有历史学习材料记录，但计划项未勾，不能自动宣称完成。

### 2. Git、发布、未提交工作区

| 项目 | 2026-11-08 核对结果 |
|---|---|
| 分支与上游 | `codex/day17-eval-dataset`，tracking `origin/codex/day17-eval-dataset` |
| HEAD / 最近有效提交 | `6f252c24dd42bdd1fc52e4dc7f7beb822ec999de`，`docs: confirm Day 17 evaluation dataset completion`，提交于 2026-11-07 20:16:29 +08:00 |
| Day17 数据提交 / 父提交 | `d947eaa31f1789ef112572bcef7241bdbc6b57bb`，`data: add Day 17 evaluation dataset for review`；它是 `6f252c2` 的父提交 |
| Day16 完成 / 实现 | `115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d` / `74949214e8f163fbdfa2e035993a640ab866026e`，均为本分支祖先，因此已随本分支推送；各自独立命名分支是否发布：待确认 |
| 远端 Day17 | GitHub 只读核对的分支头也是 `6f252c24dd42bdd1fc52e4dc7f7beb822ec999de`；`origin` 为 `https://github.com/itysrw/rag-agent.git` |
| `master` / PR | GitHub 只读核对 `master` 为 `b68b590c8262eb568a371c895e4f7033456d045c`，开放 PR 0；closed/merged 历史待确认；Day17 未合并 `master` |
| 工作区 | `HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`README.md`、`docs/architecture.md` 六份文档含先前未提交交接改动及本轮增量；暂存区为空。`.agents/` 和根目录用户 PDF 无关，保留未读 |
| 本轮交接包 | 仅本机工作区，未暂存、提交或推送；远端 `6f252c2` 不含本轮更新后的 A/B/C |

远端为核对时快照；下一会话如需发布操作，重新只读核对。不要把本地 `origin/*` 缓存当作实时远端，不要 `reset`、`checkout` 或覆盖六份未提交文档。

### 3. Day17 冻结数据、接口契约与本机入库

| 位置 | 当前契约 |
|---|---|
| `eval/corpus_manifest.json` | 语料版本 `day17-v1`；六份 FEMA Ready.gov 原版 PDF 的官方 URL、SHA-256、每份 2 个物理页；复用原版字节，不暗示政府背书 |
| `eval/corpus/` | `earthquake.pdf`、`flood.pdf`、`hurricane.pdf`、`tornado.pdf`、`wildfire.pdf`、`winter-storm.pdf`；原版字节已随 Day17 提交推送 |
| `eval/eval_dataset.jsonl` | 样本版本 `day17-v1.1`，UTF-8 JSONL、50 行、`qa_001`–`qa_050`；每行固定 `id/category/question/expected_answer/expected_source/difficulty` 六字段 |
| 问题分布 | `simple_fact` 18、`cross_paragraph` 12、`multi_hop` 10、`unanswerable` 10；难度 easy 15、medium 20、hard 15 |
| 来源与拒答 | `expected_source` 始终为数组，元素仅 `filename` 与从 1 开始的 PDF 物理 `page`；无答案题统一 `expected_answer="知识库中没有相关信息"`、`expected_source=[]` |
| 数据说明与测试 | `eval/README.md`；`backend/tests/test_eval_dataset.py` 静态检查结构、分布、重复、文件哈希/页码、来源、错误前提回归 |

用户曾要求自己上网找可公开语料；选用 Ready.gov 官方六份原版 PDF，理由是来源可追溯、可保留原文且主题足以编写跨段落和跨文档题。中文问答是本项目自写标注，原件是英文、美国应急语境，不是官方译本，也不能直接视作中国地区指南。没有复用 Day9–12 的合成调优题。

`day17-v1.1` 修正 `qa_048`–`qa_050`：旧版把语料明确反驳的错误前提当作“无答案”；新版改问语料没有提供的电视固定、集水坑泵备用电池、水管保温参数。其余 47 条、语料及类别/难度分布不变。后续若修事实标注，记录理由并升级版本，不按模型成绩删题。

2026-11-07 在这台机器上，六份 PDF 经 `backend/app/api/documents.py:upload_document` 进入 PostgreSQL，均为 `ready`；经 `backend/app/commands/index_document.py:index_document` 显式索引到 Qdrant 的 `documents` 集合。独立核对六份上传文件 SHA-256 与 manifest 相同，各文档的 PG Chunk UUID 集合等于 Qdrant Point UUID 集合，合计 25（每份 4/5/5/4/3/4）。本机收据为**被 Git 忽略、未推送**的 `data/day17-ingestion-20261107.json`，其中列出六个 Document UUID 与逐份数量；其他机器的数据库、索引和文件不随 Git 复制。

| 本机 Document | UUID | PG Chunk / Qdrant Point |
|---|---|---:|
| `earthquake.pdf` | `50567028-d9ee-449b-a35f-1ebd3269dbcd` | 4 / 4 |
| `flood.pdf` | `987d8c4b-fc59-4ed9-a31d-7a2b743db8d3` | 5 / 5 |
| `hurricane.pdf` | `41a1d4bb-4828-4530-af5c-0ff73ebd2f86` | 5 / 5 |
| `tornado.pdf` | `1a5ca047-4e33-42de-be58-b76f97325019` | 4 / 4 |
| `wildfire.pdf` | `8207341e-ec98-4ff8-886f-3c8921169894` | 3 / 3 |
| `winter-storm.pdf` | `f244515a-a2f6-4db8-83ab-f3252dd1c729` | 4 / 4 |

Day17 实际提交范围：`d947eaa` 添加 `eval/corpus/` 六 PDF、manifest、JSONL、`eval/README.md` 和 `backend/tests/test_eval_dataset.py`；`6f252c2` 收录 `qa_048`–`qa_050` 与三条参数化回归、`PLAN.md` Day17 勾选、`docs/day17-eval-completion.md`、数据说明及五份状态覆盖文档。**Day17 未修改任何后端运行函数**；本轮交接只改第2节所列六文档，未修改函数。

原默认 `ChunkingSettings` 500/100 对该批英文 PDF 会产生超出 BGE 512 token 限制的块；本次导入单独使用 300/60，预检最大 414 BGE token，未修改仓库默认值。当前 Docker、后端、PG、Qdrant 是否仍运行及 25 点是否仍存在：**待确认**；11月7日的核对不等于实时健康证明。

### 4. 当前代码位置、调用链与禁止误改的接口

| 代码位置（行号为此检查点） | 作用 |
|---|---|
| `backend/app/main.py` | FastAPI 应用入口及路由注册 |
| `backend/app/api/documents.py:83 upload_document` | `POST /documents/upload`，解析/分块/同事务写 PG；不会自动索引 Qdrant |
| `backend/app/commands/index_document.py:72 index_document` | 按 Document UUID 读取 Chunk、嵌入并 upsert Qdrant；CLI 参数 `--document-id` |
| `backend/app/api/chat.py:59 ChatRequest`、`:165 chat`、`:102 stream_sse` | `POST /chat {message,stream,session_id?}`；JSON 回 `session_id`，SSE Header `X-Session-ID`，完整保存后才发 `sources`/`[DONE]` |
| `backend/app/services/rag.py:187 RAGService`、`:227 _open_turn`、`:282 complete`、`:300 start_stream` | 打开会话、取得进程内 lease、调用图、完整轮保存、异常补偿 |
| `backend/app/agent/graph.py:37 build_rag_graph`、`backend/app/agent/nodes.py:90/117/132/149` | 有历史 `rewrite_query_node→select_tool_node→tool_node→generate_node`；无历史跳过改写；内部合法 `PreparedRAG` 直接生成且不读写会话 |
| `backend/app/agent/state.py:13 AgentState`、`backend/app/agent/service.py:112 RAGGraphRunner` | 原始 `query` 不被改写，`standalone_query` 供选择/搜索；SSE 在建立 HTTP 流前预取必要节点 |
| `backend/app/agent/tools.py:92 AgentTools` | 严格只选并执行 `search_knowledge_base` / `get_document_detail` / `list_documents` 其中一个；详情 UUID 必须来自原问题或截断历史 |
| `backend/app/services/llm.py:148 select_tool`、`:194 rewrite_query` | 单 tool call、64KiB JSON/UUID 白名单；改写 `max_tokens=4096`、结果 1..4096 字符、JSON 唯一字段/stop/retry0 校验 |
| `backend/app/models/conversation.py:13 Conversation`、`backend/app/models/message.py:14 ConversationMessage`、`backend/app/services/conversation_memory.py:101 truncate_history`、`:209 open_session`、`:261 append_turn` | PG 业务消息表；最近 5 个完整轮次，默认 `o200k_base` 2000 token；完整 user/assistant 同事务保存 |
| `backend/app/core/config.py:100 ChunkingSettings`、`:244 ConversationMemorySettings`、`:263 RAGSettings` | 常规默认分块 500/100；会话 5 轮/2000 token；RAG 检索门参数见源码 |

搜索链：向量/BM25 各最多 20 → 等权 RRF(k=60) 取 20 → CPU BGE Rerank 取 5 → 原始 `vector_score` 默认门 0.46。目录工具仅读 `ready` 安全元数据，不读正文，`sources=[]`。历史不是当前事实来源，当前答案与 `sources` 只依据本轮工具结果。会话是 PG 业务表，**不是** LangGraph checkpointer；进程内 409 互斥不是多 worker 分布式锁。首轮失败只尝试清理本次新建且仍为空的会话；正常取消不能保证删除空会话。已提交事务与客户端收到 `[DONE]` 不具原子性。

这次交接未修改上述接口、函数、源码、测试或 `PLAN.md`。未来不能在未授权范围改 API 契约、单工具边界、证据门、历史来源规则、数据集真值或冻结原版 PDF。

### 5. 已确认决策、否决方案与原因

- `DECISIONS.md` 的 D-001–D-070 保留各阶段原因和禁区；以**后续日期的已确认演进**解释历史记录，例如 D-067 的旧 256 token 已由 D-070 修复为 4096，D-062 的 Day15 无持久化范围已由 Day16 PG 业务会话演进。不得改写历史正文或以旧日范围推翻新实现。
- Day17 选择官方原版语料与独立中文标注：保留可审计的原件、版权边界和答案来源；否决把已有合成调优题当作自然 QA、把 RAG 输出当真值、修改官方 PDF 字节或暗示官方认可。
- 冻结语料 `day17-v1` 与 QA 标注 `day17-v1.1` 分别版本化：只修三道错题而不改原件/其余题；否决把有明确反证的错误前提一律标成无答案，避免误训拒答。
- 导入使用一次性 300/60：默认 500/100 在本语料会违反 BGE 512 token 预检；否决为此次语料直接放宽 BGE 长度边界或全局改默认参数。其他文档导入须重新预检，不能无条件套用 300/60。
- 评测执行与打分属于 Day18，当前没有 RAG 准确率、source_hit、LLM-as-judge 或真实 DeepSeek 改写/选择质量结果；不能用结构测试通过或本机 25 点推断这些指标。

### 6. 当前错误、日志、测试证据与不确定项

| 时间/范围 | 结果与证据 |
|---|---|
| 2026-11-08 本轮完整离线标准 | **660 passed、14 skipped，20.31s，退出码 0**；Python 3.11.15；隔离脚本记录 `.env` 读取尝试 0、外部连接尝试 0、付费调用 0。日志：`C:\Users\袁伟鑫\.codex\visualizations\2026\11\06\01a1b0d0-b6cf-73f1-8a69-9078d9cf3b99\day17-preflight-81ae3f2dbf0e4eacbc487ee012f5c05a\day17-handoff-verified-20261108-pytest.log`，结果 JSON 同目录 `day17-handoff-verified-20261108-result.json`；仓库外，不随 Git 传递 |
| 2026-11-07 完整离线标准 | **660 passed、14 skipped，122.69s**；Python 3.11.15；`.env` 读取尝试 0、外部连接尝试 0、付费调用 0。日志：`C:\Users\袁伟鑫\.codex\visualizations\2026\11\06\01a1b0d0-b6cf-73f1-8a69-9078d9cf3b99\day17-preflight-81ae3f2dbf0e4eacbc487ee012f5c05a\day17-reviewed-confirmation-pytest.log`，仓库外，不随 Git 传递 |
| 2026-11-07 入库核验 | 六文档 `ready`、25 个对应 Point，文件哈希和 Chunk/Point UUID 集合一致；本机收据见上 |
| 2026-11-02 Day16 完成 | 652 passed / 14 skipped，45.43s；`docs/day16-conversation-results.json` 的 `completion_checkpoint.standard_test`，历史结果 |
| 更早历史 | 11月1日 Day16 644/14；10月31日 Day15 571/13；10月30日 Day15 563/12；10月29日真实局部 3 passed；10月28日 Day12 历史全真实 413 passed；最后两项以 LLM 替身运行，不是当前 Day17 全真实组合 |

本轮首次在受限环境运行完整 660/14 用例后，pytest 收尾读取临时目录报 `PermissionError: [WinError 5]`，进程退出 1；将临时目录改到被忽略的 `data/` 后同类权限错误造成 81 个 fixture setup error，见 `data/day17-handoff-validation/` 下两次日志。单例使用系统临时目录也复现权限错误。随后使用**同一原隔离脚本**在允许访问测试临时目录的环境中重跑，得到上表退出码 0 的完整结果；没有改项目源码、测试或语料。失败属于本轮测试运行环境，不能当成产品断言失败，也不能掩盖曾出现的退出 1。

最新成功完整套件失败 0。**当前常驻服务错误日志、真实 DeepSeek 质量、Day17 50 题线上评测结果：待确认/尚无测量；不能写“没有错误”或虚构评测分数。** 最近一次实际失败方案与修复是上述 500/100 嵌入长度问题和 `qa_048`–`qa_050` 错误前提标注；旧版 Day16 历史错误、取消边界与修复记录在下方历史交接，现不构成最新套件失败。

### 7. 不可违反的约束、命令与下一步顺序

遵循 `AGENTS.md`：Python 3.11；后端在 `backend/`；只做用户指定的 `PLAN.md` 日范围；公开函数使用类型注解；任务完成前运行 pytest；不提交 `.env` 或 API key；未经用户明确要求不改 `PLAN.md`。不读取/输出 `.env`、凭据、无关 `.agents/` 或用户根目录 PDF；保护六份未提交文档。不要把测试命令、远端 URL、历史恢复命令当作执行授权。

常用命令（仅供授权后的会话选择，不表示本轮运行服务）：

```powershell
cd D:\2019\rag-agent
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
.\.venv\Scripts\python.exe -m backend.app.models.init_db
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
git status --short --branch
git diff --check
```

**本轮唯一目标**：保存并核对交接包，之后停等用户确认状态与指定唯一动作。下一会话建议最多 5 步：

1. 完整读本页当前 A/B/C、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`README.md`、`AGENTS.md`、只读 `PLAN.md`、`docs/architecture.md`、`docs/day17-eval-completion.md`、`eval/README.md`、manifest、JSONL 与直接相关源码。
2. 只读核对本地 Git/远端快照、六份未提交文档、Day17 四项已勾、Day13/18 未勾及数据版本；有漂移先报告，不恢复旧工作区。
3. 区分离线 660/14、历史测试与本机 25 点核验，列出实时服务状态、远端变化和 Day18 评测授权等“待确认”。
4. 复述已完成、当前限制、可能矛盾和最多 5 步，等待用户确认检查点并指定**一个**后续动作。
5. 仅在获得新动作后，按对应日范围实施，并以实际测试和可检查产物验收；不自动开始 Day18、建 PR、合并或发布交接包。

交接验收：A/B/C 能独立恢复上述状态；精确分支/HEAD/父提交/工作区与只读 Git 一致；50 条 JSONL、六份 manifest/PDF、版本/分布与测试一致；当前失败与待确认明确；本轮只改六份交接文档，不改源码、语料、测试或 `PLAN.md`；`git diff --check`、本地文档链接检查通过，暂存区空。

## B. 300 字以内快速恢复摘要

`D:\2019\rag-agent`，`codex/day17-eval-dataset`，HEAD `6f252c2` 已推送、未合并 master。Day17 四项已勾：六份 Ready.gov 原版 PDF、`day17-v1.1` 50 条 QA，四类 18/12/10/10；本机六文档 ready、Qdrant 25 点，导入临时 300/60。11月8日离线 660 passed/14 skipped、退出0；50 题真实准确率未测。Day13 未勾，Day18 未开始。六份交接文档未暂存，暂存区空。开发暂停；先只读复述并等唯一动作。

## C. 新对话的第一条启动提示词

这是已有项目的新工作会话。仓库 `D:\2019\rag-agent`，功能开发暂停；不要依赖旧聊天。本轮唯一目标是**只读核对 Day17 已完成、分支已推送、交接包与当前 Git/文件一致，并复述状态**，随后等待我确认并指定唯一后续动作。

请先完整读 `HANDOFF.md` 的当前 A/B/C（文末 2026-11-02 Day16 内容是历史档案）、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`README.md`、`AGENTS.md`、只读 `PLAN.md`、`docs/architecture.md`、`docs/day17-eval-completion.md`、`eval/README.md`、`eval/corpus_manifest.json`、`eval/eval_dataset.jsonl`，再按 HANDOFF 第4节核对直接相关源码。

已知检查点：分支 `codex/day17-eval-dataset`，HEAD/远端 Day17 分支 `6f252c24dd42bdd1fc52e4dc7f7beb822ec999de`，父 `d947eaa31f1789ef112572bcef7241bdbc6b57bb`；Day17 四项及日志已勾，Day13 未勾、Day18 未开始，尚未合并 master。六份交接文档含未提交改动，暂存区空，无关 `.agents/` 和根目录 PDF 保留未读。`day17-v1.1` 50 题，语料 `day17-v1` 六份原版 PDF；本机 11月7日六文档 ready、25 Point，导入临时 300/60。最新成功离线套件 660 passed、14 skipped、退出码0（11月8日）；受限环境曾因 pytest 临时目录权限退出1，详见 A 第6节。当前服务健康与真实 50 题准确率待确认。远端和本机状态需要按当前时间重新只读核对。

执行规则：不重做已完成工作，不擅自推翻 D-001–D-070 或 Day17 冻结真值，不假设未知。第一轮不改文件、不安装/测试、不操作服务、不下载、不暂存/提交/推送、不调用付费 API，不改 `PLAN.md` 或开始 Day18；不得读取/输出 `.env`、凭据、无关 `.agents/` 或用户 PDF。状态不一致先报告，不 reset 或覆盖用户改动。

验收：复述项目目标、已完成 Day17、提交与工作区、数据与测试范围、当前限制；列出矛盾或缺失并给出最多 5 步，然后等待我确认状态并指定唯一动作。在此之前不改变仓库或外部状态。

---

# 历史档案：2026-11-02 Day16 本地提交检查点

以下旧版 A/B/C、静态哈希及“当前”表述均只对 2026-11-02 当时有效，不作为 Day17 之后的实时状态；保留用于追溯早期接口理由、失败记录和精确符号。

# 完整交接包：Day16 已完成的本地提交检查点

更新时间：2026-11-02（Asia/Shanghai）
仓库：D:\2019\rag-agent
当前模式：**功能开发暂停。本轮只整理交接文档，不测试、不操作服务、不暂存/提交/推送，不开始Day17。**

本文件包含 A（详细文档）、B（≤300字符摘要）、C（新对话启动提示词）。
文件路径相对仓库根目录，仓库外材料使用绝对路径。不依赖旧聊天。
“功能已完成”“PLAN已勾”“测试已执行”“本地提交”“远端发布”“实际运行健康”分别判断；待确认不等于默认成功。
本包取代先前以Day15为唯一入口的启动词；历史验收文件保留原状。

## A. 详细交接文档

### 1. 项目最终目标与当前范围

构建可用于作品展示、简历和面试的企业知识库RAG Agent：
FastAPI、PostgreSQL Document/Chunk及业务会话、Qdrant、本地BGE、BM25/RRF/Rerank、DeepSeek compatible LLM、LangGraph、多轮指代，
最终交付50条自然QA/答案评测、trace、Streamlit和完整Docker Compose。
计划与开发规范：[PLAN.md](PLAN.md)、[AGENTS.md](AGENTS.md)；决策全文：[DECISIONS.md](DECISIONS.md)。

**当前完成到Day16；Day17未开始。** Day13学习文件/示例证据此前已核验，但PLAN四项和日志仍未标记，不自动补勾。
用户已经确认Day16“审查、测试与修复通过”；这是完成确认，不虚构独立审查过程或真实模型准确率。
本轮唯一目标是保存可以独立恢复的交接包，下一步最小改动为0。

### 2. 当前Git、发布、工作区与计划

| 项目 | 2026-11-02只读核对结果 |
|---|---|
| 分支 | codex/day16-conversation-memory |
| HEAD/完成提交 | 115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d |
| 说明/时间 | feat: complete Day 16 conversation memory；2026-11-02T08:13:29+08:00 |
| 父提交/Day16实现 | 74949214e8f163fbdfa2e035993a640ab866026e |
| 父提交说明/时间 | feat: implement Day 16 conversation memory；2026-11-01T21:04:28+08:00 |
| Day15完成/实现 | a006139f4ae1406c5f20144730c76fe122d0c2bc / 4ce29aa634ae4deaf975dc6380746686b0d78469 |
| Day14检查点 | b76987934663f7d90603dbc4abb2432d52baf91f，远端分支已发布 |
| Day12检查点 | 34712772b3682d174f459da91100b09f8a2493cc，远端分支已发布 |
| 本地master/origin/master及本轮远端master | b68b590c8262eb568a371c895e4f7033456d045c |
| origin | https://github.com/itysrw/rag-agent.git |
| Day16/Day15 tracking | 均未设置；不能用不存在的上游计算ahead/behind |
| 本轮远端分支快照 | 只有Day12、Day14、master，未见Day15/16 |
| 发布结论 | Day16两次及Day15两次提交仍仅本地，未合并master；本轮不发布 |
| 当前open PR | 本轮只读列表为0；closed/merged历史未查询，待确认 |
| 暂存区 | 空 |
| tracked未提交改动 | 仅HANDOFF、STATUS、DECISIONS、TODO、README、docs/architecture.md六份文档，均未暂存 |
| 无关untracked | .agents/、就业推荐表_完整填充版.pdf，保留且未读取 |
| 本轮文档范围 | 只整理上述六文档，不提交本轮交接包 |
| PLAN当前SHA256 | 1B1F6809A8350FE8584704A8290550223691B5C9378D3D0E666C8E8F76F23296 |

远端来源：[分支列表](https://api.github.com/repos/itysrw/rag-agent/branches?per_page=100)、
[open PR列表](https://api.github.com/repos/itysrw/rag-agent/pulls?state=open&per_page=100)。
这是交接时的只读快照；未来要重新只读核对，不把origin缓存引用或旧报告当实时远端。
没有fetch/push、创建PR、改变上游或全局网络设置。

PLAN逐日状态：Day1–12原标记保留；Day14五项/日志、Day15四项/日志已完成。
**Day16五项、完成确认和开发日志已于2026-11-02按用户确认完成。**
Day13四项/日志仍未标记，Day17以后未开始。总览旧日范围不替代逐日条目。
PLAN此前Day12/14/15的“尚未推送/下一日未开始”属于当日历史，不改写为当前状态。

7494921只收录Day16实现和文档增量；115d9a2收录已审查修复、PLAN完成及状态增量，原六文档历史整理保留未暂存。
本轮已为这六份文档保存原稿及diff，再统一整理为当前Day16交接；不reset/checkout恢复、不git add .。
复制仓库不等于复制凭据、模型、PG/Qdrant数据、词表或目录外验证工具。

### 3. 已完成内容与证据边界

- Day1–3：模块化FastAPI、DeepSeek compatible JSON/SSE、安全错误和可替换客户端。
- Day4–5：PDF/MD/TXT、页边界、20MiB/500页、按页o200k_base 500/100、Document/Chunk同事务两次flush。
- Day6–9：固定CPU BGE、独立token预检/有限下载重试、显式512/Cosine Qdrant索引、来源/拒答/清理、严格top_k/doc_id及受控实验。
- Day10–12：独立BM25、等权RRF60、固定CPU CrossEncoder Top20→Top5、原始vector_score证据门、排名日志与本地真实受控比较。
- Day13：仓库外笔记、可编辑图/PNG、官方无Key示例及14项自测此前已验；不是用户理解自检或永久归档，PLAN未勾。
- Day14：惰性双节点图、条件边、invoke/custom stream、预取、背压、跨线程Context与取消，已发布；当前编排已演进。
- Day15：search_knowledge_base/get_document_detail/list_documents，只选并执行一个；严格64KiB/JSON/UUID校验、安全ready目录、两阶段预取。
- a006139：S99.pdf/page 99.pdf/第1页.pdf/[S99.pdf]完整/SSE文件名修复，8条回归；真实选择入口默认关闭。
- Day16/7494921：conversations/messages、session_id、最近5轮/2000 token、独立问题改写、四节点、原子保存、SSE Header、进程内互斥、取消回滚。
- Day16/115d9a2：改写输出预算从256提升到4096 token；首轮选择/生成/保存异常补偿清理新建空会话；对应8条新增回归及完成标记收录。
- 11月2日提交前完整标准652/14通过；本次交接仅静态核对，不重跑测试。

没有：Day17自然50条QA、LLM-as-judge、Day19完整trace/request_logs/admin API、Streamlit、完整一键部署；
也没有会话管理HTTP API、跨session画像、长期记忆、历史总结、向量记忆、LangGraph checkpointer/PostgresSaver、ReAct循环或并行工具。
session隔离按UUID查询，不等于多用户认证/权限；互斥只在单进程内，不等于多worker分布式锁。

### 4. 当前调用链、State与三个工具

~~~text
POST /chat {message, stream, session_id?}
 -> ChatRequest strip/长度/UUID校验
 -> RAGService.complete 或 start_stream
 -> _open_turn:
      已有session先取得进程内lease；新session创建UUID后取得lease
      ConversationMemoryService.open_session -> 不可变DTO -> 关闭DB Session
      truncate_history: 最近5轮，默认2000 token
 -> graph START:
      内部合法PreparedRAG -> generate_node
      公共无历史         -> select_tool_node
      公共有历史         -> rewrite_query_node -> select_tool_node
 -> tool_node -> generate_node -> END
 -> 成功完整answer -> user/assistant同事务保存 -> 返回JSON
 -> SSE: 必要改写+选择+执行全部预取成功才建立HTTP流
         delta逐段发送 -> 完整生成校验 -> 原子保存 -> sources -> [DONE]
~~~

图有4个已注册业务节点；公共首轮实际经过3个，后续有历史经过4个。
内部prepare→complete(PreparedRAG)/stream(PreparedRAG)跳过改写/选择/工具及会话读写，仍复用同一检索业务代码。
无图checkpointer、thread_id、message reducer或服务对象入State；业务消息持久化在PG表。

| AgentState字段 | 不变量 |
|---|---|
| query | strip后的原始问题，1..4096字符；节点不覆盖，数据库保存它 |
| standalone_query | 首轮等于query，有历史时仅rewrite节点改写，供选择和搜索 |
| history | 截断后的不可变完整轮次DTO，最多10条；不是本轮事实证据 |
| needs_query_rewrite | 无历史/内部False；有历史True，改写后False |
| retrieved_docs | 搜索完整Top5；目录为空 |
| prepared | PreparedRAG或None；question仍对应原始query |
| answer | 完整清理后的答案，由generate节点写入 |
| tool_calls | 公共最终恰好1个，内部0个 |
| needs_tool_selection | 公共True，选择后False；内部PreparedRAG False |

AgentUpdate是局部TypedDict，不包含query/history写入字段；AgentContext仅response_mode=complete/stream。
PreparedRAG=question/messages/sources/has_relevant_context；RAGAnswer另带可选session_id，公共返回UUID，内部为None。
服务、SQL Session、客户端、lease与cancel control不进入业务State。

| 工具 | 模型参数与执行边界 | 结果 |
|---|---|---|
| search_knowledge_base | query:str，strip后1..4096；执行始终用state的standalone_query，不采用选择模型另造query | Hybrid两路各20→RRF60取20→CPU BGE Rerank5→原vector_score默认0.46 |
| get_document_detail | doc_id:str≤64且可解析UUID；规范化ID必须来自原问题或本次截断历史，不能仅出现在改写结果中 | ready安全元数据+SQL聚合chunk_count，sources=[] |
| list_documents | arguments严格{}，不能带limit/filter等额外字段 | ready，created_at DESC/id ASC，SQL最多51、返回50+truncated，sources=[] |

目录仅documents.id/filename/size/status/created_at，详情只聚合chunks.doc_id/chunk_id；不查询正文、extracted_text或本机路径。
目录Session按需创建；搜索不解析目录服务配置，但Hybrid/BM25本身仍依赖PG。
工具结果、历史和问题作为不可信user JSON，system仅静态规则；有历史时最终Prompt同时保留原问题、独立问题、历史和当前结果。
生成规则将当前工具结果规定为唯一事实依据，后端sources只取本次结果，旧答案/来源不得混入；实际模型遵循准确率待确认。没有当前证据则固定拒答“知识库中没有相关信息”。

LLM调用计数：首轮选择1次，有上下文再生成1次；后续有历史增加改写1次。
公共拒答仍有选择1次，有历史再有改写1次，只省最终生成。内部PreparedRAG拒答才是总LLM调用0。
调试检索API不经过会话、改写或工具选择。

### 5. 会话表、历史裁剪与原子保存

Conversation：conversations表，UUID主键，UTC aware created_at/updated_at。
ConversationMessage：messages表，UUID、conversation_id外键CASCADE、sequence_no、role、content、metadata、created_at。
sequence_no>=1；UNIQUE(conversation_id,sequence_no)及组合索引；role仅user/assistant；内容非空。
ORM属性message_metadata映射数据库metadata列，PG JSONB/SQLite JSON变体。
user metadata={}；assistant仅{"sources":[{"filename":...,"page":...}]}；不存工具参数、Prompt、Chunk、分数、Token用量、延迟或画像。

open_session(None)事务创建空Conversation；已有UUID必须存在。
按sequence_no DESC LIMIT 10读取，再反转；验证奇数起始、连续序号、成对user/assistant。损坏/孤立历史安全失败，不补造消息。
DTO返回前关闭Session，不持有事务等待LLM或工具。

truncate_history：
- 一轮=一条user+一条assistant，最多5轮；不能把5条消息叫5轮。
- 计数覆盖role/content/sources的紧凑JSON，o200k_base是近似口径，不是DeepSeek精确tokenizer。
- 从最新完整轮向旧轮累加，超预算停止，输出恢复时间顺序；不拆半个旧轮。
- 只有最新一轮本身超限才在token边界裁内容；严格解码避免截坏Unicode。
- 来源元数据本身过长时删完整来源条目，不生成截短文件名；历史截断不改变数据库全文或当前sources。
- 空历史直接返回，不为首轮加载词表；MEMORY_MAX_TURNS固定5，max_tokens默认2000/范围128..16000，encoding固定o200k_base。

append_turn在单事务内锁住会话行，查询最大序号（必须偶数），同时添加user/assistant并更新updated_at；
flush后若观察到取消则整轮回滚，成功才commit。第二条失败同样回滚，避免孤立user。
process-global active UUID集合+Lock分配ConversationLease，跨同一进程服务实例共享，冲突409；lease幂等关闭，不长期保留闲置UUID。
DB行锁保持追加序号一致，不代表已实现多worker请求级串行化。

115d9a2补偿：仅对本次新建会话，在选择/生成/保存异常时尝试delete_empty_session。
该方法仅在会话仍无任何消息时删除；已有会话及非空会话不删；清理DB错误不覆盖原安全错误。
流异常通过on_failure执行一次，锁释放前处理。
**正常close/GeneratorExit/客户端断开不等于所有Exception；不能声称每个取消都会删除空会话。**
首轮SSE可能已返回X-Session-ID，之后失败补偿删除空会话，再用该ID会404。取消不保存部分轮次，但可能保留无消息会话。
已提交完整轮次后网络失联不能撤回事务；不宣称DB提交与客户端收到DONE是原子操作。

### 6. LLM协议、SSE预取、关闭与来源清理

选择使用现有compatible客户端/base_url/model，stream=False、tool_choice=required、thinking disabled、with_options(max_retries=0)。
本地校验choices=1、tool_calls=1、type=function、ID strip后1..128、函数白名单、字段与类型。
arguments须JSON object，禁止重复键；原始UTF-8及规范化JSON均≤65536字节。
搜索query须合法；详情UUID还在执行边界按原问题/截断历史验证。无eval/动态反射调用；schema深拷贝、additionalProperties=false不替代本地校验。

改写LLMClient.rewrite_query：
stream=False、thinking disabled、response_format={"type":"json_object"}、max_tokens=4096、SDK retry0，不附加tools。
恰好1个choice、finish_reason严格stop，无tool_calls；content非空且UTF-8≤65536字节；
JSON只有standalone_query，禁止重复键/额外字段/错误类型/无效Unicode，strip后1..4096字符。失败抛QueryRewriteError(LLMServiceError)，安全502，不静默回退或重试。
输出4096 token与问题4096字符是两个上限，不能混为一谈；原256 token已由D-070修复。
普通生成沿用既有客户端行为，不能宣称全部LLM请求SDK重试均为0。
合法HTTP字符长度不保证BGE/Reranker tokenizer容量；真实长问题仍可能安全422。受控长问题测试含SDK/检索替身及CharacterEncoding，只证明协议路径，不证明真实DeepSeek/BGE长问题效果。

RAGGraphRunner.start_stream使用graph.stream(stream_mode=["updates","custom"],version="v2")：
有历史先验证rewrite update，再依次验证select_tool_node与tool_node update；无历史只预取后两项。
得到PreparedRAG后才创建StreamingResponse，错误保留HTTP码；后续继续同一迭代器，不重复工具/检索/改写。
只暴露custom {"type":"delta","delta":str}；内部State/update/Prompt/参数/历史不入SSE。
StreamControl每段等待acknowledge形成背压，cancel唤醒暂停生产者；
PreparedRAGStream用独立Context+RLock跨线程推进，finish持锁到保存结束，取消可发信号，close等待事务结束再释放lease。
最终answer必须与全部delta拼接一致，保存成功才sources/DONE。fail回调一次；close取消并幂等关闭图/sanitizer/上游。
ASGI finally使用取消保护与线程池清理；同步阻塞I/O仍受既有默认60s timeout，不是任意I/O立即强制中断。
每次invoke/stream tracing_context(enabled=False)、callbacks=[]，不导出业务State到LangSmith。

目录preserve_filenames=True，保留S99.pdf/page 99.pdf/第1页.pdf/[S99.pdf]等答案数据，仍清理伪造页码/来源ID，sources为空。
完整模式复用流式分类器，部分扩展名跨delta等待；4样例×complete/SSE共8条回归。
搜索及内部旧路径沿用原严格来源清理，不把样例覆盖外推所有任意文件名。

### 7. 精确文件、函数、当前代码位置与提交范围

以下行号由本轮静态AST解析取得。保护哈希未漂移时可直接定位；文件改变后以符号为准。
没有执行import应用、模型或测试来获取行号。

| 当前文件 | 精确符号与行号 |
|---|---|
| [backend/app/agent/state.py](backend/app/agent/state.py) | AgentState L13；AgentUpdate L27；AgentContext L39；initial_agent_state L45 |
| [backend/app/agent/graph.py](backend/app/agent/graph.py) | route_tool_selection L23；build_rag_graph L37 |
| [backend/app/agent/nodes.py](backend/app/agent/nodes.py) | AgentNode L26；StreamControl L34；StreamControl.acknowledge L41；StreamControl.cancel L45；StreamControl.emit L50；create_retrieve_node L62；create_retrieve_node.retrieve_node L69；create_rewrite_query_node L90；create_rewrite_query_node.rewrite_query_node L94；create_select_tool_node L117；create_select_tool_node.select_tool_node L119；create_tool_node L132；create_tool_node.tool_node L134；create_generate_node L149；create_generate_node.generate_node L152 |
| [backend/app/agent/service.py](backend/app/agent/service.py) | PreparedRAGStream L33；PreparedRAGStream.next_event L48；PreparedRAGStream.cancel L55；PreparedRAGStream.finish L59；PreparedRAGStream.fail L67；PreparedRAGStream.close L74；_initial_state L92；_event_data L102；RAGGraphRunner L112；RAGGraphRunner.complete L119；RAGGraphRunner._events L161；RAGGraphRunner.start_stream L178；RAGGraphRunner.stream L235 |
| [backend/app/agent/tools.py](backend/app/agent/tools.py) | tool_definitions L62；AgentToolExecution L68；_metadata L75；_catalog_execution L80；AgentTools L92；AgentTools.search_knowledge_base L103；AgentTools.get_document_detail L112；AgentTools.list_documents L120；AgentTools.execute L128 |
| [backend/app/models/conversation.py](backend/app/models/conversation.py) | Conversation L13 |
| [backend/app/models/message.py](backend/app/models/message.py) | ConversationMessage L14 |
| [backend/app/models/init_db.py](backend/app/models/init_db.py) | main L10 |
| [backend/app/services/conversation_memory.py](backend/app/services/conversation_memory.py) | ConversationMemoryError L28；ConversationMemoryUnavailableError L32；ConversationNotFoundError L36；ConversationBusyError L40；ConversationTurnCancelledError L44；ConversationSource L49；ConversationHistoryMessage L55；ConversationSnapshot L62；validate_history L67；history_payload L83；serialize_history L91；history_token_count L96；truncate_history L101；truncate_history.size L114；truncate_history.prefix L137；ConversationLease L154；ConversationLease.close L163；acquire_conversation L175；acquire_conversation.release L182；ConversationMemoryService L189；ConversationMemoryService._session L196；ConversationMemoryService.open_session L209；ConversationMemoryService.delete_empty_session L241；ConversationMemoryService.append_turn L261；get_conversation_memory_service L299 |
| [backend/app/services/llm.py](backend/app/services/llm.py) | OpenAICompatibleClient L15；OpenAICompatibleClient.with_options L20；LLMConfigurationError L23；LLMServiceError L27；LLMToolCallError L31；QueryRewriteError L35；LLMFunctionDefinition L45；LLMToolDefinition L53；AgentToolCall L60；validate_tool_call L68；_unique_json_object L101；LLMMessage L110；LLMClient L117；LLMClient.model L140；LLMClient.complete L144；LLMClient.select_tool L148；LLMClient.rewrite_query L194；LLMClient.complete_messages L231；LLMClient.stream L246；LLMClient.stream_messages L250；LLMClient._request_options L269；_validated_messages L285；get_llm_client L305；_QUERY_REWRITE_MAX_TOKENS L42 |
| [backend/app/services/rag.py](backend/app/services/rag.py) | RAGSource L87；PreparedRAG L95；RAGAnswer L105；RAGGraphError L114；select_relevant_chunks L118；build_sources L138；build_rag_messages L151；RAGService L187；RAGService._memory L208；RAGService._history_settings L212；RAGService._discard_created_empty_session L218；RAGService._open_turn L227；RAGService.model L248；RAGService._runner L253；RAGService.prepare L266；RAGService.complete L282；RAGService.start_stream L300；RAGService.stream L326；_strip_model_source_references L333；_sanitized_model_deltas L339；_consume_sanitized_text L365；_reference_candidate_start L402；_classify_reference_candidate L412；_classify_group_candidate L438；_classify_extension_candidate L458；_classify_page_candidate L478；_classify_chinese_page_candidate L521；_classify_source_id_candidate L563；_following_filename_extension L594；_is_word_character L614；get_rag_service L619 |
| [backend/app/services/document_catalog.py](backend/app/services/document_catalog.py) | DocumentCatalogError L25；DocumentCatalogUnavailableError L29；DocumentListItem L34；DocumentDetail L45；DocumentListResult L52；DocumentCatalogService L60；DocumentCatalogService.list_documents L82；DocumentCatalogService.get_document_detail L92；get_document_catalog_service L106 |
| [backend/app/api/chat.py](backend/app/api/chat.py) | ChatRequest L59；ChatSourceResponse L70；ChatResponse L77；require_rag_service L86；stream_sse L102；_RAGStreamingResponse L139；chat L166；_source_dict L249 |
| [backend/app/core/config.py](backend/app/core/config.py) | Settings L24；LLMSettings L41；DatabaseSettings L60；DocumentSettings L77；DocumentSettings.resolve_upload_dir L93；ChunkingSettings L100；ChunkingSettings.validate_encoding_name L116；ChunkingSettings.validate_overlap L124；EmbeddingSettings L131；EmbeddingSettings.resolve_cache_dir L159；EmbeddingSettings.require_normalized_vectors L167；QdrantSettings L174；QdrantSettings.strip_nonempty_value L196；QdrantSettings.build_url L203；RerankerSettings L208；RerankerSettings.resolve_cache_dir L231；RerankerSettings.reject_boolean_batch_size L237；ConversationMemorySettings L244；ConversationMemorySettings.parse_fixed_turn_limit L253；RAGSettings L263；get_settings L281；get_llm_settings L287；get_database_settings L293；get_document_settings L299；get_chunking_settings L305；get_embedding_settings L311；get_qdrant_settings L317；get_rag_settings L323；get_reranker_settings L329；get_conversation_memory_settings L335 |
| [backend/app/core/database.py](backend/app/core/database.py) | Base L12；DatabaseConfigurationError L16；build_database_url L20；get_engine L40；get_session_factory L49；get_database_session L54 |
| [backend/app/core/logging.py](backend/app/core/logging.py) | configure_logging L11；_include_jsonl L36；_exclude_jsonl L40 |
| [backend/app/main.py](backend/app/main.py) | lifespan L27；create_app L36；create_app.log_request L53 |
| [backend/app/services/document_storage.py](backend/app/services/document_storage.py) | UploadMetadata L20；UploadPaths L28；DocumentStorageError L35；UnsafeFilenameError L39；UnsupportedDocumentTypeError L43；EmptyDocumentError L47；DocumentTooLargeError L51；validate_upload_metadata L55；build_upload_paths L78；save_upload_to_part L93；promote_upload L122；cleanup_upload_files L130；_validate_stored_content L137；_unlink_if_present L148 |
| [backend/app/services/document_parser.py](backend/app/services/document_parser.py) | PageText L13；DocumentParseError L20；InvalidPdfError L24；EncryptedPdfError L28；PdfPageLimitError L32；InvalidTextEncodingError L36；NoExtractableTextError L40；parse_document L44；serialize_pages L65；_parse_pdf L70；_parse_utf8_text L93 |
| [backend/app/services/text_splitter.py](backend/app/services/text_splitter.py) | ChunkDraft L31；TextSplittingError L40；split_pages L44；split_pages.token_length L66；_split_by_token_windows L117；_find_chunk_end L161；_find_overlap_start L207；_validate_configuration L247 |
| [backend/app/services/embedding.py](backend/app/services/embedding.py) | EmbeddingError L26；ModelDownloadError L30；ModelLoadError L34；EmbeddingInputError L38；EmbeddingInputTooLongError L42；ChunkEmbeddingInputTooLongError L61；EmbeddingResultError L74；ChunkEmbeddingInput L79；EmbeddedChunk L87；Tokenizer L94；Tokenizer.encode L97；SentenceEmbeddingModel L106；SentenceEmbeddingModel.encode L112；SentenceEmbeddingModel.get_sentence_embedding_dimension L114；ensure_model_snapshot L122；load_embedding_model L180；_load_embedding_model_cached L194；validate_model_input_length L226；EmbeddingClient L255；EmbeddingClient.dimension L272；EmbeddingClient.embed_documents L276；EmbeddingClient.embed_query L339；embed_chunks L357；get_embedding_client L415；_validated_snapshot_path L420；_is_retryable_download_error L429；_model_max_tokens L448；_coerce_vector_rows L455；_validate_vector L463 |
| [backend/app/services/qdrant_store.py](backend/app/services/qdrant_store.py) | QdrantStoreError L28；QdrantUnavailableError L32；QdrantCollectionMismatchError L36；QdrantResultError L40；VectorizedChunk L45；RetrievedChunk L59；QdrantClientProtocol L72；QdrantClientProtocol.collection_exists L75；QdrantClientProtocol.create_collection L77；QdrantClientProtocol.get_collection L84；QdrantClientProtocol.upsert L86；QdrantClientProtocol.query_points L93；QdrantVectorStore L96；QdrantVectorStore.initialize_collection L112；QdrantVectorStore.validate_collection L141；QdrantVectorStore.upsert_chunks L193；QdrantVectorStore.search L216；_build_point L283；_validated_vector L312；_parse_scored_point L337；_validated_metadata L392；get_qdrant_vector_store L411 |
| [backend/app/services/retrieval.py](backend/app/services/retrieval.py) | RetrievalService L24；RetrievalService.search L35；_validated_top_k L59；_log_search_event L70；get_retrieval_service L106 |
| [backend/app/services/bm25.py](backend/app/services/bm25.py) | BM25Error L45；BM25UnavailableError L49；BM25IndexError L53；BM25CorpusChunk L58；BM25RetrievedChunk L71；BM25Snapshot L85；tokenize_bm25 L98；load_bm25_chunks L120；build_corpus_fingerprint L160；build_bm25_snapshot L189；BM25Service L214；BM25Service.search L222；_is_chinese_run L333；_validate_corpus_chunk L337；_validated_top_k L364；_validated_scores L374；_log_search_event L401；get_bm25_service L442 |
| [backend/app/services/hybrid.py](backend/app/services/hybrid.py) | HybridError L38；HybridResultError L42；HybridRetrievedChunk L47；_RankedPayload L65；reciprocal_rank_fusion L79；HybridRetrievalService L146；HybridRetrievalService.search L157；_ranked_branch L197；_validated_payload L213；_validated_metadata L262；_same_payload L279；_best_rank L296；_validated_top_k L307；_validated_rank_constant L318；_log_search_event L328；get_hybrid_retrieval_service L369 |
| [backend/app/services/reranker.py](backend/app/services/reranker.py) | RerankerError L46；RerankerUnavailableError L50；RerankerInputError L54；RerankerResultError L58；CrossEncoderModel L62；CrossEncoderModel.predict L67；RerankedChunk L71；RankMovement L92；RerankOutcome L104；_snapshot_complete L115；ensure_reranker_snapshot L122；PassageOnlyTokenizer L180；load_reranker_model L196；rank_candidates L228；RerankerService L299；RerankerService.rerank L319；_validated_query L398；RerankedRetrievalService L404；RerankedRetrievalService.search L413；get_reranked_retrieval_service L452 |
| [backend/app/api/documents.py](backend/app/api/documents.py) | DocumentUploadResponse L54；require_database_session L64；upload_document L83；_cleanup_failed_upload L240；_format_byte_limit L265 |
| [backend/app/api/retrieval.py](backend/app/api/retrieval.py) | RetrievalSearchRequest L32；RetrievedChunkResponse L48；RetrievalSearchResponse L61；require_retrieval_service L67；search_retrieval L79 |
| [backend/app/api/bm25.py](backend/app/api/bm25.py) | require_bm25_service L24；search_bm25 L33 |
| [backend/app/api/hybrid.py](backend/app/api/hybrid.py) | require_hybrid_retrieval_service L36；search_hybrid L51 |
| [backend/app/api/rerank.py](backend/app/api/rerank.py) | RerankSearchRequest L26；RerankedChunkResponse L34；RerankSearchResponse L42；require_reranked_retrieval_service L48；search_reranked L57 |
| [backend/app/api/health.py](backend/app/api/health.py) | health L9 |
| [backend/app/commands/init_qdrant.py](backend/app/commands/init_qdrant.py) | QdrantInitializationSummary L22；initialize_qdrant L33；print_summary L47；main L59 |
| [backend/app/commands/embed_document.py](backend/app/commands/embed_document.py) | DocumentChunksNotFoundError L32；EmbeddingConfigurationError L36；EmbeddingSummary L41；embed_document L57；print_summary L99；build_parser L111；main L125 |
| [backend/app/commands/index_document.py](backend/app/commands/index_document.py) | DocumentIndexingError L41；DocumentNotFoundError L45；DocumentChunksNotFoundError L49；QdrantConfigurationError L53；IndexSummary L58；index_document L72；print_summary L148；build_parser L157；main L171 |
| [backend/tests/test_conversation_models.py](backend/tests/test_conversation_models.py) | test_explicit_schema_registers_new_tables_without_altering_documents L15；test_database_rejects_invalid_business_messages L33；test_duplicate_sequence_and_database_cascade L49 |
| [backend/tests/test_conversation_memory.py](backend/tests/test_conversation_memory.py) | test_reads_latest_five_complete_turns_in_order L35；test_unknown_session_and_isolation L56；test_second_message_failure_rolls_back_whole_turn_and_updated_at L67；test_memory_errors_are_classified_without_sensitive_details L96；test_turn_limit_priority_and_exact_json_token_budget L114；test_oversized_latest_turn_is_valid_unicode_json_and_counted_with_sources L124；test_large_source_metadata_is_bounded_without_fabricating_filenames L137；test_partial_or_reversed_turn_is_rejected L145；test_incomplete_persisted_turn_is_rejected L150；test_process_local_conflict_and_independent_sessions L160；test_memory_settings_defaults_and_bounds L173；test_memory_environment_configuration L182 |
| [backend/tests/test_conversation_chat.py](backend/tests/test_conversation_chat.py) | test_two_turn_json_and_sse_resolve_document_reference_and_keep_current_sources L37；test_sse_first_then_json_followup_and_session_isolation L71；test_only_five_recent_turns_enter_rewrite_and_generation_prompts L87；test_prompt_injection_stays_in_json_and_previous_answer_cannot_supply_evidence L99；test_historical_uuid_is_allowed_but_rewriter_cannot_invent_uuid L113；test_memory_open_failures_happen_before_any_model_call L138；test_http_missing_or_invalid_session_never_calls_model L154；test_failure_at_each_stage_saves_no_turn_and_releases_session L167；test_partial_stream_close_and_prefetch_close_never_save_and_release_lease L187；test_stream_errors_emit_no_sources_or_done_and_no_partial_turn L206；test_first_failed_request_leaves_no_conversation_or_messages L235；test_long_independent_followup_reaches_tool_and_generation L290；test_process_lock_spans_generation_across_service_instances_but_other_sessions_run L375；test_internal_prepared_adapter_never_opens_or_writes_memory L398；test_asgi_delivery_failure_drops_partial_turn_and_releases_session L409；test_http_session_conflict_is_409_before_model_or_tool_work L438；test_full_response_save_failure_is_safe_500_and_no_orphan_turn L455；test_followup_sse_prefetch_finishes_rewrite_and_tool_before_generation L474；test_truncated_prompt_does_not_shorten_persisted_messages L488；test_history_in_generation_prompt_is_data_and_never_enters_system L502；test_bad_memory_configuration_is_safe_503_before_creating_a_session L516；test_cancellation_during_save_rolls_back_both_messages_before_releasing_lease L537 |
| [backend/tests/test_conversation_postgres.py](backend/tests/test_conversation_postgres.py) | test_real_postgres_creates_memory_tables_and_persists_two_atomic_turns L22 |
| [backend/tests/test_llm.py](backend/tests/test_llm.py) | test_rewrite_uses_bounded_json_output_without_tools_or_retries L112；test_invalid_rewrite_never_retries_or_exposes_content L140；test_rewrite_rejects_multiple_choices_and_upstream_failure L148；test_rewrite_accepts_question_length_boundaries L162；test_selector_uses_required_nonstreaming_single_call_without_retries L310；test_selector_rejects_malformed_or_ambiguous_responses_without_retry L343；test_selector_sdk_failure_is_safe_and_not_retried L351；test_selector_accepts_full_4096_character_unicode_query L360；test_selector_cannot_be_overridden_by_extra_body_and_does_not_change_generation L367 |
| [backend/tests/test_agent_graph.py](backend/tests/test_agent_graph.py) | test_compiled_graph_selects_and_executes_exactly_one_tool L12；test_prepared_false_branch_skips_retrieval_and_missing_context_fails L36；test_graph_compiles_lazily_once_per_service L54 |
| [backend/tests/test_agent_service.py](backend/tests/test_agent_service.py) | test_prefetch_is_retrieval_only_then_deltas_are_live_and_close_upstream L45；test_iterator_can_resume_and_close_on_different_http_worker_threads L63；test_close_after_prefetch_does_not_start_llm L76；test_retrieval_error_propagates_before_any_streaming_or_llm L86；test_invalid_prefetch_events_fail_safely L102；test_missing_generation_update_fails_instead_of_reporting_success L112；test_forced_environment_tracing_cannot_export_state L128；test_incomplete_final_state_is_safe_failure L145；test_bad_event_after_prefetch_is_not_exposed L161；test_prefetch_rejects_missing_out_of_order_or_premature_generation L180；test_final_tool_count_is_distinct_for_public_and_internal_paths L195 |
| [backend/tests/test_agent_tools.py](backend/tests/test_agent_tools.py) | test_catalog_result_is_untrusted_json_with_no_page_sources_or_body L88；test_bad_or_invented_arguments_execute_no_tool L117；test_detail_normalizes_only_uuid_present_in_original_question L127；test_catalog_failure_is_http_before_sse_with_no_retrieval_or_generation L197；test_catalog_answers_keep_filename_extensions_but_remove_page_and_source_markers L239；test_catalog_api_preserves_legal_source_like_filename_verbatim L258；test_malicious_filename_is_json_data_and_cannot_change_system_rules L307 |
| [backend/tests/test_llm_tool_selection_integration.py](backend/tests/test_llm_tool_selection_integration.py) | test_real_deepseek_selects_one_correct_tool_for_each_question L29 |

115d9a2直接收录的6个已审查修复路径：
- backend/app/agent/service.py：PreparedRAGStream.on_failure/fail及RAGGraphRunner.stream异常补偿。
- backend/app/services/conversation_memory.py：ConversationMemoryService.delete_empty_session。
- backend/app/services/llm.py：_QUERY_REWRITE_MAX_TOKENS=4096与rewrite_query。
- backend/app/services/rag.py：_discard_created_empty_session、_open_turn、complete、start_stream。
- backend/tests/test_conversation_chat.py：首轮失败不留会话/消息、长独立问题JSON/SSE、已有错误/取消断言。
- backend/tests/test_llm.py：改写max_tokens=4096请求断言。

115d9a2另收录PLAN、六状态文档和Day16 MD/JSON，共15个路径。
7494921收录36路径，含Day16模型/服务/图/测试/配置样例/报告及文档增量，未改PLAN。
两提交联合37个路径（不是当前六份未提交文档）：

~~~text
.env.example
DECISIONS.md
HANDOFF.md
PLAN.md
README.md
STATUS.md
TODO.md
backend/app/agent/graph.py
backend/app/agent/nodes.py
backend/app/agent/service.py
backend/app/agent/state.py
backend/app/agent/tools.py
backend/app/api/chat.py
backend/app/core/config.py
backend/app/models/conversation.py
backend/app/models/init_db.py
backend/app/models/message.py
backend/app/services/conversation_memory.py
backend/app/services/llm.py
backend/app/services/rag.py
backend/tests/conftest.py
backend/tests/test_agent_graph.py
backend/tests/test_agent_service.py
backend/tests/test_agent_state.py
backend/tests/test_agent_tools.py
backend/tests/test_chat.py
backend/tests/test_conversation_chat.py
backend/tests/test_conversation_memory.py
backend/tests/test_conversation_models.py
backend/tests/test_conversation_postgres.py
backend/tests/test_llm.py
backend/tests/test_rag.py
backend/tests/test_rag_integration.py
docs/architecture.md
docs/day16-conversation-memory.md
docs/day16-conversation-memory.mmd
docs/day16-conversation-results.json
~~~

本次交接实际只编辑六个文档，原稿和diff已保存到第12节证据目录；源码、测试、PLAN、依赖和验收报告不动。

### 8. HTTP、JSON、SSE及安全错误契约

| 方法/路径 | 当前输入与行为 |
|---|---|
| GET /health | 源码契约200 {"status":"ok"}，仅进程存活；本轮未请求它 |
| POST /documents/upload | multipart file；PDF/MD/TXT，成功201，实际≤20MiB/PDF≤500页 |
| POST /retrieval/search | query、strict top_k 1..20默认5、可选单UUID doc_id；Cosine score，不返回向量 |
| POST /retrieval/bm25/search | 同上；raw BM25，token无重合返回空 |
| POST /retrieval/hybrid/search | 同上；两路各20、等权RRF60，按请求top_k返回RRF score |
| POST /retrieval/rerank/search | 仅query及可选doc_id，不接受top_k/candidate_k/mode；Hybrid20→Rerank5及名次 |
| POST /chat | message、stream默认False、session_id:UUID或None；JSON或SSE |

检索query strip后1..4096、extra=forbid；top_k拒绝bool/字符串/浮点/null/0/21。
合法但无匹配doc_id返回200空数组，不新增404。
Chat保留原extra忽略行为，但额外needs_*字段不能跳过工具；session_id省略/null创建新会话，合法但不存在的会话404。

~~~json
{"message":"有哪些文档？","stream":false}
{"answer":"...","model":"...","sources":[],"session_id":"后端生成的UUID"}
~~~

后续携带同一个真实返回的session_id；SSE响应头X-Session-ID，Content-Type=text/event-stream，
Cache-Control=no-cache，X-Accel-Buffering=no。成功事件：

~~~text
data: {"delta":"..."}

event: sources
data: {"sources":[]}

data: [DONE]
~~~

搜索sources来自本轮实际通过门控的filename/page并去重；目录为空。没有新增会话管理/工具轨迹/trace字段或端点。

| 条件 | 状态/固定安全detail |
|---|---|
| session UUID无效 | 422 |
| session不存在 | 404 / The conversation does not exist. |
| 同session运行中 | 409 / The conversation already has a request in progress. |
| PG/记忆配置、连接或超时 | 503 / The conversation memory is unavailable. |
| 会话内部查询/保存错误 | 500 / The conversation memory request failed. |
| LLM缺配置 | 503 / The language model is not configured. |
| 选择/改写/完整生成失败 | 502 / The language model request failed. |
| 目录配置/连接/超时 | 503 / The document catalog is unavailable. |
| 目录内部SQL | 500 / The document catalog service failed. |
| Embedding/Reranker输入过长 | 422 / 各自既有chat专用安全detail |
| 非法检索结果/重复ID/payload冲突 | 502 / The retrieval service returned an invalid result. |
| 检索分支/模型不可用 | 503 / The retrieval service is unavailable. |
| BM25/Hybrid/Reranker内部计算 | 500 / The retrieval service failed. |
| 图协议错误 | 500 / The RAG service failed. |
| 流开始后LLM失败 | event:error / The language model stream failed. |
| 流开始后图协议失败 | event:error / The RAG stream failed. |
| 流开始后保存/取消事务错误 | event:error / The conversation could not be saved. |

流内错误不发sources/DONE；工具、改写及检索错误必须在HTTP建立前完成。
空目录/不存在ready文档/无证据搜索是200固定拒答，若整体成功仍保存该完整轮次。
独立rerank API沿用自身“The rerank ...”错误文案，不套用Chat文案。
不公开异常原文、SQL、参数、State或私有上游响应。

### 9. 模型、参数、持久化、排序及依赖

以下是源码固定值/默认值，**未读取.env，实际运行配置和可用性待确认**。

| 项目 | 固定/默认值 |
|---|---|
| Python | 项目规则3.11，最新测试3.11.15 |
| LLM | https://api.deepseek.com / deepseek-v4-flash / 默认60s；普通生成默认thinking disabled |
| 改写 | 非流式JSON，max_tokens=4096，结果1..4096字符，SDK retry0 |
| 工具选择 | 非流式required、thinking disabled、SDK retry0，本地恰好1调用、64KiB |
| Memory | 最多5轮/10条，o200k_base默认2000 token，可配128..16000；存储完整 |
| Embedding | BAAI/bge-small-zh-v1.5 / revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4 / CPU / 512维归一化 / batch≤32 |
| 查询instruction | 为这个句子生成表示以用于检索相关文章：；只添加一次，文档直接编码 |
| 切分 | 按页o200k_base 500/100；BGE另做包含特殊token的512 token预检 |
| Hybrid | 顺序向量/BM25各20，等权Σ1/(60+rank)，一基排名，取20 |
| Reranker | BAAI/bge-reranker-base / revision 2cfc18c9415c912f9d8155881c133215df768a70 / CPU / 512 / batch默认4范围1..8 |
| 搜索证据门 | RAG_MIN_RELEVANCE_SCORE默认0.46范围0..1，仅原始vector_score；BM25-only排除 |
| Qdrant | documents默认collection、unnamed 512/Cosine、localhost:6333、timeout10s、upsert batch≤32/wait=True |
| PG | localhost:5432 / ragagent / postgres，密码须安全配置；新会话表是否已实际建好待确认 |
| 上传 | 1MiB分块、实际20MiB、PDF≤500页、UUID.part→os.replace |
| Compose | 目前仅PostgreSQL；完整backend/frontend/qdrant编排未做 |

Hybrid按chunk UUID融合；同路重复ID拒绝，跨路同ID的doc_id/chunk_index/content/page/filename/metadata类型和值须一致，true/1/1.0不能互换。
稳定键(-rrf_score,best_rank,doc_id,chunk_index,chunk_id)，原始score不参与融合；任一路失败整体失败，不静默降级。
Rerank对全部最多20候选按位置绑定logit，再以(-logit,hybrid_rank,doc_id,chunk_index,chunk_id)排序取5；
rank_change=hybrid_rank-rerank_rank。RerankOutcome保留完整movements和耗时，推理在实例锁内串行。
query+成对特殊token数>=512时安全422；PassageOnlyTokenizer显式only_second，不截query。
Cosine/BM25/RRF/logit量纲不同；0.46不能用于RRF或logit。

Reranker固定匿名六文件：config.json、model.safetensors、sentencepiece.bpe.model、special_tokens_map.json、tokenizer.json、tokenizer_config.json。
仅范围内连接/读/超时、429/5xx有限重试，首次+最多3次，1/2/4s；从本地加载local_files_only、trust_remote_code=False/use_safetensors=True，Identity与apply_softmax=False保留logit，要求num_labels=1。
不要把Reranker safetensors名单错套到原Embedding白名单。
上传不自动Embedding/索引；显式索引先关PG Session再推理/upsert，PG/Qdrant不是跨库事务，不自动recreate collection。
BM25全局ready快照、全局IDF、指纹刷新、token-overlap门控，doc_id在TopK前过滤；刷新失败不返回旧快照。

直接依赖固定sentence-transformers==5.3.0、qdrant-client==1.18.0、rank-bm25==0.2.2、langgraph==1.2.16；Day16无新依赖。
依赖闭包/checkpoint/prebuilt包名不代表启用checkpointer或预置ToolNode。当前安装完整版本/pip check未在交接阶段重新查询。
openai仅作compatible SDK，不代表后端调用OpenAI服务或需要OpenAI Key。
配置前缀APP_/LLM_/POSTGRES_/EMBEDDING_/QDRANT_/RERANKER_/RAG_/MEMORY_；相对上传/模型路径锚定PROJECT_ROOT，默认data/uploads、data/models。

### 10. 已确认决策、原因及否决项

D-001至D-070完整原文见[DECISIONS.md](DECISIONS.md)，本轮70条正文逐字节保留，不新增/推翻决策。

| 决策 | 当前采用与理由 | 已否决/禁止擅自回退 |
|---|---|---|
| D-001/014 | 按PLAN逐日、文件检查点，不依赖会话记忆 | 未授权跨Day，把计划写成实现/发布 |
| D-003–010/038 | 单一DeepSeek compatible、JSON/SSE、安全错误、替身标准 | 多供应商、标准测试计费、输出私有上游错误 |
| D-015–023 | 页边界、500/100、稳定UUID/JSONB、两次flush同事务 | 混页、无relationship时假设一次flush自动排序、提前迁移/回填 |
| D-024–030 | 固定本地CPU BGE、独立长度预检、显式512/Cosine索引 | 云Embedding、静默截断、上传自动索引、自动重建collection |
| D-032–037 | 不可信user JSON、当前来源/拒答/预取/清理 | 历史/Context入system或作事实、模型自报来源、无证据生成 |
| D-039–042 | 严格top_k/doc_id、最小日志、确定性质量常量 | bool/字符串top_k、TopK后过滤、记录原问题正文、改判据迁就失败 |
| D-043–049 | 确定性BM25、全局IDF/刷新、等权RRF60、UUID一致性 | raw score相加、正文去重、旧快照/部分降级、RRF当证据门 |
| D-050–053 | CPU安全CrossEncoder、query完整、20→5、原向量证据 | pickle/remote code替代、先截5、截query、logit套0.46、BM25-only生成 |
| D-054–058 | 惰性图、局部State、真实custom流、背压/取消、禁tracing、内部适配 | 预缓冲完整答案、重复检索、透传State、服务入State |
| D-059–064 | 严格单工具、safe ready目录50+1、来源/文件名分离 | beta strict、多个调用取第一个、动态执行、正文/路径目录输出 |
| D-065/066 | PG业务消息表、最新5个完整轮/JSON token预算 | 双存checkpointer、只存内存、5条当5轮、截断存储、半个旧轮 |
| D-067/068 | 先改写再选工具，原/独立问题分开；完整轮事务、进程内互斥 | 改写失败回退、历史当当前事实、原问题被覆盖、先存孤立user、长事务等LLM |
| D-069 | 完整流保存后终态，提交前取消回滚，事务结束再释放 | 部分答案入库、保存失败仍DONE、多worker锁或客户端收到DONE原子性的虚假承诺 |
| D-070 | 改写预算4096 token及新建空会话异常补偿 | 继续256截断合法长问题、删除已有/非空会话、补偿错误覆盖主错误、宣称所有close皆删 |

历史范围必须区分：
D-031固定Top5属于Day7，Day9已有可调top_k；D-049不改Chat属于Day11，Day12已接Rerank。
D-034零LLM是原生成链路拒答；Day16公共仍选择，后续还有改写。
D-054双节点/空tool_calls属于Day14，Day15单工具，Day16增加条件改写节点与PG业务会话。
D-061“原问题检索/原文UUID”在Day16按授权演进为独立问题检索、原问题或截断历史UUID。
D-062“不持久化”是Day15范围，Day16已有PG消息持久化但仍没有图checkpointer。
D-067的256 token是11月1日实现快照，D-070明确修复为4096 token；不能修改历史原文或拿它否定已确认演进。
D-011–013的额度边界、供应商比较仍只是历史决策/可选未来范围，不自动产生任务。

### 11. 已执行测试、当前通过/失败与质量范围

| 日期/阶段 | 实际结果 | 范围与不可外推项 |
|---|---|---|
| 2026-11-02 / 115d9a2提交前 | **652 passed / 14 skipped，45.43s，0失败/0警告** | 最新完整backend/tests；Python3.11.15，dotenv/真实连接尝试0、付费0 |
| 2026-11-01 / 7494921交付 | 644 passed / 14 skipped，18.83s | Day16原实现历史，不含本次8条新增回归 |
| 2026-11-01 / 取消落库定向 | 90 passed，17.90s | 真实SQLite事务+受控LLM/检索，非真实PG/DeepSeek |
| 2026-11-01 / Day16开工离线 | 571 passed / 13 skipped，16.85s | 修复本机缺失词表之后的接受基线 |
| 2026-10-31 / Day15完成 | 571 passed / 13 skipped，34.70s | Day15完成历史 |
| 2026-10-30 / Day15实现 | 563 passed / 12 skipped，44.52s | 同文件final_standard历史，之后有Day15收尾 |
| 2026-10-30 / Day14提交前 | 453 passed / 12 skipped，23.34s | 旧检查点 |
| 2026-10-29 / 最近真实局部 | **3 passed，160.84s** | 2项真实本地集成+1项普通质量回归；PG/Qdrant/BGE/Reranker真实，LLM替身 |
| 2026-10-28 / 历史全部本地真实 | **413 passed，158.94s** | Day12历史、0跳过，LLM替身；不是当前Day16全真实套件 |

最新依据：[Day16 JSON](docs/day16-conversation-results.json)的completion_checkpoint.standard_test、
[Day16 MD](docs/day16-conversation-memory.md)首节。
原JSON顶层standard_test=644/14、contracts.rewrite_max_tokens=256、verification.plan_unchanged=true属于11月1日实现快照；
completion_checkpoint记录11月2日652/14、4096 token和PLAN授权变更，不能互相覆盖。
[Day15 JSON](docs/day15-agent-tools-results.json)中completion_checkpoint=571/13、顶层final_standard=563/12也是分阶段记录。
[Day14 MD](docs/day14-langgraph-migration.md)的未推送文字是推送前历史；本轮远端已见b769879，不得沿用作现状。
[Day12 MD](docs/day12-rerank-comparison.md)/[JSON](docs/day12-rerank-results.json)保留原测量，本轮不追写。

14跳过=原12项可选真实集成+Day15付费工具选择1项+Day16真实PG记忆1项。
标准测试包含SQLite持久化/约束/回滚和fake LLM/SDK/检索，不是全部真实本地组合，更不是DeepSeek路由/改写准确率。
test_long_independent_followup_reaches_tool_and_generation使用CharacterEncoding替身隔离输出预算路径，不是实际o200k/BGE长度/质量证明；真实Token裁剪另有tiktoken中文/Emoji等测试。
未执行本次真实PG表创建/两轮持久化入口，没有本次真实DeepSeek改写探测；实际新表是否已建待确认。
不得把413和新增测试数量相加推算“当前全真实”计数。

**本次交接没有重跑pytest、pip check、模型或服务。最近已执行标准失败0，不表示当前常驻应用健康或没有运行时错误。**

核心入口：
- test_conversation_models.py：PostgreSQL DDL/JSONB、注册/角色/序号/非空/唯一/外键CASCADE。
- test_conversation_memory.py：0/1/5/6轮、序号/来源、完整事务回滚、异常分类、Token预算/Unicode/元数据、固定5轮环境解析。
- test_conversation_chat.py：两轮JSON/SSE混用、指代、当前来源、UUID来源、隔离/409、各阶段失败、ASGI取消、提交前取消、内部适配；
  首轮失败不留会话/消息6种组合，长独立问题完整/SSE2种组合。
- test_llm.py：改写JSON/stop/空白/额外字段/重复键/Unicode/1..4096、4096 token预算、SDK retry0，以及既有单工具协议。
- test_agent_state/nodes/graph/service.py：9字段、三路入口、内部0工具、实际图、预取顺序、背压、跨线程、错误、tracing及惰性编译。
- test_agent_tools.py：三工具与目录SQL安全边界、四种文件名×完整/SSE；test_chat.py/test_rag.py/test_main.py保留既有契约。
- test_conversation_postgres.py::test_real_postgres_creates_memory_tables_and_persists_two_atomic_turns：默认关闭、只读取进程PG配置、显式建新表并清理自建会话。
- test_llm_tool_selection_integration.py::test_real_deepseek_selects_one_correct_tool_for_each_question：默认关闭，成功一次会有3次付费选择，无工具/生成。

受控质量仍是同24 Chunk/12正/3负：
Hybrid Hit@1/Hit@5/MRR@5=0.917/1.000/0.944，Rerank=0.917/1.000/0.958。
Hit@1未提升；远程接入正确目标3→2但首位仍错，6203问题无关年假候选17→2保留。
首次命中不代表Top5每项正确，不外推自然长文、表格、多跳或50条自然QA。
历史首次装载约2.83s、同题热predict约6.29s/20候选、12题平均约6.39s，是同进程且缓存可能预热的测量，不是冷启动/HTTP全链路/QPS/p95。
历史临时Document/Chunk/collection曾清理为0；当前数据现状待确认。

### 12. 验证入口、原始证据及仓库外依赖

当前完成证据根目录（本轮已读机器记录和运行器，未读basetemp）：

~~~text
C:\Users\袁伟鑫\.codex\visualizations\2026\11\01\01a196e1-5365-73c0-9067-5ee389a7cdd4\
  day16-validation\
    run_checks.py / prepare_tokenizer.py
    tokenizer-data\fb374d419588a4632f3f557e76b4b70aebbca790
    baseline-offline-result.json / baseline-offline-pytest.log / -openapi.json
    cancellation-regression-result.json / -pytest.log
    delivery-standard-result.json / -pytest.log / -openapi.json / -graph.mmd
    original-documents\ / original-six-documents.diff / baseline-hashes.json
    documentation-increments.json / staged-verification.json / postcommit-verification.json
  day16-completion-20261102\
    run_checks.py
    precommit-20261102-result.json / -pytest.log / -openapi.json / -graph.mmd
    protected-reviewed-hashes.json
    original-workspace\ / starting-workspace.diff / original-six-documents.diff
    completion-doc-increments.json / staged-verification.json / postcommit-verification.json
  day16-handoff-20261102\
    original-documents\ / starting-six-documents.diff
    original-decisions-body.bin
    protected-sha256.json / source-symbols.json / git-checkpoint.json
    remote-readonly-snapshot.json / static-verification.json
~~~

公开o200k_base词表SHA256=446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d；
原URL为https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken。
它是分词数据，不是BGE模型；仅历史Day16开工时取回并验证，本轮未下载或读取其内容。
完成运行器将TIKTOKEN_CACHE_DIR指向day16-validation/tokenizer-data；这是本机路径，不保证异机仍在。
运行器和原始日志不在Git；独占pytest basetemp是临时/缓存资源，不读取、复用或清理。
本包记录的路径不保证所有原始文件未来存在，未复核者均待确认。

原Day16需求附件历史路径：
C:\Users\袁伟鑫\.codex\attachments\ffb45bcb-391c-42bf-8907-690eff21cdf4\已粘贴的文本.txt。
本包已记录实现边界；附件现存与新会话访问能力待确认。

#### Day13–15历史证据路径与真实选择入口原始记录

以下沿用旧交接中已记录的路径和阶段事实，“本轮/本次”指原Day15交接阶段；不当作11月2日新执行或实时可用性证明：

`backend/tests/test_llm_tool_selection_integration.py::test_real_deepseek_selects_one_correct_tool_for_each_question`
是一项默认跳过的付费集成入口，内部有三类问题，成功时会产生**3次真实选择请求**，不是1次。
它只验证生产选择Prompt/schema/LLMClient，不执行三个业务工具，不验证PG目录或RAG生成的真实组合。
需要RUN_LLM_TOOL_SELECTION_INTEGRATION=1且用户已安全配置进程LLM_API_KEY；
该测试使用 `_env_file=None`，硬编码DeepSeek base_url与deepseek-v4-flash，不读取项目.env。
本次10月31提交前显式设该开关0，没有执行该入口；“新增/收录测试”不能写成“真实探测已通过”。
未来付费运行必须获得独立明确授权，并约束至这三次选择，不能自动调用。

本机可追溯证据（仓库外，复制仓库不会自动带走）：

```text
C:\Users\袁伟鑫\.codex\visualizations\2026\10\30\01a18d2e-ee85-7d93-981a-6b35e55d4d74\day15-validation\
  run_checks.py
  baseline-offline-result.json / -pytest.log / -openapi.json
  final-result.json / final-pytest.log / final-openapi.json / final-graph.mmd
  original-documents\ / doc-increments.json / stage_day15.py / verify_delivery.py

C:\Users\袁伟鑫\.codex\visualizations\2026\10\30\01a18d2e-ee85-7d93-981a-6b35e55d4d74\day15-completion-20261031\
  run_checks.py
  precommit-20261031-pytest.log / -result.json / -openapi.json / -graph.mmd
  reviewed-source-hashes.json / original-workspace\ / completion-doc-manifest.json
  update_completion.py / stage_completion.py

C:\Users\袁伟鑫\.codex\visualizations\2026\10\30\01a18d2e-ee85-7d93-981a-6b35e55d4d74\day15-handoff-20261101\
  original-documents\        本轮六份文档原始快照
  protected-sha256.json      本轮92项保护基线
  remote-branches.json       本轮GitHub分支只读摘要
  static-verification.json   本轮文档收尾静态核验结果
```

上述已读取的日志/摘要在本轮可用，其余具体文件只保存路径线索；新会话或异机是否仍可访问待确认。
独占pytest basetemp是缓存/临时资源，不是交付物；不要读取或清理其中内容，也不要复用作下一次basetemp。

历史临时材料（本轮未访问，当前是否存在待确认）：

- Day13：`C:\Users\袁伟鑫\AppData\Local\Temp\rag-agent-day13-71af7f75cf91462a8d38247a5b2fa22a`；
  day13-langgraph-notes.md、day13-agent-graph.drawio/.png、official-hello-world.py、hello-world-result.json、day13-delivery-manifest.json。
  关键产物哈希已记录在Day14报告，不属于永久归档。
- Day14：`C:\Users\袁伟鑫\AppData\Local\Temp\rag-agent-day14-feb71aa9c2e74566b33c1213b211cc47`；
  run-checks.py、run-real.py、baseline/final OpenAPI、real-pytest.log、day14-real-quality.json。
  Day14提交前标准标签commit-20261030-8f24b715，与Day15的precommit-20261031不同。
- 原Day15需求附件：`C:\Users\袁伟鑫\.codex\attachments\5d1cf91e-ffb1-4511-b152-b1249f63f1da\已粘贴的文本.txt`。
  附件Gate0“Day14未提交、HEAD3471277”是旧状态，已经被b769879及Day15两次提交取代，不能重复执行保存任务。

机器JSON的pytest stats含空键，普通PowerShell ConvertFrom-Json可能报空属性名错误；
使用 `ConvertFrom-Json -AsHashtable` 或Python标准库json读取。空键是阶段统计，不是JSON损坏或新的业务错误。

### 13. 精确操作命令（示例不等于许可）

当前只允许只读恢复与复述；下面安装、启动、测试、建表、索引或付费命令仅供未来用户明确指定对应动作后使用。
已有.env/.venv不得覆盖；不读取或输出凭据；Python必须3.11。

从仓库根目录安装/启动：

~~~powershell
Set-Location -LiteralPath 'D:\2019\rag-agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
~~~

默认Swagger为http://127.0.0.1:8000/docs，这不是当前后端运行证据。
显式数据库和索引入口：

~~~powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m backend.app.models.init_db
.\.venv\Scripts\python.exe -m backend.app.commands.init_qdrant
.\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
~~~

init_db注册Document、Chunk、Conversation、ConversationMessage，只create_all缺失表，不改已有表，不在启动/health执行。
Day16标准DDL/SQLite测试不代表真实PG已建表，先确认实际状态；不重复初始化或重启服务来代替只读恢复。
<UUID>仅用户指定文档；embed_document只产内存向量，index_document才写Qdrant。
Qdrant历史部署镜像qdrant/qdrant:v1.18.1、命名卷rag-agent-qdrant-data、绑定127.0.0.1:6333；完整Compose尚未实现。

AGENTS标准入口：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
~~~

裸命令没有本机审计守卫，不能冒充与652/14完全相同的隔离运行。
最近实际完整标准由目录外run_checks.py调用pytest.main，参数为：

~~~text
backend/tests -v --tb=short --basetemp=<新GUID独占目录> -p no:cacheprovider -p no:langsmith_plugin
~~~

若未来明确授权标准复验，先只读审查并确认运行器和公开词表路径可用，再使用新标签：

~~~powershell
$day16VerifyLabel = 'verify-' + [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python.exe -B 'C:\Users\袁伟鑫\.codex\visualizations\2026\11\01\01a196e1-5365-73c0-9067-5ee389a7cdd4\day16-completion-20261102\run_checks.py' $day16VerifyLabel backend/tests
~~~

该运行器固定REPO=D:\2019\rag-agent；改到异机前须审查路径，不盲跑。
七个真实开关均设0：

~~~text
RUN_POSTGRES_INTEGRATION=0
RUN_QDRANT_INTEGRATION=0
RUN_LOCAL_EMBEDDING_INTEGRATION=0
RUN_RAG_INTEGRATION=0
RUN_RERANKER_INTEGRATION=0
RUN_LLM_TOOL_SELECTION_INTEGRATION=0
RUN_CONVERSATION_POSTGRES_INTEGRATION=0
~~~

同时HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE=1，LANGSMITH_TRACING/LANGCHAIN_TRACING_V2=false，-B不写pyc；
禁dotenv source并拦截.env打开与服务连接，仅在Windows框架内部socketpair创建上下文放行内部通信。
缺少词表会引发网络守卫错误，不要删守卫或伪造分词结果。历史临时目录访问限制需针对本次独占目录获得适当执行权限，不改全局ACL或删旧缓存。

模块定向（仍需另行指定）：

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_conversation_models.py backend/tests/test_conversation_memory.py backend/tests/test_conversation_chat.py backend/tests/test_llm.py backend/tests/test_agent_graph.py backend/tests/test_agent_service.py backend/tests/test_chat.py -v
~~~

仅真实PG记忆验收（默认关闭，本轮未执行；仅进程配置、不读取.env）：

~~~powershell
$env:RUN_CONVERSATION_POSTGRES_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_conversation_postgres.py -v
~~~

它会显式创建缺失记忆表并清理自建会话，属于真实DB写操作，不能在只读恢复时运行。
当前没有已执行的真实DeepSeek改写验收，不自动新增/运行付费探测。
已收录的真实工具选择入口只在另获明确付费授权且进程Key安全就绪时使用：

~~~powershell
$env:RUN_LLM_TOOL_SELECTION_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_llm_tool_selection_integration.py -v
~~~

成功一次测试有3次选择请求，无业务工具或生成；不得自动读.env填Key。
若另行授权全部本地真实组合，按指定范围显式开启相应开关，两个付费/PG独立入口按范围单独控制，不把旧413当新计数。
test_rag_integration.py会在启用时显式建记忆表，记录并清理自建会话；质量报告DAY12_RERANK_REPORT_JSON只指向不存在的新文件（open x），不覆盖历史报告。

首次恢复允许的只读Git示例：

~~~powershell
git --no-optional-locks -c core.quotepath=false status --short --branch
git --no-optional-locks branch -vv
git --no-optional-locks rev-parse HEAD HEAD^ refs/heads/codex/day15-agent-tools refs/heads/master
git --no-optional-locks log -4 --oneline
git --no-optional-locks diff --name-only
git --no-optional-locks diff --cached --name-only
git --no-optional-locks diff -- PLAN.md backend/requirements.txt docker-compose.yml
git --no-optional-locks diff --check
~~~

不fetch/push、不compileall（会写缓存），不调用应用探测依赖来证明只读状态。

### 14. 已尝试但失败的方案与处理

| Day16历史尝试/问题 | 实际结果与处理 |
|---|---|
| 最初受限pytest临时目录 | WinError5，使用新独占目录和获准的正常执行权限；不改ACL，不读/清旧缓存 |
| 词表缺失的开工基线 | 558 passed/13 failed/13 skipped，14次连接尝试被守卫阻止；取得公开固定SHA256词表后，接受基线571/13，未修改业务规则 |
| Emoji超长参数化ID | 74 passed/2 errors；Windows PYTEST_CURRENT_TEST值超过32767字符；改短ids，保留原Unicode内容和断言 |
| 首次HTTP定向 | 241 passed/6 failed；原Day15精确JSON/schema断言尚未包含授权新增session_id；按新契约修正，非放宽来源/错误断言 |
| MEMORY_MAX_TURNS环境字符串 | 47 passed/1 failed；Literal[5]拒绝字符串"5"；parse_fixed_turn_limit只把"5"转为5，其他非法值仍拒绝 |
| 记忆配置异常映射 | 修为安全503并在创建会话前验证，避免裸ValidationError/无效会话副作用 |
| 取消恰逢消息保存 | 持RLock到flush/commit/rollback结束，提交前检测cancel并整轮回滚；定向90项通过 |
| 改写输出max_tokens=256 | 可能截断合法长独立问题；已审查修复为4096 token，结果字符/JSON校验不放宽；受控完整/SSE回归通过，不等于真实模型测量 |
| 首轮选择/生成/保存失败 | 新建空会话可能无返回ID而遗留；115d9a2按created标记+空表条件补偿清理，不删除已有/成功会话，不覆盖主错误 |
| 文件写入/补丁工具历史失败 | 普通写入曾EPERM，部分非幂等补丁重放曾造成重复定义/参数；用明确作用域、事前哈希、幂等脚本修正并静态检查。不要在未知状态盲目重放补丁或恢复旧文件 |

相关历史错误原文（不是当前失败）：

~~~text
PermissionError: [WinError 5]
EPERM: operation not permitted, open 'D:\2019\rag-agent\backend\tests\test_chat.py'
ValueError: the environment variable is longer than 32767 characters
pydantic_core._pydantic_core.ValidationError:
max_turns
Input should be 5 [type=literal_error, input_value='5', input_type=str]
~~~

本机Day16初期失败及处理在机器报告earlier_attempts，652/14接受记录没有这些失败。
以下原Day12–15记录保留细节与错误行，时间/“本轮”均指其历史阶段，不覆盖当前Day16状态：

下表区分已解决的历史试跑/操作问题与尚无根治证据的环境问题；不把它们写成当前业务回归。

| 历史尝试/问题 | 结果与处理/否决原因 |
|---|---|
| Day15目录清理只保留扩展名 | 合法S99.pdf/page 99.pdf/第1页.pdf/[S99.pdf]仍可能被当来源删掉；a006139统一完整/流式分类器并补8条回归，已解决 |
| 首次Day15定向 | 178 passed/1 failed：惰性编译计数包装器未转发新增catalog_factory关键字；修正包装器，不删除断言；后续全量通过 |
| Day15临时目录权限 | 初始pytest遇到WinError5；在新独占目录和适当执行权限下验证，不改全局ACL、不清旧缓存；根因未宣称根治 |
| 离线隔离器一律阻断socket.connect | Windows asyncio内部socketpair误被拦截；失败试跑309 passed/69 failed/75 errors/12 skipped，144次内部通信被误记为连接尝试；改为thread-local仅放行socketpair创建上下文，接受基线453/12、最终571/13外部尝试0 |
| Day15文档增量git apply --cached --check | 曾报patch does not apply；未采用此补丁，具体不匹配原因待确认；改为对明确文档路径构造已校验增量blob，保留旧正文 |
| Day12未创建临时父目录 | WinError3 setup错误；创建获准的新独占父目录后通过，不复用未知basetemp |
| Day12重复注册rerank_router | Duplicate Operation ID；删除重复注册并增加路由回归，未改接口 |
| Xet权重首次下载 | 未及时完成后停止；标准HTTPS取得相同固定safetensors成功；没有完整失败trace，根因待确认 |
| 受限网络安装rank-bm25 | 获网络允许后成功，不是已证实的版本冲突 |
| BM25完整复合编号“只能一条命中”断言 | 共享组成token可命中多Chunk；用唯一数字验证刷新，未改分词算法 |
| Day14检查器先import应用 | anyio重写警告；pytest之后再导出OpenAPI，最终无警告 |
| 离线探针要求Embedding safetensors/完整Rerank snapshot | 与既有白名单不符；按生产Embedding名单和Rerank六文件核验，不改模型要求 |
| QdrantClient当context manager | 改为显式try/finally close，无生产代码回归 |
| 内存Qdrant替代真实验收 | 不能替代真实服务证据；后续已做真实局部和历史全部真实 |
| Docker移动run/禁AI/单独升级 | 另一Secrets Engine socket仍失败；不是默认路径根治 |
| 管理员/cipher /d/WSL、EFS或中文用户名猜因 | 未形成根治证据；观察不等于根因 |
| 升级后C盘新空数据盘 | 旧容器不可见；恢复D盘CustomWslDistroDir找回旧数据，原盘和备份保留 |

与恢复直接相关的错误原文/关键行：

```text
TypeError: test_graph_compiles_lazily_once_per_service.<locals>.build() got an unexpected keyword argument 'catalog_factory'
AssertionError: The standard suite must not connect to services.
PermissionError: [WinError 5]
error: patch failed: HANDOFF.md:1
error: HANDOFF.md: patch does not apply
```

隔离器AssertionError及WinError5是运行环境/检查器历史问题，不是当前工具接口业务错误。
后续已接受的571/13记录没有这些失败。

历史Day12关键行：

```text
FileNotFoundError: [WinError 3] 系统找不到指定的路径:
'C:\Users\Public\codex-pytest-rag-agent-day12\unit-20261028-01'

UserWarning: Duplicate Operation ID search_reranked_retrieval_rerank_search_post
for function search_reranked at D:\2019\rag-agent\backend\app\api\rerank.py
```

### 15. 当前错误、日志、网络与Docker外部材料

最近实际标准为652/14，0失败/0警告。当前常驻应用是否有错误、服务是否健康：**待确认**。
本轮没有采集运行时日志或探测后端/PG/Qdrant/Docker，也未检查真实会话表和数据。

以下为原Day12–15历史记录；其中“本轮/当前”属于原阶段，不是11月2日新探测结果：

**最近已执行标准：0失败/0警告。当前常驻应用是否有错误：待确认。**
本轮未采集应用运行时日志或探测服务，不能用历史成功断言当前健康。
项目日志由backend/app/core/logging.py:configure_logging输出stderr，没有固定项目日志文件。
JSONL_LOG_MARKER专用{message} handler输出机器事件，human handler排除标记避免重复。
事件retrieval_search_completed、bm25_search_completed、hybrid_search_completed、rerank_search_completed：
搜索工具成功自然产生四条；目录工具不产生这四条检索事件。
检索日志保留query哈希/长度、参数和安全身份/排名/分数；Rerank记录全部movements和耗时。
不打印原问题、Chunk正文、metadata、参数正文或State。旧分支各有分数/来源字段，不能说所有日志都没有raw score。

2026-10-30 Git直连曾失败，后用系统已有代理成功推送Day14（不是Day15）：

```text
fatal: unable to access 'https://github.com/itysrw/rag-agent.git/': Failed to connect to github.com port 443 after 21101 ms: Could not connect to server
```

已成功的历史入口（本轮不执行，今后须用户指定发布动作）：

```powershell
$env:NO_PROXY = ''
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
git -c http.proxy=http://127.0.0.1:7890 push --set-upstream origin codex/day14-langgraph
```

未改全局网络设置、未关TLS校验、未force push。当前代理可用性待确认。
历史命令中的分支是Day14，不是可直接套用的Day15发布授权；Day15是否发布/PR/合并需独立指定。

历史Docker错误原文（本轮未复采）：

```text
starting services: initializing Inference manager: listening on unix://C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: remove C:\Users\袁伟鑫\AppData\Local\Docker\run\dockerInference: The file cannot be accessed by the system. (listener: The filename, directory name, or volume label syntax is incorrect.)
```

```text
starting services: initializing Secrets Engine: listening on unix://C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock: rename C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock C:/Users/袁伟鑫/AppData/Local/docker-secrets-engine/engine.sock.stale: The file cannot be accessed by the system. (listener: The file cannot be accessed by the system.)
```

以下均为仓库外历史恢复记录，本轮未访问这些目录或复核文件/哈希；当前存在性和可用性待确认：

- 历史Docker Desktop4.97.0.244584、Engine29.9.2，不是今天查询的版本。
- `D:\Docker\Start-DockerDesktop.ps1`（历史2378字节），启动前须无Docker进程，不强杀。
- 仅为新Docker进程设置LOCALAPPDATA=`D:\Docker\codex-runtime-20261027`，恢复调用shell原值，不改系统/用户环境变量。
- 专用路径的全零字节端点Docker/run与docker-secrets-engine目录曾重命名保留；若有非零文件/子目录/链接则停止，不删数据。
- 原盘 `D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx`。
- 停机备份 `D:\Docker\docker_data.codex-pre-recovery-20261027.vhdx`，历史5,602,541,568字节，恢复前与源盘SHA256一致。
- CustomWslDistroDir=`D:\Docker\DockerDesktopWSL`曾恢复。
- 原配置备份 `C:\Users\袁伟鑫\AppData\Roaming\Docker\settings-store.codex-backup-20261027.json`。
- 升级后配置备份 `D:\Docker\settings-store.codex-post-upgrade-20261027.json`。
- 原日志 `C:\Users\袁伟鑫\AppData\Local\Docker\log\host`；规避后 `D:\Docker\codex-runtime-20261027\Docker\log\host`，旧错误曾在com.docker.backend.exe.log。
- 没有factory reset、WSL unregister、prune或覆盖数据库/VHDX，不读取Secrets存储或上传诊断。

详见 [Docker恢复记录](docs/docker-desktop-recovery.md)。默认socket问题没有已记录的根治证据；
当前是否仍触发待确认，不能把用户名/EFS猜测写成确定根因。

上面历史发布命令仅说明Day14曾经如何成功，不能直接套用为Day15/16的发布许可。
本轮新增确认：GitHub open PR=0；closed/merged历史待确认。当前代理可用性、Docker socket是否仍触发均待确认。
长期未解决：多worker会话锁、BM25全扫描/多worker快照、跨库outbox/删除同步、自然长文/表格/多跳评测、CPU p50/p95/QPS。
日志不是Day19完整trace，业务表不存Prompt/Chunk/工具参数/Token/延迟。

### 16. 不可违反的约束与禁止修改的接口

1. Python3.11、backend/、公开函数类型注解、pytest。严格按用户指定Day范围；PLAN只能在明确授权时修改，不补勾Day13、不开始Day17。
2. 当前功能开发暂停。本轮只整理六文档；新会话第一轮只读核对/复述，等待状态确认及唯一后续动作。
3. 不读取/输出.env、API Key、PG密码/Secrets，无关.agents/PDF不读、不打包、不暂存；不读取或清理模型/测试缓存。
4. 保留用户修改；不reset --hard/checkout --、force push/prune、覆盖VHDX/备份、删用户数据、改全局网络/ACL、自动重启或全量索引。
5. 保护Chat message/stream/session_id、JSON answer/model/sources/session_id、SSE Header及delta→保存→sources→DONE/错误契约；保护可信当前来源、目录文件名、固定拒答。
6. 保护原始query与独立问题分离、5个完整轮次/JSON token预算、全文存储、安全metadata、原子整轮、UUID来源校验和409互斥/取消补偿边界。
7. 公共只执行一个合法工具、内部PreparedRAG零工具且不读写会话；无工具循环/并行、checkpointer、长期画像、额外供应商/Web工具、会话管理HTTP、迁移框架。
8. 固定CPU模型/revision、query长度预检、ready安全目录50+1、HTTP错误分层不能绕过；不以RRF/logit代替原向量0.46，不让BM25-only直接生成，不静默降级。
9. 不改变受控语料/expected_phrase/顺序/质量常量隐藏失败；不把替身当真实LLM，不推算当前全真实计数，不把小样本当自然50QA评测。
10. 命令样例不是执行许可；安装、服务/DB写入、真实本地测试、付费、Git暂存/提交/发布各按用户指定范围。提交不等于推送，文件证据不等于真实环境可用。

后续实现/修复/提交遵循AGENTS运行pytest；本轮纯文档交接复用刚刚记录的652/14，明确没有重跑。
当前源码接口不因交接而改动，本轮104项保护文件与D-001至D-070正文必须保持不变。

### 17. 待完成、待确认、唯一下一步及验收

| 类别 | 状态/后续边界 |
|---|---|
| 本轮任务 | 保存A/B/C并同步六文档，完成后停止，不提交交接包 |
| 新会话唯一目标 | 只读核对Day16已完成/已勾/仅本地提交检查点，先复述后等确认及唯一动作 |
| Day15/16发布 | 均尚未发布/无上游；是否推送/PR/合并必须单独指定 |
| 六份交接文档 | 工作区保留未暂存；是否收录由用户另行指定 |
| 本地真实复验 | 当前Day16全真实组合未测，是否建表/复验和范围待指定，不猜服务/缓存 |
| 真实DeepSeek | 选择/改写准确率无本次测量；付费范围需明确，不自动探测 |
| Day13 | 既有学习证据已验、PLAN未标；理解自检/材料现存/永久归档待确认 |
| Day17以后 | 自然50QA、答案评测、完整trace、Streamlit、完整Compose等未开始，需新范围授权 |
| 外部资源 | 模型/词表/测试运行器、DB、新表、Docker、代理、D盘脚本/VHDX/备份可用性待确认 |
| 未知运行错误 | 本轮未采运行日志，不用标准成功代替服务健康 |
| 长期限制 | 多worker锁、自然语料质量/性能、BM25扫描、跨库同步和Docker根因不顺手扩展 |

新会话最多5步：
1. 完整读本包A/B/C、STATUS、DECISIONS、TODO、README、AGENTS、只读PLAN、architecture与Day16 MD/JSON。
2. 只读核对分支/HEAD115d9a2/父7494921/无上游、六文档未暂存/空暂存区及发布快照；保留全部用户修改。
3. 按第7节只读核对四节点、PG消息/Token预算、4096 token改写、单工具/UUID、SSE/补偿/参数与当前验收范围。
4. 复述当前实现、PLAN、发布和测试边界；列缺失/矛盾及最多5步，未知写待确认，漂移先报告，不恢复旧工作区。
5. 等待用户确认状态并指定唯一动作；此前不改文件、测试、操作服务、付费或改变Git/远端状态。

**下一步最小改动：0。** 没有被授权的下一项功能开发、测试或发布。
只读恢复完成判定：分支/两个Day16提交、五项勾选、六文档未暂存/暂存区空一致；
区分最新652/14、历史644/14、571/13、563/12及真实局部3/历史全真实413，区分入口已收录与真实未执行；
确认当前改写4096 token、业务PG记忆与无checkpointer、当前sources和补偿/互斥边界；所有未知不补全；返回最多5步并停等。

### 18. 本轮实际修改、保护基线与静态完成判定

仅编辑：

~~~text
HANDOFF.md
STATUS.md
DECISIONS.md
TODO.md
README.md
docs/architecture.md
~~~

原六文档已在第12节day16-handoff-20261102/original-documents及starting-six-documents.diff保留起始快照。
本轮整合先前分层旧状态为当前Day16检查点，保留决策原文、重要历史失败/否决理由及测量边界。
不是新增代码/测试/验收报告，不改PLAN或依赖，不暂存/提交/推送这份交接包。

保护范围：104个源码、测试、规范、配置、PLAN、依赖和原验收文件；D-001至D-070正文单独逐字节核对。
下面是本机工作区当前SHA256，不包含私有配置/缓存。异机行尾差异先解释，不据此覆盖用户文件。
最新完成提交报告里的92项是当时源码/测试/规范/配置/依赖保护范围，和本轮含PLAN/报告的104项不同，不混淆。

| 保护文件 | SHA256 |
|---|---|
| .env.example | 1A16476035EC0F2974AFCD8BC214AF00C1AAB135E14D4B51B1C905F10CC7F8C2 |
| AGENTS.md | 7BE7CC1A8DF4A0D5C4ED64BCDB395DDF76FDC978EFCEFB4EB2A896F8D9A2E394 |
| PLAN.md | 1B1F6809A8350FE8584704A8290550223691B5C9378D3D0E666C8E8F76F23296 |
| backend/app/__init__.py | D8369D08B20CCD2B6AA404B5D4925C92C418C439C233E0F647227F459D94792E |
| backend/app/agent/__init__.py | C0DC982AD6628CA2CBD7121525449E6BE0B884CCC95B1284ACFD65F1F4661F99 |
| backend/app/agent/graph.py | 4260533960B3F88A09D7383306A96211551CBF6A7120FAEE3D4379EA7B89017C |
| backend/app/agent/nodes.py | A4DBDAA9E09DB339C157EB4A43026642326A640B61C9283A17BE463188CA520F |
| backend/app/agent/service.py | EFA576A5FE331FB4CBA1CE1AD785C57B1248CB81B8D24DC115E36D22577C4805 |
| backend/app/agent/state.py | 869F3117E29972C5EC789F53C823B84A960018379A4FCCE5AE69198096D7E00B |
| backend/app/agent/tools.py | BABFC8F4C4E21BD43010F46BA63326265D8F66586A3441C9EE36D93675DE3889 |
| backend/app/api/__init__.py | D93B5F927D5548A8AC36FCB08FF9EA4D61844066F86244C9564B8B01C01428B4 |
| backend/app/api/bm25.py | CE2EE433F723F5558E575501DC65219634D90832DBF8D877B1F38A8022E54C8E |
| backend/app/api/chat.py | DCDB893597232ED7E81C1805ADC713D8D1AA29AEAAA8C2B09BDB5D5A66AB686F |
| backend/app/api/documents.py | 578AAC20FDC9BE5BB0BBC9EFD3CCB182E36E3B7B3ACA526B62CA8C0ADD42892B |
| backend/app/api/health.py | B017DFE00810F4771FAAC5826CAB0022C83399DE1B1465CAEBA78AC681C52B14 |
| backend/app/api/hybrid.py | F7E06FCC8E13078CA4519785D1EBCEA7C684DB279068D011F51958D9089A2E3E |
| backend/app/api/rerank.py | E6155A21329A85735BBEA1FC685CA827DF0F1FF51F522719030D19DBD63E0CB5 |
| backend/app/api/retrieval.py | 40A834661DEB9574E04C5685CD46F30A301DEFAFA104958A1A9E7443F00B28CC |
| backend/app/commands/__init__.py | 132CABC7235610FBF8D798C9CE28AB781EB88EFE4CCC630C166747E7D6D772D9 |
| backend/app/commands/embed_document.py | E38D390A8D2CF862D082C1092E1E9F3BE8AC497BA678EE0B9207CC387595AB00 |
| backend/app/commands/index_document.py | 905364E12A06826F45B232741A6B26C145255C74E7C3EC3A91A60BB6C6D816DC |
| backend/app/commands/init_qdrant.py | CEEA946C184DBC210A0AE511FC9DF90E1C60A98909DC42AB506302F32E6A2B62 |
| backend/app/core/__init__.py | 03E662EA0025DEB9738AB6653D6929F98693BD8F95FC01FF38951A80FCE034CA |
| backend/app/core/config.py | 477CDC34F848186E693BCDB683077A259C4B53B4F9C279BE7A56BBC59BBBFA01 |
| backend/app/core/database.py | 78913844214D4CBE5AEB101040B5100DDEF53E144480CDAD256EB26FAAB8A974 |
| backend/app/core/logging.py | 15DC743B55B8FFFA69AE64208810FD80585D261AD39F5562D187FA3ED10B056C |
| backend/app/main.py | C0888DD1D9141AABE6E944676421597E1F7C1EDDED20E90C23159349F088E4DD |
| backend/app/models/__init__.py | FB0B73665A2B5060BEE9601431341008C90576B6DB7F3150A6A4AE7419DA8945 |
| backend/app/models/chunk.py | 63295536DC313DBD700B6DF05C72CF544DF257E995D8F2518A40734B1604CD3E |
| backend/app/models/conversation.py | FAA4DDEB3395F59387D80019A111074695278D9351F86A0C98F795BE7A6F0B08 |
| backend/app/models/document.py | 5CCBD528DB1F10E7CFE54293300E8CD510C9DB00879653F0E34787CA170E0E4E |
| backend/app/models/init_db.py | C84F93C93D66F3D20F98F564A301729DCABD6B5953B6D5650C9E1E465220241F |
| backend/app/models/message.py | 81224CA07779C6C70963C5E895C60C53C692FD2CC5F8C1417B17A2A62D6CC2E6 |
| backend/app/services/bm25.py | D26C49BE73E8AD8133AB6AB9BF0788FBA1CB660C9A49FD092005F4AF362180B0 |
| backend/app/services/conversation_memory.py | B2513A4B83352CF3AF78B797213AE1A026C24AB5285E19828EDF4A9A79AB5EED |
| backend/app/services/document_catalog.py | 31EF98C8C75CAC86BE0A5253AEC01AA7079EF3AF71693E2EE5ED0EE85656D2A6 |
| backend/app/services/document_parser.py | D8497381BB561EED79BF38BFF02FFDC9C8F70FD23450F4E917830794A3060C90 |
| backend/app/services/document_storage.py | CF8B5E671A21C3334FC3D6D0B9352E89DEE8B957D18F53E7BFDE255E79F89C00 |
| backend/app/services/embedding.py | 5F4E20CCCCDF970ABD34A4DCAD6C06937B73C660481DA6BE3474C14518EB7AC0 |
| backend/app/services/hybrid.py | 7F501464E2D10FD541460C60A046478167492A607C100E29B50E44ADB04FC771 |
| backend/app/services/llm.py | 3BC40600A645534A11C3210A8E355E892E0BD1F37E210016AB4785F1B1C4C7EE |
| backend/app/services/qdrant_store.py | 50F016D4B027C00AE485E06B0482CB3B355E1ABDC256799379BCF27DF55E3630 |
| backend/app/services/rag.py | EC0E28DCD11017DB9878F1FCD20528E9DB4143B4481A2FC5DA66609AD5315740 |
| backend/app/services/reranker.py | F90B512DC11DA898636C1414111671EEA086393D1BC96DD655FFCD77C0AA4F86 |
| backend/app/services/retrieval.py | BA104ACB083903EBB5F12F28BD10A51B2F4BDE54481E58A02D09BAD466A23CF3 |
| backend/app/services/text_splitter.py | 0D7DCE57792EA58D795BB3636384ADFCDD6E28FB644D5EDFFA85FA3E599505FC |
| backend/requirements.txt | A2D8568A2531E650E736FF0004F416F3F13D274E9BFA117169229D38524771F7 |
| backend/tests/__init__.py | 2239E268F25B0BDE50F8614A7892719A3D9F242EC5CFCB81C9D82133AE9C3246 |
| backend/tests/conftest.py | 2BBE7AD2C59BE7FEDA6F61286D868E97CDD46D3E2B66D8277CA960FF64A7CAE7 |
| backend/tests/day10_bm25_cases.py | 9FDE794A76D1372A007F8AB5A8DE0D0387F3B0C2703AAC8A5645D47FA4BAEA1F |
| backend/tests/day9_tuning_corpus.py | 2CC6FFDB3839C8A4FF81C1F9AAD3D1E24E0D85F750036D04B2DFA4FC86D8E94E |
| backend/tests/pdf_fixtures.py | C03412BD1E9D5CB3B0603152AF6C74288C85DD29280F20E477D14DCAEC969757 |
| backend/tests/test_agent_graph.py | B6AAB6E7B9ED6F0A761BDBDF4B2DE6727C35EEB5F628FA884E20F30FA603B68A |
| backend/tests/test_agent_nodes.py | B7C8E2F69678F2B564EBBAD6AA734F6115586BEC311830D926C8FE3966B46B9E |
| backend/tests/test_agent_service.py | 9BD1F5122CC1F58A2C18018F595671FE16950F59C5DAE41E485D85C94A85308B |
| backend/tests/test_agent_state.py | 3850919830F161A1D688F61294878A4FCBD87D70D98F398652E21779C39ECA23 |
| backend/tests/test_agent_tools.py | E1425F37C7D108C320B668202D70830AB2F33E40C135BD78272D52907C2042F5 |
| backend/tests/test_bm25.py | 169CA546E5E52F785BD283D84AF38956365D26AA51CDEFBCEA69AF1E25018310 |
| backend/tests/test_bm25_api.py | A0D593C68682B1B649C7DBDB81B4C03C17D225B234F1D71D2C40607BA7E889DA |
| backend/tests/test_bm25_comparison_integration.py | 0E949EA179327EC58FC58B49EE0BA06C0C346963D69864157B537DB4CF73C4AB |
| backend/tests/test_bm25_postgres.py | FB0E5E4F6899E6CFE01BAF8F7E30ACB43C9CADF922E8F1667023CE289748CC60 |
| backend/tests/test_chat.py | 93B23A3E4ED808F4CF3BFFDD0DA98FFF42B4682DA3580811F760F21EF7E79889 |
| backend/tests/test_conversation_chat.py | 6DD8035F202A505480ED47E6476DE53D6271E6D8B465F7F95269619A0396BA45 |
| backend/tests/test_conversation_memory.py | 3179CB9B7FFA33ECC9E82641A898F706C408ACBCAFAB26A6D2639C0F2B15E1EA |
| backend/tests/test_conversation_models.py | 80998D76F2044508827E83DD6E7E2B800BAF6A5AEAF875DF0BABF4F0113E7F93 |
| backend/tests/test_conversation_postgres.py | 4171A43B59C999F1BAEBD5D4610FAF770F3849BB685E875048869802FAB6B172 |
| backend/tests/test_document_catalog.py | 4F8944BEBAD69D6A9100775854729FC6FD9097CA0DF809DCC087E45D6FB9F3DF |
| backend/tests/test_document_parser.py | C70C1221F48D2A9FD98BDFE567BA37DD312081FE85D8923DA94806D4BCBC3F6D |
| backend/tests/test_document_storage.py | FE036C46E315562A79DCA27F9956973B039DFCD0C720B98723BFFDE2DF5BCB26 |
| backend/tests/test_documents.py | BD5161FF9E2DB4293FBD5E991B32D25E6E08AAE59170250EAF4D4538DB6208B5 |
| backend/tests/test_documents_postgres.py | 56911121FFB1055482DA895630F8EC8C0EE54033710309CFF15AF69C337E1033 |
| backend/tests/test_embedding.py | 76BFFB510D388A0DC68AA32B6D4AE3605812E258BC8FD9000158A8DCC6BDF22B |
| backend/tests/test_embedding_integration.py | 3CD48FEFBE84AD7AFA5EC83607E7BD68AA5E44DA980FEBB90CBE499ED64398DD |
| backend/tests/test_health.py | 8B73FA30C8918A9DAFC61EC7F4BB0B1293D0FB1A802C8080222596C40DE2E388 |
| backend/tests/test_hybrid.py | E6DE1E120C583A17115AAC364D95D6D5B72DAF7AE05A5049B1F6A3CB4B0D8572 |
| backend/tests/test_hybrid_api.py | D1F991885768735A6CEC3B89B5189CDEDAAA2295A56CBBA485B8239C2F85DF44 |
| backend/tests/test_hybrid_comparison_integration.py | 34F04B53C8FBD22DDA74597B15F26C46E52D940952B8168BBB784456CF405F5B |
| backend/tests/test_index_document.py | 31DA1240B67213D89276B5699EC200AABD8D95A6B98A8818D7EED89B5DE3870C |
| backend/tests/test_llm.py | 7D769CAA7F84E0B7BC8DE6284A857D28E938E6AE33953FC0A0AAC5D1641E7DF0 |
| backend/tests/test_llm_tool_selection_integration.py | 820DC75018AE12E553DD17437E1A07E777A1723728BD4D96852DE1EC1077B91D |
| backend/tests/test_main.py | 0AE59168DD5D028805332EEFD374C066D7688864C8989F9E6513AA16893DEBA6 |
| backend/tests/test_qdrant_integration.py | 3C71A87D737C0482302F2F65DCC06EDACAE9EE3E0B793E13A214FBCC657EAFEF |
| backend/tests/test_qdrant_store.py | 5665C6BEA31323A0F5DB3A95CC8531E0EB50747BFB7F63B127AE80E07BF35909 |
| backend/tests/test_rag.py | 6DF3D6C398C2D103A49B8DA459E2E83344EC30987AC6B4F370C8520ED632DE6E |
| backend/tests/test_rag_integration.py | 567954D3CFAEEF7F57601B064034CD14A533DACC253EC22F9A7EE7FC306B8533 |
| backend/tests/test_rerank_api.py | ECCE325C7D7242E6B69462DF02806EDFE714D05F64092464E13A89BE6285440D |
| backend/tests/test_rerank_comparison_integration.py | E48B06AC09288E588D9C12A0F2F809AC3406085CF8BA088CDEA02AC5247975DF |
| backend/tests/test_reranker.py | 5D95AF897B0E6F614A958BAA1CE9300676253E307A00B75F0E94C1F91E8202E6 |
| backend/tests/test_reranker_integration.py | 79B296D2B0EBD4BF25D18090E0ADAA312F4FE031EDFD5E9B63E7E5CDF468010D |
| backend/tests/test_retrieval.py | 5349C40F3A56BF055356744060BB91BA15E3A302762F7EFBEDA872518CD5AE79 |
| backend/tests/test_retrieval_tuning_integration.py | 3191CC19F5F4A4819E67AAEA202711F1BD1BDF194DF8A25BB638653104811541 |
| backend/tests/test_text_splitter.py | B5FE9408CC725C68FE37F9B324894EEB43E8F97BA7834DC83FF07186E9AB3210 |
| docker-compose.yml | 704967B993637E56752B87EF9DFD8F38666DD0FA8BB3EE0BCF1843B10C959E68 |
| docs/day12-rerank-comparison.md | A2AB837A4CBDEA2A070777FBE6AEA7A43865149C9164B1933BA02511DE61A094 |
| docs/day12-rerank-results.json | 43FC6D0AD73DCA87DEA7E94B3CF15AB2F9D91F9E2D786672897C9247E31C7538 |
| docs/day14-agent-graph.mmd | D96244164AFD722A688655372E66CE6DB42FB4BBE959499C0CDE738E60594E58 |
| docs/day14-langgraph-migration.md | B81A7FE45667E04B4E2E3AA32DB779AA6BD4473279FD340D90E90A06E7B0957B |
| docs/day14-langgraph-results.json | AB62EED9F2A3440373B218773FDFB61E6D64EAF7A90ED79B129FAE0950166602 |
| docs/day15-agent-tools-results.json | 1742971325DF4AAD62AE16F6271B714A1C741DCEE953AD976F189C867D531DBE |
| docs/day15-agent-tools.md | B6677E1DC728BD521280AC9086F632D1358B99BEBE8E3F1886326AF7449E36F4 |
| docs/day15-agent-tools.mmd | B93E5200199592DCBD0E81E2C67F1FA32833EDC68760B3DFA46BA78913A77423 |
| docs/day16-conversation-memory.md | 9D6A50A45EC634756DDE345EC68A8A0249F72838B0003B3186FD6ECCC341D7B4 |
| docs/day16-conversation-memory.mmd | E08AB0364572920270C46E063F649B87851E05A9DEBAB2CAAE5E769FA7329A77 |
| docs/day16-conversation-results.json | 4CA467734BBBCAEC2BD60B792FF8C77785B2EEE5766EDD6996978CA09D7F2ECF |

静态完成判定：A/B/C完整、B≤300字符、六文档一致；本地链接有效、git diff --check通过；
104项起止SHA256相同、70条正文原字节相同，HEAD115d9a2不变、暂存区空、仅六文档未暂存；
无代码/PLAN/依赖/验收报告写入，无测试、安装、服务、下载、付费、Git写操作或全局设置变化。
本轮实际静态结果见本文件末尾的“交接收尾核验”，不能把它当作新pytest记录。

## B. 300字以内快速恢复摘要

D:\2019\rag-agent，codex/day16-conversation-memory，HEAD115d9a2、父7494921。Day16五项和日志已勾，两提交仅本地、无上游，远端未见Day15/16。PG消息表、5轮/2000token、先改写再单工具；改写4096token和失败空会话补偿已收录。11月2标准652/14（45.43s），644/14是11月1日历史；真实局部仍10月29的3，全真实10月28的413，LLM替身。六文档未暂存、暂存区空；Day13未勾、Day17未开始。开发暂停，本轮仅交接，先只读复述，等唯一动作。

## C. 新对话的第一条启动提示词

~~~text
这是一个已有项目的新工作会话，仓库 D:\2019\rag-agent。功能开发暂停。不要依赖旧聊天。

本轮唯一目标：只读核对 Day16 已完成、PLAN 已勾、本地提交尚未发布的检查点与交接包一致；先复述状态、列出矛盾或缺失及最多5步，然后等待我确认状态并指定唯一后续动作。

请完整阅读：
1. D:\2019\rag-agent\HANDOFF.md（A/B/C）
2. D:\2019\rag-agent\STATUS.md
3. D:\2019\rag-agent\DECISIONS.md
4. D:\2019\rag-agent\TODO.md
5. D:\2019\rag-agent\README.md
6. D:\2019\rag-agent\AGENTS.md
7. D:\2019\rag-agent\PLAN.md（只读）
8. D:\2019\rag-agent\docs\architecture.md
9. D:\2019\rag-agent\docs\day16-conversation-memory.md 和 day16-conversation-results.json，最新看 completion_checkpoint。

再按 HANDOFF 第7节精确文件/符号，只读核对会话表、5轮/Token裁剪、四节点图、改写/单工具、UUID来源、原子保存、SSE预取/取消/失败补偿及验收报告。

已知基线（2026-11-02 Asia/Shanghai）：
- 分支 codex/day16-conversation-memory，HEAD 115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d，提交说明 feat: complete Day 16 conversation memory；父提交 74949214e8f163fbdfa2e035993a640ab866026e 是Day16实现。
- Day16两提交仅本地、无tracking；Day15两提交也未发布。交接时只读GitHub未见Day15/16分支，master仍b68b590；Day14已发布，open PR为0。闭合PR历史及未来远端变化待确认，不用旧本地引用冒充实时远端。
- 只有HANDOFF/STATUS/DECISIONS/TODO/README/docs/architecture.md六文档未暂存，暂存区空；无关.agents/及PDF保留未读。本次交接包不提交。
- PLAN Day16五项、完成确认和日志已于11月2日按用户确认完成；Day14/15已完成；Day13四项和日志仍未标记，Day17未开始。本次交接没有改PLAN。
- 公共有历史先rewrite_query_node，无历史直接select_tool_node，再tool_node→generate_node；内部合法PreparedRAG直接生成、零工具，不读写会话。会话是PG业务消息表，不是checkpointer。
- 最近5个完整轮次最多10条，Prompt默认o200k_base/2000 token，存储不裁剪。query保留规范化原文，standalone_query用于选择和搜索；历史不是当前事实来源。
- 当前改写max_tokens=4096 token，结果长度1..4096字符；原256 token已被D-070修复。选择仍严格单调用/64KiB/JSON/UUID白名单，详情UUID只能来自原问题或截断历史。
- JSON新增session_id，SSE用X-Session-ID；成功整轮原子保存后才发sources/DONE。进程内互斥409，不等于多worker锁。首轮异常尝试清理本次新建空会话；正常close/取消不等于全部异常，不能断言所有空会话都会删除。
- 最新标准11月2日652 passed/14 skipped（45.43s），0失败/0警告、dotenv/真实连接尝试0、付费0。JSON原standard_test=644/14是11月1日历史；Day15的571/13、563/12更早。
- 最近真实局部仍为10月29日3 passed（160.84s），历史全真实为10月28日413 passed（158.94s），LLM替身；未重跑当前Day16全真实组合。
- 真实PG入口和Day15付费选择入口已新增/保留但本次未执行；后者成功一次测试会有3次付费选择。真实DeepSeek改写/选择准确率没有本次证据。
- 当前后端/Docker/PG/Qdrant、新表是否已建、缓存、临时数据、代理及仓库外备份/学习材料可用性均待确认。

执行规则：不重做已完成工作，不擅自推翻D-001至D-070，不补全未知事实。第一轮不改文件、不安装/测试、不操作服务、不下载、不暂存/提交/推送、不调用付费API，不改PLAN或开始Day17。不得读取/输出.env、凭据、无关.agents/PDF、模型或测试缓存。命令样例不是许可。
状态不一致先报告，不reset或恢复旧工作区；保留用户改动。远端若核对仅只读，不fetch/push或改全局代理。

验收：复述与本地文件/只读Git一致；明确Day16已勾且两提交仅本地、六文档未暂存/暂存区空；区分652/14、历史644/14、571/13、563/12及真实局部3/历史全真实413的日期与范围；未知标记“待确认”。给出最多5步并等待我确认状态与指定唯一动作，此前不改变仓库或外部状态。
~~~

## 交接收尾核验

2026-11-02（Asia/Shanghai），仅执行静态文件与只读Git核对，实际结果：

- A/B/C已保存，快速恢复摘要278字符；六份交接文档统一到Day16完成检查点。
- 104项保护文件起止SHA256一致；PLAN未改，SHA256为1B1F6809A8350FE8584704A8290550223691B5C9378D3D0E666C8E8F76F23296。
- D-001至D-070共70条正文逐字节未变，正文SHA256为955f98f3a3b165c7223747c95c4250aeac568f1d8271553b3b3d1eac14497bf8。
- 94处本地Markdown链接有效；44个文件的437处符号/常量行号通过静态定位检查；UTF-8、代码围栏与git diff --check通过。
- HEAD仍115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d，父仍74949214e8f163fbdfa2e035993a640ab866026e；分支/无上游未变。
- 只有HANDOFF、STATUS、DECISIONS、TODO、README、docs/architecture.md六文档修改未暂存，暂存区空；无关.agents/及PDF保留未读取。
- 本轮没有安装、pytest、应用导入、服务/数据库操作、模型下载、付费调用、Git暂存/提交/推送或全局网络修改。
- 最新已执行测试仍为11月2日提交前652 passed/14 skipped（45.43s）；本段不是新增测试报告或运行健康证明。

机器记录为第12节day16-handoff-20261102/static-verification.json；原稿和起始差异同目录保留。
后续唯一任务仍为只读恢复与状态确认，下一步最小改动0，等待用户指定唯一动作。
