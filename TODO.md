# 后续任务

更新时间：2026-10-29（Asia/Shanghai）
Day1–12任务已完成。用户已确认Day12完成，计划状态已同步，继续暂停功能开发。本提交收录Day12的26个相关文件；提交前已重跑标准测试，不操作服务。

## Day12完成清单

- [x] 固定本地CPU/safetensors BGE Reranker、惰性加载与有限安全下载。
- [x] Hybrid20→Rerank5、完整query保护、显式passage截断、稳定排序与完整movement日志。
- [x] 独立rerank API及Chat原始vector_score 0.46证据门、JSON/SSE/后端来源/拒答保留。
- [x] ReadError指数退避及质量退化普通回归，已随2026-10-29标准套件通过。
- [x] 2026-10-29已执行标准403 passed/12 skipped（45.66s），无失败、无付费调用。
- [x] 2026-10-28历史真实集成413 passed；同语料Hit@5=1.000、MRR@5=0.958、3负样本拒答零LLM。
- [x] 2026-10-29按用户确认勾选PLAN Day12四项并更新开发日志，相关状态文档同步。

- [x] 按用户要求独立本地提交Day12共26个相关文件；提交前标准403 passed/12 skipped（15.93s）。

## 等待用户指定

- [ ] 是否推送或合并Day12；本地提交尚未推送，精确哈希用git log -1 --format=%H核验。
- [ ] Day13 LangGraph的独立范围与开始时间；当前未开始，不自动推进。
- [ ] 若用户需要当前全部真实组合的再次验收，按指定范围执行并记录新日期/计数；
  现有最新全真实证据仍为2026-10-28的413，本次不重复运行。
- [ ] 按具体任务需要再核查实时远端、运行时和缓存；不为文档交接操作服务。

## 新会话恢复顺序（最多5步）

1. 阅读HANDOFF A/B/C及相关文档，确认Day12已完成、PLAN已勾选、Day13未开始。
2. 只读核对codex/day12-rerank的Day12提交、Day11 tracking ref b68b590、26个提交内文件；相关改动应为0、暂存区应为空，无关untracked保留。
3. 区分2026-10-29提交前标准403/12（15.93s）和2026-10-28全真实413，保留运行时/远端未知项。
4. 复述当前实现、计划、Git发布和证据边界，列必要待确认项。
5. 等待用户指定唯一下一动作，不自动推送、合并或开始Day13。

## 长期延后

自然长文/表格/多跳评测、CPU batch2/4/8与p50/p95/QPS、BM25扩展性/多worker、
PostgreSQL/Qdrant outbox/删除同步、BM25-only可信生成证据、Docker默认socket/历史pytest ACL、
LF/CRLF与未来迁移方案。不得为通过而改问题/expected_phrase/基线或隐藏失败。

保留提交后的工作区与所有用户修改；不读取或提交.env、凭据、无关.agents/、PDF或模型/测试缓存，
不使用git add .。恢复入口：[HANDOFF.md](HANDOFF.md)。
