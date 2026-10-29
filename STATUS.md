# 项目状态

更新时间：2026-10-29（Asia/Shanghai）
**Day1–12每日任务已完成。** 用户于2026-10-29确认Day12完成并授权同步计划与相关状态；
完成标记更新后继续暂停功能开发，等待用户指定下一动作。

## 当前实现、计划与Git

- Day11发布检查点为b68b590c8262eb568a371c895e4f7033456d045c，2026-10-28独立提交、推送并实时核验。
- 当前分支codex/day12-rerank；本提交收录Day12，精确HEAD用git log -1 --format=%H核验。本地origin/master tracking ref仍为Day11的b68b590；当前实时远端未查询。
- Day12四项任务及PLAN.md开发日志已勾选/标记已完成。Day13及以后未开始、未勾选。
- Day12本地提交包含26个相关文件：提交前17个tracked修改、9个相关新增。提交完成后相关改动应为0、暂存区应为空；Day12尚未推送。
- 排除.agents/、就业推荐表_完整填充版.pdf、.env、凭据、模型/测试缓存。推送或合并等待用户另行指定。

## Day12已完成内容

- 固定本地CPU BAAI/bge-reranker-base，revision 2cfc18c9415c912f9d8155881c133215df768a70；
  safetensors、禁止remote code、512 token、默认batch4、缓存优先与惰性加载。
- Hybrid20→CrossEncoder原始logit→Rerank5，稳定排序、完整候选movement、安全日志，
  保护完整query、只显式截断passage并记计数。
- 独立POST /retrieval/rerank/search仅query/doc_id；Hybrid保留原始分数但不用于RRF或公开响应。
- Chat完整新链路，Rerank Top5后使用原始vector_score默认0.46证据门，BM25-only不作为生成依据；
  固定拒答不调用LLM，JSON/SSE、后端sources和引用清理保留。

## 实际测试与证据边界

| 日期/阶段 | 实际结果 | 范围 |
|---|---|---|
| 2026-10-29本地提交前标准回归 | **403 passed / 12 skipped，15.93s** | 真实集成关闭、模型离线、假LLM，无付费调用 |
| 2026-10-29完成状态收口标准回归 | **403 passed / 12 skipped，45.66s** | 真实集成关闭，假模型/假LLM，无付费调用 |
| 2026-10-28 Day12标准 | 401 passed / 12 skipped，17.93s | 历史版本记录 |
| 2026-10-28 Day12全部真实 | 413 passed，158.94s，无跳过 | PostgreSQL/Qdrant/BGE/Reranker真实，LLM替身 |
| 2026-10-28 Day11发布前 | 335 passed / 10 skipped，1333.56s | 随后独立发布b68b590 |

最近一次标准套件覆盖后续新增的ReadError指数退避和质量退化普通回归，当前标准失败数0。
本次本地提交前重新运行标准403/12；未重跑全部真实集成，最新全真实证据仍为2026-10-28的413，不能写成今天重新通过。
后续修复作者与独立审查记录未补查；本次提交整理未修改既有源码或测试。

## 历史真实效果与运行边界

2026-10-28同24 Chunk/12正样本：Hybrid 0.917/1.000/0.944，Rerank 0.917/1.000/0.958
（Hit@1/Hit@5/MRR@5）；3负样本固定拒答，LLM调用0。Hit@1没有提升，无关候选升位也有记录。
原实验见[Day12报告](docs/day12-rerank-comparison.md)与[JSON](docs/day12-rerank-results.json)。

模型新实例加载2.832s、首次predict6.562s、热predict6.291s，来自已缓存权重的同进程测量，
不是系统物理冷启动。受控语料不能外推自然长文/表格/多跳，CPU、BM25全扫描/多worker快照、
跨库无outbox/同步与BM25-only保守门的限制仍在。

2026-10-28最后确认PG running/healthy、Qdrant running，独立核验临时资源均0；
本次未探测或操作服务。当前运行时/远端/模型缓存可用性待确认。
Docker默认socket未根治，仓库外D盘脚本和备份的历史规避保留。

## 本次本地提交与唯一下一步

2026-10-29用户明确要求提交Day12。本提交收录完整实现、测试、PLAN完成标记、实验记录及同步后的状态文档，共26个相关文件；未开始Day13。

提交前标准回归首次因新临时目录写入权限报错（322 passed/12 skipped/81 errors，47.57s）；取得本次测试所需权限后使用新的独占目录重跑，403 passed/12 skipped，15.93s，无代码修改。未操作服务、下载模型或查询实时远端。

源码/测试、依赖、Compose及原实验JSON保持原样；只同步八份计划/状态/说明文档中的提交状态与测试记录。无关.agents/与PDF保持在提交外。

唯一下一步：新会话先按[HANDOFF.md](HANDOFF.md)只读恢复，确认Day12已本地提交且未推送、PLAN已勾选、标准403/12与历史全真实413的日期边界，再等待用户指定唯一后续动作。
