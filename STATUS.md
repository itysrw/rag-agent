# 项目状态

更新时间：2026-10-28（Asia/Shanghai）

## 当前检查点

- 当前模式：按用户要求暂停功能开发，仅完成文档交接。下一会话先只读核对 Day 11
  检查点、复述状态并列出待确认项，再等待用户指定唯一动作。
- 当前分支为 `master`，本地 HEAD 与 `origin/master` tracking ref 均为
  `98ff9d3860e845f47df91e366811663c71a0ec5d`；Day 10 两个提交已推送并核对实时远端。
  2026-10-27 收尾再次查询实时远端时 GitHub 443 连接失败（21063 ms），当前实时 HEAD 待网络恢复
  后复查；保留开工成功核对的发布证据，不用本地 tracking ref 替代该次实时结论。

- Day 1-9：已实现、验收并提交；Day 9 实现提交为
  `4cccbe26688de33ff25756fc10584060c82fd03f`。
- Day 9 发布状态文档已由独立提交
  `f3ca9ec1541d5e774f1eae92217d32160f15153f` 收口；Day 9 `PLAN.md` 状态由后继提交
  `5928fa0034aa0378ae164fe9bd1f38e0ca27b807` 更新。Day 10 未混入旧工作区差异。
- Day 10：独立 BM25 关键词检索已实现并通过标准、真实 PostgreSQL、真实 BGE/Qdrant
  及全量集成验收；实现提交为 `a614a365ff52b8fa087ce651614c23e2e1017c0b`。
- Day 11：独立 Hybrid API、标准 RRF、安全日志、测试与真实三路对比已完成；
  2026-10-28 用户确认审查、测试与修复通过，并授权更新完成进度。
  代码与文档尚未暂存、提交或推送；Day 12 及以后未开始。
- `PLAN.md`：Day 11 四项复选框及开发日志已按本次授权标记完成；Day 1-11 每日任务完成，
  Day 12 及以后未勾选。
- `.agents/` 是须排除的无关未跟踪目录，未纳入提交。`.env`、测试临时目录、项目内
  tiktoken 缓存和 `data/models/` 均由 Git 忽略且未纳入提交。
- 在原有 6 份未提交交接文档基础上合并更新；新增 Hybrid 服务/API/3 个测试文件、实验
  文档和 Docker 恢复记录，`main.py` 仅注册路由。无关 `.agents/` 和 PDF 保持排除。

## Day 11 已完成内容与最新证据

- 两路同步顺序各召回 20，标准等权 `1/(60+rank)`；chunk_id 聚合、稳定排序后截取
  最终严格 top_k=1..20。原始分支 score 不参与融合，响应 score 为 RRF score。
- 分支内重复 ID、跨分支同 ID payload 冲突安全失败；任一路异常整体失败，不静默降级。
- 独立 `POST /retrieval/hybrid/search`，共享请求/响应模型与可选 doc_id；422/500/502/503
  错误契约、安全 JSONL、空结果和 health lazy 均覆盖。
- 最近一次进度收口标准测试（2026-10-28）：`335 passed, 10 skipped in 57.73s`；
  10 个跳过均为显式真实集成，未新增代码修改。
- 实现阶段标准测试（2026-10-27）：`333 passed, 10 skipped in 14.39s`。
- 最近一次全部真实集成记录（2026-10-27）：开启 PostgreSQL、Qdrant、本地 BGE、RAG
  全部真实开关后 `343 passed in 35.42s`，无跳过、无失败；本轮未重跑该套件。
  LLM 使用测试替身，无付费 API 调用。
- 首次三路真实实验：`1 passed in 28.65s`；真实接口含 doc_id 的成功和空结果路径通过。
  相同 24 Chunk、12 正样本、候选 20、Top 5 的向量/BM25/Hybrid 指标分别为
  `0.750/0.917/0.812`、`0.833/1.000/0.882`、`0.917/1.000/0.944`。
- 负样本返回率分别为 1.0/0.0/1.0；RRF 不提供拒答。逐题排名、候选重合和局限见
  `docs/day11-hybrid-comparison.md`。临时 PostgreSQL/Qdrant 资源由 finally 清理并验证。
- `pip check`、`compileall -q backend`、`git diff --check` 通过；保留既有 LF→CRLF 提示。
- `/chat`、RAG `0.46`、现有两路接口、依赖、数据库 schema 和 Compose 未改动；无 Rerank。
- Docker 已升级 4.97.0，默认 C 盘 socket 仍有访问故障；D 盘进程级运行时目录方案已
  通过正常停止/重启及原有容器恢复验证。启动脚本 `D:\Docker\Start-DockerDesktop.ps1`，
  完整数据盘备份仍保留；详见 `docs/docker-desktop-recovery.md`。
- 本次完整交接仅核对文件、本地 Git、文档一致性与外部脚本/备份文件存在性；
  未重新运行代码测试、真实集成、实时远端查询或服务探测。当前运行状态待确认，
  不能把历史成功记录写成当前服务健康或当前代码全真实重新通过。
- 本次实际修改 6 份核心文档：HANDOFF、STATUS、DECISIONS、TODO、README 和 architecture；
  代码/测试、PLAN、requirements 和 Compose 的交接前后校验一致。本地失效链接 0，
  快速摘要 275 字符，`git diff --check` 通过；无暂存、提交或推送。

## Day 10 已完成内容

- 固定并安装 `rank-bm25==0.2.2`，使用 `BM25Okapi` 默认参数，不做 Day 10 调参。
- 新增 `POST /retrieval/bm25/search`，复用 Day 9 的 `RetrievalSearchRequest` 和响应结构：
  query strip 后 1..4096、严格整数 top_k 1..20（默认 5）、可选单 UUID doc_id、禁止
  额外字段。raw BM25 score 不限制在 `0..1`。
- 确定性 tokenizer：NFKC + casefold；中文连续段生成 unigram + bigram；英文、数字和
  复合编号保留完整与组成 token；query 有序去重，corpus 保留重复 TF。
- PostgreSQL loader JOIN Document/Chunk，只读取 `status=ready`，按
  doc_id/chunk_index/chunk_id 稳定排序；Session 内转 DTO，关闭后再分词和构建索引。
- 每次可搜索请求扫描 corpus 并计算 SHA-256 指纹；指纹未变复用索引，变化时在同一锁
  内完整构建后原子替换。读取或构建失败时当前请求 fail closed，不静默使用旧快照。
- 使用 `get_scores()`；只保留 query/document token 有交集的 Chunk，不用 `score > 0`，
  因而无重合不补齐无关零分结果，负分/零分真实匹配仍可返回。
- doc_id 在 Top-K 前过滤；按 `(-score, doc_id, chunk_index, chunk_id)` 稳定排序；score
  数量、类型和有限性全部校验。
- 每次成功搜索（含空结果）输出一条带 `JSONL_LOG_MARKER` 的
  `bm25_search_completed` JSONL；不记录 query 原文、query tokens、正文、metadata、SQL
  或凭据。
- PostgreSQL/配置不可用安全映射 503，非法索引或 score 映射安全 500；应用启动和
  `/health` 不解析 BM25 corpus 或连接数据库。
- `/retrieval/search`、`/chat`、RAG `0.46` 门控、上传、显式 Qdrant 索引和 collection
  契约均未修改；未实现 mode、Hybrid、RRF 或 Rerank。

## 真实向量与 BM25 对比

使用 Day 9 自撰 8 页语料，固定 500/100、Top 5。真实 PostgreSQL 与临时 Qdrant 写入
完全相同的 24 个 Chunk ID；12 个正样本分为精确编号、语义改写、混合表达各 4 题，另有
3 个知识库外负样本。

| 范围 | 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---|---:|---:|---:|
| 全部 12 题 | 向量 | 0.750 | 0.917 | 0.812 |
| 全部 12 题 | BM25 | 0.833 | 1.000 | 0.882 |
| 精确编号 4 题 | 向量 | 0.750 | 1.000 | 0.812 |
| 精确编号 4 题 | BM25 | 1.000 | 1.000 | 1.000 |
| 语义改写 4 题 | 向量 | 0.500 | 0.750 | 0.625 |
| 语义改写 4 题 | BM25 | 0.500 | 1.000 | 0.646 |
| 混合表达 4 题 | 向量 | 1.000 | 1.000 | 1.000 |
| 混合表达 4 题 | BM25 | 1.000 | 1.000 | 1.000 |

负样本返回率：向量 1.000，BM25 0.000。该结果只说明当前受控语料上的错误形态不同，
不证明 BM25 普遍优于向量，也不是 Hybrid/RRF 收益证据。逐题排名和限制见
`docs/day10-vector-vs-bm25.md`。

## Day 10 验收证据

- BM25 单元与 API 定向套件：`47 passed in 20.43s`。
- 真实 PostgreSQL 搜索、doc_id、add/update/delete 刷新和 cascade cleanup：
  `1 passed in 2.54s`。
- 相同 Chunk 的真实 PostgreSQL + BGE + Qdrant 对比：`1 passed in 41.29s`；临时
  PostgreSQL Document/Chunk 与 `day10_compare_*` collection 已清理。
- Day 10 真实模块合并复验：`4 passed in 21.80s`，覆盖真实 PostgreSQL 刷新/过滤、
  清理防御和真实 BGE/Qdrant 对比，指标保持完全一致。
- 最终标准套件：`264 passed, 9 skipped in 21.49s`；9 个跳过均为显式真实集成开关。
- 开启 PostgreSQL、Qdrant、本地 BGE 和 RAG 全部真实集成开关后，全量套件
  `273 passed in 59.39s`，无跳过、无失败。
- `pip check`：`No broken requirements found.`；`compileall -q backend`、
  `git diff --check`：通过。
- 当前失败测试：无。未调用 DeepSeek、千问或其他付费 API。

## 已知限制与残余风险

- 每次请求为计算指纹仍扫描全部 ready Chunk；多 worker 各持独立索引，不适合大规模 corpus。
- 中文 unigram/bigram 可能因常见单字产生宽泛重合；未使用停用词、同义词或领域词典。
- BM25 score 随 corpus 变化且可能为负，不能与 Cosine score 或 RAG `0.46` 直接比较。
- PostgreSQL 是 BM25 corpus，Qdrant 是向量 corpus；项目仍无跨存储自动同步、事务、outbox
  或一致性修复，实验通过相同 Chunk ID 显式保证公平性。
- 12 个正样本和 3 个负样本规模很小，且仍是受控制度语料；更大、更难、接近自然企业
  文档分布的评测集仍待后续建设。
- `%TEMP%` pytest ACL 与 LF→CRLF 历史问题未在 Day 10 修复；本轮通过独立可写 basetemp
  完成测试，`git diff --check` 只出现既有 LF→CRLF 提示，不存在 whitespace error。

## 唯一下一步

新会话只读确认 Day 11 完成检查点与 `HANDOFF.md` 一致：核对 Git/工作区、PLAN、
带日期的测试证据和 Docker 规避方式，列出矛盾及最多 5 个步骤，然后等待用户指定动作。
Day 11 已完成但未提交；不自动暂存、提交、推送、重启服务、重跑测试或开始 Day 12。
