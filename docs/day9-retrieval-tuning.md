# Day 9 检索优化实验记录

日期：2026-07-16（America/New_York）

本记录包含两部分真实实验：

1. `top_k` / `doc_id` 检索参数功能验收（真实 Qdrant）。
2. 300 / 500 / 800 chunk size 的真实检索质量对比与 BGE 上限证据
   （真实本地 BGE + 真实 Qdrant，按任务包补丁 8.B/8.C/8.D 执行）。

所有数字均来自实际运行输出，未经手工修改。

## 1. 实验环境

| 项目 | 值 |
|---|---|
| Embedding 模型 | `BAAI/bge-small-zh-v1.5`，revision `4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4` |
| 推理设备 | CPU，512 维归一化向量 |
| BGE token 上限 | `max_seq_length = 512`（含特殊 token，禁止静默截断，见 D-025） |
| Qdrant | `qdrant/qdrant:v1.18.1`，REST `127.0.0.1:6333` |
| 切分 tokenizer | `tiktoken` `o200k_base`，`disallowed_special=()`（与 Day 5 口径一致，D-019） |
| 检索 | unnamed 512/Cosine，固定 Top 5 |
| 语料与问题集 | `backend/tests/day9_tuning_corpus.py`（纯 Python 常量，补丁 8.B） |
| 测试文件 | `backend/tests/test_retrieval_tuning_integration.py` |
| 运行方式 | `RUN_QDRANT_INTEGRATION=1` + `RUN_LOCAL_EMBEDDING_INTEGRATION=1`，3 passed in 13.90s |

实验只使用以 `day9_tuning_<chunk_size>_<uuid>` 命名的一次性 Qdrant collection，
在 `finally` 中删除；不接触 PostgreSQL，也不修改正式 `documents` collection。

### Token 口径声明（补丁 8.D）

本文所有 token 数字（页长、平均 Chunk token、Top 5 上下文 token 总量）统一使用
`tiktoken o200k_base`（`disallowed_special=()`）计数。该口径**不是** BGE 自有
tokenizer（512 上限用 BGE tokenizer 单独测量，表中单列 `最大 BGE token`），也不是
DeepSeek 的精确 tokenizer，仅作为跨配置可比的统一近似成本单位。

## 2. 语料与问题设计（补丁 8.B）

语料为自撰、可公开提交、无第三方版权风险的中文《企业制度手册》，以纯 Python 常量
固定在 `backend/tests/day9_tuning_corpus.py`，每次运行完全确定、不随机、不联网。
共 8 页，主题分别为：报销与差旅、年假与请假、VPN 与远程接入、数据库备份、信息安全
与门禁、会议室使用、采购审批、新员工入职 IT。

结构设计（前置测试 `test_corpus_satisfies_the_patched_structural_contract` 强制）：

- 每页由 5 个段落（`\n\n` 分隔）组成，单页正文为 982～1011 o200k token，全部
  大于 800；每段为 194～209 o200k token；
- 每段包含固定的长审计标识。该标识用于提供确定、可复现的 o200k 长度，同时被固定
  BGE tokenizer 视为极少量 token，从而让三个配置产生不同 Chunk 数并都保持在 BGE
  512 上限内；
- 该构造是为满足三配置真实可运行性而设计的受控实验语料，不代表自然长文本的
  o200k/BGE token 比例。

固定 8 个问题，每题带一个只在一页出现的 `expected_phrase`：

| # | 问题 | expected_phrase | 相关页 |
|---|---|---|---:|
| 1 | 报销票据最晚什么时候提交给财务组？ | 每月二十五日前 | 1 |
| 2 | 入职满一年的员工每年有几天带薪年假？ | 五天带薪年假 | 2 |
| 3 | VPN 连不上应该联系哪个团队，分机是多少？ | 服务分机是 6203 | 3 |
| 4 | 生产数据库的全量备份在什么时间执行？ | 每周日凌晨两点 | 4 |
| 5 | 访客进入办公区需要办理什么手续？ | 访客登记 | 5 |
| 6 | 会议室单次预订最长可以订多长时间？ | 最长不得超过两个小时 | 6 |
| 7 | 单笔超过五万元的采购需要谁审批？ | 总经理审批 | 7 |
| 8 | 新员工的笔记本电脑多久内发放？ | 三个工作日内发放 | 8 |

## 3. 命中判据（补丁 8.C）

- 归一化定义：NFKC 规整 + 去除首尾空白（不改大小写，保留中文原义）。
- 单个 Chunk 命中某题 ⇔ 该 Chunk 的 content 归一化后，以子串方式包含该题归一化
  后的 `expected_phrase`。
- Hit@1 = Top-1 Chunk 命中记 1，否则 0。
- Hit@5 = Top-5 中任一 Chunk 命中记 1，否则 0。
- MRR@5 = Top-5 中首个命中 Chunk 的名次 r 得 1/r；无命中记 0。
- 三项指标对全部 8 题取平均。不使用任何主观判据。

## 4. 方法

三种配置：`300/60`、`500/100`、`800/160`（chunk_size / chunk_overlap，o200k token，
overlap 均为 20%）。每种配置：

1. 用 Day 5 的 `split_pages`（按页独立切分，Chunk 不跨页）切分同一份语料；
2. 在创建 collection 前用 BGE 自有 tokenizer 验证全部 Chunk 不超过 512 token，再用
   真实本地 BGE 对全部 Chunk 生成向量；
3. 每个配置写入独立的一次性 Qdrant collection，对 8 个问题使用相同的查询向量
   （BGE query instruction），固定 Top 5 检索；
4. 按第 3 节判据计算 Hit@1、Hit@5、MRR@5；每配置的 Top-5 上下文 token 总量为
   全部 8 题实际 Top-5 Chunk 的 o200k token 数之和。

## 5. 主实验结果

`DAY9_TUNING_RESULT`（8 页 × 5 段语料，8 问，Top 5）：

| 配置 | Chunk 数 | 平均 Chunk token | 最大 Chunk token | 最大 BGE token | Hit@1 | Hit@5 | MRR@5 | Top-5 context token 总量 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 300/60 | 40 | 199.3 | 209 | 62 | 1.00 | 1.00 | 1.000 | 7986 |
| 500/100 | 24 | 332.9 | 411 | 114 | 1.00 | 1.00 | 1.000 | 13590 |
| 800/160 | 16 | 499.9 | 797 | 213 | 1.00 | 1.00 | 1.000 | 18576 |

观察：

- 三种配置切出的 Chunk 数量互不相同（40 / 24 / 16），满足补丁 8.B。
- 三种配置均完成真实 BGE 编码、Qdrant 写入与 8 个问题检索，不存在缺失指标。
- 三种配置的 Hit@1、Hit@5、MRR@5 均为满分，说明当前简单事实型语料没有足够难度
  区分检索质量，而不是证明三种配置普遍等价。
- Top-5 上下文 token 总量随 chunk size 增长：7986 / 13590 / 18576。在本实验中，
  增大 Chunk 没有提高命中指标，却增加了近似上下文成本。
- 最大 BGE token 为 62 / 114 / 213，均低于 512。该结果依赖固定审计标识被 BGE
  tokenizer 高度压缩的受控构造，不能外推到普通中文长段落。

## 6. 结论与生产默认值

- 生产默认 `500/100` 保持不变：当前实验没有质量证据支持修改生产配置。
- 300 配置以相同命中指标获得最低上下文 token 总量，是后续成本优化候选，但必须用
  更大、更难且更接近自然文档分布的评测集复验。
- 不宣称任何配置"普遍最优"。
- 面试可讲点：chunk size 同时影响召回粒度和 Prompt 成本；跨 tokenizer 的计数差异
  必须显式声明和分别校验。

## 7. 局限性

1. 语料是受控构造的制度手册文本（8 页 × 5 段，主题清晰、每题单页答案），不能代表
   真实企业文档的表格、噪声和跨页场景。
2. 固定长审计标识是为同时满足 o200k 页长和 BGE 512 上限而加入的合成结构；自然文本
   的 tokenizer 比例可能完全不同，尤其不能据此断言普通 800-token Chunk 可嵌入。
3. 8 个问题全部是单页事实型问题，未覆盖跨段落、多跳和无答案类型；三配置均为满分，
   说明语料对质量没有区分度，不能得出三者等价的一般结论。
4. 判定短语子串匹配（NFKC 归一化）是保守的相关性代理：改写型答案可能被漏判，
   本实验中未出现。
5. Hit/MRR 基于固定 Top 5，未测试其他 top_k 值下的召回曲线。
6. 本实验不改变 Day 8 `/chat` 的固定 Top 5 与 `0.46` 门槛。
