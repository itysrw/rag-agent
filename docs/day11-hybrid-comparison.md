# Day 11 纯向量、BM25 与 Hybrid 真实对比

日期：2026-10-27（Asia/Shanghai）

任务完成确认：2026-10-28，用户确认审查、测试与修复通过；`PLAN.md` Day 11 四项任务
及开发日志已按授权标记完成。本轮标准回归为 `335 passed, 10 skipped in 57.73s`；
下文实验指标及 `343 passed` 真实集成证据保留 2026-10-27 原始记录，本轮未重跑真实集成。

## 1. 实现契约

新增独立 `POST /retrieval/hybrid/search`，复用严格的 `query/top_k/doc_id` 请求和 Chunk
响应结构：query strip 后 1..4096 字符，top_k 为严格整数 1..20、默认 5，可选单 UUID
doc_id，禁止额外字段。

生产固定按向量 → BM25 的顺序同步调用，两路各召回最多 20 条。使用标准等权 RRF：

```text
RRF(chunk) = Σ 1 / (60 + rank_i(chunk))
rank 从 1 开始；缺席某一路贡献为 0。
```

按 chunk_id 聚合两路并集，不按正文、页码或文件名去重。同一分支重复 ID 被拒绝；跨
分支同 ID 的 doc_id、chunk_index、content、page、filename、metadata 必须一致，原始
分支 score 不参与检查。排序键为 `(-rrf_score, best_rank, doc_id, chunk_index, chunk_id)`，
排序后才截取最终 top_k。融合不修改输入列表或输入 metadata。
metadata 的键顺序可以不同，但标量值的类型必须一致，`true`、`1` 和 `1.0` 不能互相替代。

响应 score 为 RRF score，不是概率、Cosine 或 BM25 score，不能套用 RAG 的 `0.46`。
任一路失败整体失败，不静默返回单路结果。HTTP 契约：非法请求/BGE 超限 422，BM25
内部索引/计算失败 500，非法向量结果/同 ID payload 冲突 502，分支不可用 503；合法
空结果 200。

成功请求自然产生向量、BM25、Hybrid 三条完成日志。Hybrid 事件仅记录 query 哈希与
长度、参数、候选数、结果身份、两路 rank、RRF score；不记录 query、正文、tokens、
metadata、向量或原始分支 score。分支日志继续遵守 Day 9/10 原有契约。

## 2. 环境与公平性

| 项目 | 实际配置 |
|---|---|
| Python | 3.11.15 |
| Embedding | 本地 CPU `BAAI/bge-small-zh-v1.5`，固定 revision `4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4` |
| 向量 | 512 维归一化，Qdrant unnamed Cosine |
| Qdrant | `qdrant/qdrant:v1.18.1`，真实 REST 服务 `127.0.0.1:6333` |
| PostgreSQL | `postgres:16-alpine`，真实 PostgreSQL Document/Chunk |
| BM25 | `rank-bm25==0.2.2`，BM25Okapi 默认参数，Day 10 tokenizer |
| 语料 | Day 9 自撰 8 页企业制度手册，500/100，`o200k_base`，24 Chunk |
| 问题 | Day 10 固定 12 个正样本，3 个知识库外负样本 |
| 候选/评估 | 向量与 BM25 各最多 20，统一评估 Top 5，RRF k=60 |

实验先写 PostgreSQL，再读取这 24 个 Chunk；相同 UUID、正文、页码、文件名和 metadata
被显式写入一次性 Qdrant collection。BM25 使用且仅使用这份 corpus，向量查询对应
collection，避免两个库内容不同。没有接入 LLM，也没有进行付费 API 调用。

另通过真实 HybridService + FastAPI TestClient 验证接口：`6203`、top_k=1、真实 doc_id
返回正确目标与 RRF score，内部 rank 不出现在响应；未知合法 UUID 返回 200 空数组。
该测试替换的仅是服务装配，执行的是实际本地 BGE、PostgreSQL 读取和 REST Qdrant 检索。

命中规则沿用 Day 9/10：NFKC + 首尾 strip 后，Chunk 正文包含固定 expected_phrase。
Hit@1、Hit@5、MRR@5 只比较排名；负样本返回率单独统计。

## 3. 三路聚合结果

| 范围 | 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---|---:|---:|---:|
| 全部 12 题 | 向量 | 0.750 | 0.917 | 0.812 |
| 全部 12 题 | BM25 | 0.833 | 1.000 | 0.882 |
| 全部 12 题 | Hybrid | 0.917 | 1.000 | 0.944 |
| 精确编号 4 题 | 向量 | 0.750 | 1.000 | 0.812 |
| 精确编号 4 题 | BM25 | 1.000 | 1.000 | 1.000 |
| 精确编号 4 题 | Hybrid | 1.000 | 1.000 | 1.000 |
| 语义改写 4 题 | 向量 | 0.500 | 0.750 | 0.625 |
| 语义改写 4 题 | BM25 | 0.500 | 1.000 | 0.646 |
| 语义改写 4 题 | Hybrid | 0.750 | 1.000 | 0.833 |
| 混合表达 4 题 | 向量 | 1.000 | 1.000 | 1.000 |
| 混合表达 4 题 | BM25 | 1.000 | 1.000 | 1.000 |
| 混合表达 4 题 | Hybrid | 1.000 | 1.000 | 1.000 |

负样本返回率：向量 1.000，BM25 0.000，Hybrid 1.000。Hybrid 仍接纳向量分支的最近邻，
即使 BM25 无重合也会返回结果；这符合两路并集契约，不等于具备拒答能力。

## 4. 每题排名与候选重合

`-` 表示预期短语未进入 Top 5。候选重合率为两路 Top 20 的 Jaccard：交集数/并集数。

| 类别 | 问题 | expected_phrase | 向量 | BM25 | Hybrid | 候选重合率 |
|---|---|---|---:|---:|---:|---:|
| 精确编号 | `6203` | 服务分机是 6203 | 4 | 1 | 1 | 0.050 |
| 精确编号 | 五万元采购 | 总经理审批 | 1 | 1 | 1 | 0.450 |
| 精确编号 | 网络组 | 服务分机是 6203 | 1 | 1 | 1 | 0.150 |
| 精确编号 | 全量备份 | 每周日凌晨两点 | 1 | 1 | 1 | 0.500 |
| 语义改写 | 远程接入工具坏了应该找谁处理？ | 服务分机是 6203 | - | 3 | 3 | 0.739 |
| 语义改写 | 新人多久能拿到办公设备？ | 三个工作日内发放 | 1 | 4 | 1 | 0.739 |
| 语义改写 | 差旅单据交财务的截止日是什么时候？ | 每月二十五日前 | 2 | 1 | 1 | 0.667 |
| 语义改写 | 周末什么时候做整库备份？ | 每周日凌晨两点 | 1 | 1 | 1 | 0.727 |
| 混合表达 | VPN 出错后拨打哪个 6203 服务？ | 服务分机是 6203 | 1 | 1 | 1 | 0.667 |
| 混合表达 | 采购超过五万元要找最高负责人审批吗？ | 总经理审批 | 1 | 1 | 1 | 0.739 |
| 混合表达 | 访客登记后如何进入办公区？ | 访客登记 | 1 | 1 | 1 | 0.739 |
| 混合表达 | 会议室最多能占用多久？ | 最长不得超过两个小时 | 1 | 1 | 1 | 0.636 |

- 平均候选重合率：0.567（逐题三位小数后取平均）。
- 逐题累加的单路独有候选数：仅向量 87，仅 BM25 24。这是 query/Chunk 对数，
  不是跨所有问题去重后的 Chunk 数。
- 单路独有正确候选命中：仅向量 0 题，仅 BM25 0 题；每题正确目标在两路 Top 20 均存在。
- Hybrid 补回向量 Top 5 漏检 1 题，补回 BM25 Top 5 漏检 0 题。远程接入问题的向量
  候选第 7、BM25 第 3，融合后进入第 3；本次收益来自排名重组，没有新增候选级正确目标。
- `6203` 保留 BM25 的第 1；新人设备问题保留向量的第 1；差旅截止问题从向量第 2
  提升为第 1。这说明两路提供互补排名信息，但没有证明普遍收益。

## 5. 局限与后续边界

1. 仅 24 Chunk、12 正样本和 3 负样本，均来自受控自撰手册；固定审计标识被 BGE 高度
   压缩，不能外推到自然长文本、复杂表格或跨页知识。
2. 语义改写仍保留部分字面重合；中文 unigram/bigram 也会引入常见单字重合。
3. 未根据结果调整 k、权重或 tokenizer；结果没有被用来宣称 Hybrid 必然优于两路。
4. RRF 是排序方法，不提供拒答或经过校准的相关性分数，不能直接接入 Day 8 的门槛。
5. PostgreSQL/Qdrant 仍依靠显式索引，无 outbox 或自动删除同步。同 ID payload 检查只
   覆盖共同返回的候选，无法发现所有缺失/未索引内容；单路独有候选仍允许进入结果。
6. BM25 每请求扫描 ready Chunk 计算指纹，多 worker 各有快照；当前实现不适合大规模
   corpus。两路顺序执行的延迟尚未作为正式性能指标评测。
7. 未修改 `/chat`、RAG 门槛、现有两路接口、数据库 schema 或依赖；未实现 Day 12 Rerank。

## 6. 复验与清理

```powershell
$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/test_hybrid_comparison_integration.py -v -s
```

首次真实三路实验 `1 passed in 28.65s`，输出标识
`DAY11_HYBRID_COMPARISON_RESULT`。三路聚合指标和每题 Hybrid 排名已固定为真实集成回归
基线。测试在 `finally` 中删除临时 Qdrant collection 并验证不存在，再关闭客户端；
无论 Qdrant 清理是否成功，都会删除 PostgreSQL Document 并验证 Chunk 级联清理。

实现阶段（2026-10-27）标准套件 `333 passed, 10 skipped in 14.39s`；开启全部真实集成后
`343 passed in 35.42s`，三路指标与首次实验一致。完整证据见 [STATUS.md](../STATUS.md)。
Docker 恢复过程独立记录在
[Docker Desktop 恢复记录](docker-desktop-recovery.md)，不把之前内存 Qdrant 的初步试验
当作最终真实服务证据。
