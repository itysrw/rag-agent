# 项目状态

更新时间：2026-10-30（Asia/Shanghai）

**Day14 已由用户确认审查、测试与修复通过，并授权同步完成状态及本地提交。**
本提交收录 Day14 完整源码、测试、图和相关文档。提交前重新运行完整标准：
**453 passed / 12 skipped，23.34s**。未推送、未合并，Day15 未开始。

## 实现、计划与 Git

- 当前分支 `codex/day14-langgraph`；本提交为 Day14 检查点，
  精确 HEAD 用 `git log -1 --format=%H` 核验；父提交为
  `34712772b3682d174f459da91100b09f8a2493cc`（Day12）。
- 本提交共 27 个相关路径：提交前 15 个 tracked 变更（含删除 .gitkeep）、12 个新增。
  提交完成后相关改动应为 0、暂存区应为空；无关 .agents/ 与 PDF 保留且未读取。
- 2026-10-29 实时核验 Day12 远端分支为 3471277、master 为 b68b590。
  本次未查询实时远端；不把本地 tracking ref 当成当前发布证明。Day14 尚未推送。
- 按本次用户要求，将 PLAN Day14 五项任务和开发日志标记完成；
  Day1–12 原标记保留，Day13 保持未勾选，Day15 及以后未改。
- Day13 仓库外学习笔记、图和官方示例运行证据此前已核验；本次不重做或复制入仓库，
  不代替用户确认理解自检。该学习包是否永久归档仍待指定。

## Day14 已完成内容

- 固定 LangGraph 1.2.16；六字段 State、独立 response_mode Context、retrieve/generate 双节点。
- START 按 needs_retrieval 条件路由；公共 /chat 固定 True，tool_calls=()。
  False 仅支持内部合法 PreparedRAG，缺失上下文安全失败。
- complete 走 graph.invoke，stream 走同一 graph.stream 的 v2 updates + custom；
  retrieve update 预取成功后才创建 HTTP 流，保留检索错误码。
- 保留 Hybrid20→固定 CPU BGE Rerank5→原始 vector_score 0.46 门、
  Prompt、固定拒答零 LLM、后端 sources、引用清理和 JSON/SSE。
- 图惰性编译并缓存，启动/health 不访问服务或模型；
  逐 delta 背压、跨线程上下文、迭代器与 ASGI 断连清理均有回归覆盖。
- tracing 逐次关闭，内部 State 不进入 HTTP 或错误日志；无工具、会话、checkpointer 或记忆。

设计与完整证据见 [迁移报告](docs/day14-langgraph-migration.md)、
[机器记录](docs/day14-langgraph-results.json)、[实际图](docs/day14-agent-graph.mmd)、
[架构](docs/architecture.md)。D-001 至 D-058 保持原适用范围。

## 实际测试与证据边界

| 日期/阶段 | 实际结果 | 范围 |
|---|---|---|
| 2026-10-30 Day14 提交前标准 | **453 passed / 12 skipped，23.34s** | 完整 backend/tests；无警告，dotenv/外部服务连接均 0 |
| 2026-10-29 Day14 迁移后标准 | 453 passed / 12 skipped，31.10s | 迁移验收记录，新增 50 项回归 |
| 2026-10-29 Day14 真实局部 | 3 passed，160.84s | 两模块的 2 项真实测试和 1 项普通回归；真实本地检索、LLM 替身 |
| 2026-10-29 Day14 迁移前标准 | 403 passed / 12 skipped，4.11s | 迁移前完整标准基线 |
| 2026-10-29 Day12 提交前标准 | 403 passed / 12 skipped，15.93s | Day12 历史标准 |
| 2026-10-28 Day12 全部真实 | 413 passed，158.94s | 最新历史全部真实；本次未重跑真实集成 |

本次仅重跑标准测试，不操作服务、不下载模型或调用付费 API；
用户关于审查/修复通过的确认与本次实际标准测试分别记录。
本轮未改生产源码、测试或依赖；16 个已审查实现/测试/依赖文件起止哈希一致。
17 个其余保护文件未变；PLAN 是本次明确授权的状态修改。
迁移阶段 OpenAPI、15 个 RAG 辅助函数 AST 与 18 个保护文件一致的证据仍保留原日期。

## 历史质量与运行边界

2026-10-29 同一 24 Chunk/12 正样本/3 负样本：
Hybrid Hit@1/Hit@5/MRR@5=0.917/1.000/0.944，
Rerank=0.917/1.000/0.958；逐题常量和 20 候选/0 截断通过，
3 负样本固定拒答、LLM 调用 0，临时 Document/Chunk/collection 清理核验均 0。
本次没有重测这些质量数据；不能外推自然长文、表格或多跳问答。

服务与模型可用性仅在 2026-10-29 验收时确认，当前常驻服务状态未复查。
CPU、BM25 全扫描/多 worker、跨库同步与 BM25-only 保守门限制仍在；
同步上游阻塞时取消退出受原 LLM timeout（默认 60s）约束。
Docker 默认 socket 历史问题未根治，仓库外 D 盘脚本及备份保留。

## 下一步

Day14 本地提交完成后，按 [HANDOFF.md](HANDOFF.md) 只读恢复，
核对提交、空暂存区与无相关残留改动，再等待用户指定推送/合并或下一独立任务。
不自动推送、修改其他日计划或开始 Day15。
