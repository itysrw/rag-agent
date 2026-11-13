# Day19：冻结 50 题的完整 RAG 分块对照

更新时间：2026-11-14。用户授权的真实模型实验在相同的 `day17-v1.1` 50 题及 `day17-v1` 六份 PDF 上，对三套隔离的 PostgreSQL schema 与 Qdrant collection 运行完整检索、重排和生成链路。可复跑入口为 [`eval/day19_full_comparison.py`](../eval/day19_full_comparison.py)；默认不发起付费请求，真实运行须显式开启付费并设置请求上限。该实验没有修改生产默认分块、原有 collection、冻结题集或 Day18 报告。

## 口径与结果

`source_hit` 是 40 道有来源答案题的**最终可信引用全命中**；候选来源命中单列，不能与最终引用互换。150 条逐题结果均正常完成、零执行错误，已从本机 `results.jsonl` 独立复算，与汇总一致。

| 方案 | token 单位 | 完成题数 | 候选来源全命中 | 最终来源全命中 |
|---|---|---:|---:|---:|
| 200/40 | `o200k_base` | 50/50 | 33/40 | 7/40 |
| 300/60 | `o200k_base` | 50/50 | 30/40 | 6/40 |
| 500/100 | BGE tokenizer | 50/50 | 30/40 | 7/40 |

500/100（BGE token）与 200/40（o200k token）在最终来源命中上**持平**，不能写成 500/100 独占最高。两种方案使用不同的 token 计量单位，也不能把这次 BGE-token 500/100 称为原有的 o200k-token 500/100。后者在此前[不付费向量对照](day19-chunk-comparison.md)中有 7 个块超过 BGE 512-token 输入上限，因此未作为合格方案进入这次完整对照。三组各 50 题的差异也不足以证明一般意义上的最优参数。

## 运行证据与边界

- 本机忽略的汇总：`data/eval/day19_full_comparison/20261113T155106Z-8dd43008/summary.json`；逐题记录：同目录 `results.jsonl`。这些记录未纳入 Git；提交的是可复跑脚本、测试和本结论。
- 记录确认**至少 207 次**付费模型请求。中断时可能有少量在途请求，不能据此推算精确请求总数或费用。
- 独立实验 schema 与 collection 已清理；原有 Qdrant collection 保留。真实 PostgreSQL 中 Day19 `request_logs` 的在线部署和 `/chat` trace 验收仍未完成。
- 这次是隔离环境中的完整 RAG 评测，不是通过生产 `/chat` trace 观察到的分块最优结果；也不等于此前的纯向量 Top5 代理指标。Day18 正式基线仍是一次性 300/60（o200k token）下最终来源 6/40。
- 本次完整后端测试复跑为 `724 passed, 14 skipped, 0 failed`，退出码 0；被跳过的真实集成测试没有计为通过。
