# Day17 评测数据集完成记录

日期：2026-11-07（Asia/Shanghai）。用户确认 Day17 已通过审查、测试与修复，并授权同步完成状态、提交和推送。Day13 标记保持原状；Day18 评测脚本与指标尚未开始。

## 数据与审查修复

- 正式样本：[eval/eval_dataset.jsonl](../eval/eval_dataset.jsonl)，50 条；`simple_fact` 18、`cross_paragraph` 12、`multi_hop` 10、`unanswerable` 10。难度为 easy 15、medium 20、hard 15。
- 六份 Ready.gov 原版 PDF、官方地址、SHA-256 和物理页数见[语料清单](../eval/corpus_manifest.json)。原版 PDF 字节未修改；问题与参考答案为单独撰写的中文标注。
- 样本版本 `day17-v1.1` 修正 `qa_048`–`qa_050`：原题的错误前提可由语料明确反驳，不宜标为无答案；新题询问语料缺失的具体参数。其余 47 条及类别、难度分布不变。具体规则与版本记录见[数据集说明](../eval/README.md)。
- [静态测试](../backend/tests/test_eval_dataset.py)对行数、结构、分布、去重、哈希、页码、来源及上述三道题的回归条件进行离线检查。

## 实际验证与运行边界

| 验证 | 2026-11-07 结果 |
|---|---|
| 完整 `backend/tests` | **660 passed、14 skipped，122.69s**；Python 3.11.15；隔离运行中 `.env` 读取及外部服务连接尝试均为 0，付费调用 0 |
| 本地入库与索引 | 六份 PDF 通过现有上传接口入 PostgreSQL，均为 `ready`；显式本地 BGE 索引后，Qdrant `documents` 集合有 25 个对应 Point |
| 独立数据核对 | 六份已上传文件的 SHA-256 均与清单一致；逐份 PostgreSQL Chunk ID 集合与 Qdrant Point ID 集合一致，合计 25 条 |

原默认 500/100 分块会使该英文语料的部分块超过 BGE 512 token 上限。本次导入单独使用 300/60，最长 414 个 BGE token；仓库默认配置未改。入库记录保存在本机被 Git 忽略的 `data/day17-ingestion-20261107.json`，不随提交传播；其他环境须按同一语料清单另行导入。上述结果不包含 50 题的 RAG 准确率或真实 DeepSeek 质量测量。
