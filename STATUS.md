# 当前状态：Day21 已发布

2026-11-21。Day21 四服务 Compose 已推送至 `codex/day17-eval-dataset`，发布提交为 `0e1ee15`。同一分支包含 Day20 Streamlit（`06a8885`）与 Day19 证据筛选（`003e0a1`）。启动及接手见 [README.md](README.md#docker-compose-启动day21) 与 [HANDOFF.md](HANDOFF.md)。

| 阶段 | 已有验收证据 |
| --- | --- |
| Day21 | 四服务启动沿用已有验收。收尾的 Compose 配置测试 2 项通过，耗时 7.40 秒，覆盖默认数据卷配对和管理员令牌转发。 |
| Day20 | 发布快照离线回归 766 项通过、14 项跳过。无付费浏览器演示和 3 项 AppTest 通过。真实单轮 HTTP SSE 返回 34 段正文、同轮工具、5 条引用与 `[DONE]`，并确认同一会话的 PostgreSQL 消息和 trace 落库。[验收记录](docs/day20-streamlit.md) |
| Day19 | 固定 50 题上，生成前所选上下文的标注来源页全覆盖由 6/40 提升至 31/40。改良后的全量真实生成效果待评估。[离线对照](docs/day19-evidence-gate.md) |

---

# 历史状态：2026-11-14 Day19 初版

更新时间：2026-11-14（Asia/Shanghai）。用户确认 Day19 审查、测试与修复通过，授权同步状态并本地提交；随后授权的完整 50 题分块对照已完成。实现与部署边界见 [可观测性记录](docs/day19-observability.md)；下方 2026-11-09 及更早暂停说明为历史快照。

| 类型 | 当前事实 |
|---|---|
| 最终目标 | 企业知识库 RAG Agent；后续尚有 Streamlit 与完整 Docker Compose |
| 已完成 | Day17 冻结语料与 50 条 QA；Day18 真实评测基线；Day19 本地请求 trace、`request_logs`、受保护查询；另完成不付费的[向量对照](docs/day19-chunk-comparison.md)及授权的[完整 RAG 对照](docs/day19-full-comparison.md) |
| 真实结果 | `20261108T095705Z-real-625c1f7c53b2`，50/50 正常、0 执行错误、65/100 请求；规则准确率 11/50、候选来源 30/40、最终引用 6/40、正确拒答 8/10 |
| 测试 | 本次完整后端 pytest 724 passed / 14 skipped / 0 failed，退出码 0；14 项真实集成等测试被跳过，不计为通过 |
| 本机服务 | 使用 D 盘启动脚本恢复 Docker Engine 29.9.2；2026-11-08 18:19 左右 PG healthy、Qdrant /readyz 200；新会话实时健康待确认 |
| Git | `codex/day17-eval-dataset`；Day19 本地提交的父提交为 `a3f791bbc5c8116db2b67c7e0b6719c2513b39c0`，当前 HEAD 以 `git rev-parse HEAD` 为准；未推送或合并；两项无关未跟踪条目保留 |
| 待确认 | Day13 计划未勾；Day19 四项及完成确认证据已更新；真实 PostgreSQL 建表与 Day19 在线运行未验；远端实时状态和服务健康未验 |
| 当前阶段 | Day19 本地实现与实验已完成，用户已授权本地提交；生产 trace 尚未在线验收，Day20 未开始 |

Day18 正式报告见 [eval/eval_report.md](eval/eval_report.md)，原始逐题记录在被 Git 忽略的 `data/eval/day18/20261108T095705Z-real-625c1f7c53b2/`；关键词规则是近似评分。Day19 对同一冻结 50 题另做三方案完整 RAG 对照，未覆盖 Day18 原始基线或报告；`PLAN.md` 将 Day19 四项改为真实完成状态和事实表述。

不付费向量对照中，原 o200k-token 500/100 有 7 个块超过 BGE 输入上限；合格组 200/40、250/50、300/60 的纯向量 Top5 全页命中为 21/40、16/40、22/40。另一次授权的完整 RAG 对照中，200/40（o200k）与 500/100（BGE token）最终来源均为 7/40，300/60（o200k）为 6/40；500 并未独占最高，两种 500/100 不可混称。150/150 逐题完成，至少 207 次付费请求，精确费用未知；隔离实验数据已清理，原有 Qdrant collection 保留。

---

# 历史档案：2026-11-08 Day17 交接时的状态

> **当前检查点（2026-11-08）**：`codex/day17-eval-dataset` 的 HEAD `6f252c24dd42bdd1fc52e4dc7f7beb822ec999de` 已推送并与只读核对的远端分支一致，尚未合并 `master`。Day17 的 50 条 `day17-v1.1` 样本、六份原版 PDF 和四项 PLAN 已完成；11月8日隔离完整标准 660 passed/14 skipped、退出0，本机11月7日六文档 ready、Qdrant 25 Point。Day13 未勾、Day18 未开始，功能开发暂停。
> 六份交接文档仍含未暂存改动，暂存区空；本轮更新的交接包也只留在本地。当前服务健康与 50 题真实准确率待确认。完整 A/B/C 见[HANDOFF.md](HANDOFF.md)；下方 2026-11-02 的分支/HEAD/“Day17 未开始”仅为历史快照。

## 2026-11-08 当前状态

| 类型 | 事实 |
|---|---|
| 已完成 | Day14–17 对应实现和计划标记（Day13 仍未勾）；Day17 `day17-v1.1` 50 条 QA、六份原版 PDF、离线测试及 11月7日本机六文档/25 Point 入库核验；`6f252c2` 已推送 |
| 正在做 | 仅保存本轮交接包；不继续开发、操作服务、暂存、提交或推送 |
| 待完成 | Day18 评测脚本和真实指标、Day19 trace、Day20–25 前端/交付；Day13 计划标记待用户单独决定，不能自动补勾 |
| 仍待确认 | 当前 Docker/PG/Qdrant/后端健康、50 题真实 RAG 表现、当前模型准确率、其他机器数据是否导入；历史 open PR 已只读核对为 0，closed/merged 历史未核 |

Day17 代码和数据文件、命令、决策原因、失败方案、日志及下一会话验收见[当前 HANDOFF A/B/C](HANDOFF.md)。

---

# 项目状态

更新时间：2026-11-02（Asia/Shanghai）

功能开发暂停；本轮仅整理交接文件，未运行测试、安装、操作服务、下载、付费、暂存/提交/推送。
完整A/B/C、精确代码定位、失败原文、命令和验收见[HANDOFF.md](HANDOFF.md)。
开发规范见[AGENTS.md](AGENTS.md)，技术决策见[DECISIONS.md](DECISIONS.md)。

## 当前检查点

| 项目 | 已核对状态 |
|---|---|
| 仓库/分支 | D:\2019\rag-agent / codex/day16-conversation-memory |
| HEAD | 115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d |
| 提交说明/时间 | feat: complete Day 16 conversation memory / 2026-11-02T08:13:29+08:00 |
| 父提交 | 74949214e8f163fbdfa2e035993a640ab866026e，feat: implement Day 16 conversation memory |
| Day15完成/实现 | a006139f4ae1406c5f20144730c76fe122d0c2bc / 4ce29aa634ae4deaf975dc6380746686b0d78469 |
| 上游/发布 | Day16、Day15均无tracking；两日各两提交仅本地，未合并master |
| 本轮只读GitHub分支 | 只有Day12、Day14、master，未见Day15/16 |
| Day14已发布 | b76987934663f7d90603dbc4abb2432d52baf91f |
| master | 本地、origin缓存及本轮远端均b68b590c8262eb568a371c895e4f7033456d045c |
| open PR | 本轮只读列表0；closed/merged历史待确认 |
| 未暂存tracked | 仅HANDOFF、STATUS、DECISIONS、TODO、README、docs/architecture.md六份文档 |
| 暂存区 | 空；本轮交接包不提交 |
| 无关untracked | .agents/、就业推荐表_完整填充版.pdf，保留未读取 |

发布与提交分开判断；历史验收报告的“尚未推送”不代表当前远端。
本轮远端快照见HANDOFF第2节，之后如需核对仍用只读方式，不fetch/push。

## 已完成

| 阶段 | 当前结果 |
|---|---|
| Day1–5 | FastAPI、compatible LLM JSON/SSE、安全错误、PDF/MD/TXT与PostgreSQL Document/Chunk |
| Day6–9 | 固定CPU BGE、显式Qdrant索引、可信来源/原向量证据门、严格检索API、受控实验 |
| Day10–12 | BM25、等权RRF60、固定CPU BGE Rerank、Hybrid20→Rerank5及结构化排名日志 |
| Day13 | 仓库外学习证据/官方无Key示例此前已验；四项及日志未勾，不自动补标 |
| Day14 | 惰性图、条件边、预取/背压/跨线程取消、内部PreparedRAG适配；五项/日志已勾并发布 |
| Day15 | 严格单工具、ready安全目录50+1、UUID来源校验、目录文件名8条回归、默认关闭付费入口；四项/日志已勾，仅本地 |
| Day16实现7494921 | PG业务消息、5个完整轮次/2000 token、指代改写、四节点、session_id、事务/409/取消 |
| Day16完成115d9a2 | 已审查的改写4096 token及新建空会话失败补偿收录，8条新增回归；五项、完成确认和日志于11月2日按用户确认完成 |

用户确认审查、测试与修复通过；不虚构独立审查记录或真实DeepSeek准确率。
[PLAN.md](PLAN.md)本轮不改；Day13未勾，Day17以后未开始。

## 当前实现

POST /chat接受message、stream、可选session_id；JSON增加session_id，SSE通过X-Session-ID返回它。
省略/null创建新会话；历史按sequence_no取最新10条并校验成对，读完立即关闭DB Session。
默认o200k_base/2000 token，保留最新5个完整user+assistant轮次；配置token范围128..16000，存储全文。

无历史：select_tool_node→tool_node→generate_node；有历史：rewrite_query_node→上述三节点。
改写为严格JSON、非流式、thinking关闭、SDK retry0、max_tokens=4096；独立问题仍1..4096字符。
query保留原问题；standalone_query用于选择和搜索。详情UUID必须来自原问题或本次截断历史。
只选择并执行search_knowledge_base/get_document_detail/list_documents之一；内部PreparedRAG零工具且不读写会话。
搜索保持Hybrid20→CPU Rerank5→原始vector_score默认0.46，BM25-only不生成；目录sources=[]。
Prompt规定当前工具结果为事实依据；后端sources只取本次结果，不复制历史来源。

完整生成成功才同事务保存原始user、完整清理后的assistant及当前安全sources。
进程内同session互斥409，保存前取消整轮回滚；不是多worker分布式锁。
SSE同迭代器在HTTP前预取必要改写/选择/执行，delta背压，保存后sources/DONE，错误停止；关闭链路幂等。
115d9a2在首轮选择/生成/保存异常时尝试删除本次新建且仍为空的会话；已有/非空会话不删。
正常close/断开不保证删除空会话；已提交完整轮次后网络失败不能撤回，不宣称commit与客户端DONE原子。
公共拒答仍有选择1次，有历史再有改写1次，只省最终生成；内部PreparedRAG拒答才是总LLM0。
业务PG消息不是LangGraph checkpointer；无循环、并行、长期画像或认证/会话管理API。

## 已执行验证与当前失败

| 时间/范围 | 结果 |
|---|---|
| 2026-11-02最新完整标准 | **652 passed / 14 skipped，45.43s；0失败/0警告；dotenv/服务连接尝试0、付费0** |
| 2026-11-01原Day16标准 | 644 passed / 14 skipped，18.83s，历史 |
| 2026-10-31 Day15完成 | 571 passed / 13 skipped，34.70s，历史 |
| 2026-10-30 Day15实现 | 563 passed / 12 skipped，44.52s，历史 |
| 2026-10-29最近真实局部 | 3 passed，160.84s，PG/Qdrant/本地模型真实，LLM替身 |
| 2026-10-28历史全部本地真实 | 413 passed，158.94s，Day12历史、LLM替身，不是当前Day16全真实 |

最新读[Day16 JSON](docs/day16-conversation-results.json)的completion_checkpoint.standard_test；
顶层standard_test=644/14、改写256 token及PLAN未变是11月1日快照，不覆盖最新4096和PLAN已完成。
[Day16 MD](docs/day16-conversation-memory.md)、[Day15 MD](docs/day15-agent-tools.md)保留阶段边界。
14跳过=原12可选真实集成+付费选择1+真实PG记忆1。
真实选择入口已新增但未执行；成功一次会有3次付费选择，不执行工具/生成；没有真实改写准确率结论。
本轮未重跑测试。最新接受标准失败0；当前运行错误/日志待确认，不等于服务健康。

## 待确认与后续边界

后端、Docker/socket、PG/Qdrant、新会话表、缓存/词表、临时数据、代理和仓库外材料可用性待确认。
当前Day16全真实组合未重跑；没有真实DeepSeek选择/改写质量结论。
多worker锁、BM25全扫描/多worker快照、跨库同步、自然语料/表格/多跳质量和CPU p50/p95/QPS是限制，不顺手扩展。
Day17自然50QA、答案评测、Day19完整trace、Streamlit和完整Compose未开始。

唯一下一步：新会话完整读HANDOFF A/B/C及相关文件，只读核对本检查点，复述状态、列缺失/矛盾和最多5步；
然后等待用户确认并指定唯一动作。下一步最小改动0；此前不改文件、测试、服务、PLAN或Git/远端状态。

本轮只同步六文档；104项源码/测试/规范/配置/PLAN/依赖/验收报告与70条决策正文的核验记录见HANDOFF末尾。
