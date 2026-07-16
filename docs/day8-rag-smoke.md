# Day 8 基础 RAG 验收记录

更新时间：2026-07-16（America/New_York）

## 实现边界

- `/chat` 复用 Day 7 固定 Top 5，不向请求开放 top_k、filter 或 threshold。
- 相关性门控只位于 RAG 生成层；`/retrieval/search` 保持原契约。
- 上传仍只写 PostgreSQL；必须显式执行 `index_document` 后才能被检索。
- 未实现 BM25、Hybrid/RRF、Rerank、LangGraph、多轮记忆、trace 或 Day 9 能力。

## 分数校准

使用修复后的三页中文 PDF、固定 revision BGE 和真实 Qdrant，记录每个问题的 Top-1：

| 类型 | 问题 | Top-1 页 | Top-1 score |
|---|---|---:|---:|
| 正 | 报销票据最晚什么时候交？ | 1 | 0.688781 |
| 正 | VPN 连不上应该联系谁，分机是多少？ | 2 | 0.734850 |
| 正 | 年假需要提前多久申请？ | 3 | 0.814524 |
| 负 | 月球表面温度是多少？ | 1 | 0.282149 |
| 负 | Python 如何定义一个函数？ | 2 | 0.326244 |
| 负 | 纽约今天的天气怎么样？ | 3 | 0.306839 |

当前正样本最小值 `0.688781`，负样本最大值 `0.326244`。固定门槛选择 `0.46`，位于两者
之间并保留余量。该结论只适用于当前六个受控样本；Qdrant score 是相似度而非概率，后续
仍需用更大评测集复验。

## Prompt、拒答与来源

- `LLMClient` 接收结构化 system/user messages，旧单消息方法保持兼容。
- system message 规定只根据 Context 回答、正文不可信、禁止执行正文指令和使用外部知识。
- user message 的 Context 使用 JSON，仅包含 filename/page/content。
- 低于门槛的 Chunk 不进入 Prompt。
- 没有相关 Chunk 时精确返回 `知识库中没有相关信息`，complete/stream LLM 方法调用数为 0。
- sources 由实际 Context 生成，按 filename/page 去重并保持首次检索顺序。
- 模型自由文本中的文件名、页码和 `SNN` 类来源标记由完整/流式 sanitizer 清理；
  结构化 sources 是唯一可信引用。
- JSON 返回 answer/model/sources；SSE 成功返回 delta、sources event、DONE。

## 中文 PDF fixture 修复

真实端到端首次上传失败为 PostgreSQL `DataError`。定位发现旧测试 fixture 的 Type1 字体与
BOM UTF-16BE hex string 被 pypdf 提取为带 NUL 的字节映射；第一次分数测量也因此无效。
Fixture 改为 Type0/CID `/STSong-Light`、`/UniGB-UCS2-H`、无 BOM UTF-16BE 后：

- pypdf 精确返回中文且不含 NUL；
- PostgreSQL 上传成功；
- Day 7 三个问题继续分别 Top 1 命中页 1、2、3；
- 上表为修复后的有效校准结果。

## 自动化验证

标准套件：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v

初验结果：`178 passed, 5 skipped, 1 warning in 16.43s`。加入模型来源标记清理回归后，
2026-07-16 重新运行当前标准套件，结果为
`181 passed, 5 skipped, 1 warning in 13.91s`（`186 collected`）。

真实 Qdrant+BGE 回归：

    $env:RUN_QDRANT_INTEGRATION='1'
    $env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v

结果：`2 passed, 1 warning in 14.41s`。

真实上传→显式索引→RAG：

    $env:RUN_RAG_INTEGRATION='1'
    $env:RUN_POSTGRES_INTEGRATION='1'
    $env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
    $env:RUN_QDRANT_INTEGRATION='1'
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_rag_integration.py -v

结果：`1 passed, 1 warning in 15.81s`。该测试使用真实 PostgreSQL/BGE/Qdrant、临时
collection/上传目录和 Stub LLM，验证上传、显式索引、结构化来源、知识库外拒答和完整清理。

## 真实 DeepSeek JSON/SSE 验收

2026-07-16 已在用户显式授权下执行一次真实、产生费用的验收（未加入 pytest 套件，避免每次
跑标准测试都产生费用）。复用本文档校准用的三页中文 PDF，走
`upload → index_document → /chat`，检索与 embedding 使用真实本地 BGE + 隔离的临时 Qdrant
collection，LLM 使用真实 `get_llm_client()`（`deepseek-v4-flash`），验收后已清理临时
collection、PostgreSQL 文档行和上传文件。

JSON 模式（"报销票据最晚什么时候交？"）：

    {
      "answer": "报销票据必须在每月二十五日前提交给财务组。",
      "model": "deepseek-v4-flash",
      "sources": [
        {"filename": "day8-real-deepseek.pdf", "page": 1},
        {"filename": "day8-real-deepseek.pdf", "page": 3}
      ]
    }

答案内容准确对应第 1 页原文；sources 额外带出第 3 页，符合"同一问题可能有多个 Chunk 超过
门槛"的已知行为，不是缺陷。

SSE 模式（"VPN 连不上应该联系谁，分机是多少？"）：delta 逐字拼出"VPN 故障请联系网络组，
分机是 6203。"，与第 2 页原文一致；`event: sources` 只带回第 2 页；以 `data: [DONE]` 收尾；
流式文本中未出现引用标记泄漏。

知识库外问题（"Python 如何定义一个函数？"）：精确返回固定拒答，`sources` 为空，未产生
额外 LLM 调用，与结构化测试的"不调用 LLM"契约一致。

结论：真实 DeepSeek JSON、SSE 与拒答三条路径均通过，验收记录到此为止；该验收脚本未提交
仓库，如需复跑可参考本节步骤重新编写。

覆盖边界：本次真实调用验证的是报销 JSON、VPN SSE 和 Python 门控拒答；没有单独调用
“年假需要提前多久申请？”或“月球表面温度是多少？”。因此只能结论为上述三条路径通过，
不能写成四个规划问题均已完成真实 DeepSeek 调用。当前任务已暂停，任何补充付费调用都需新授权。

## 未执行项与风险

- 门槛样本仍很小；领域、文档长度和 Chunk 分布变化后可能出现误拒绝或误接受。
- 同一问题可能有多个 Chunk 超过门槛，因此 sources 可包含多个实际 Context 页。
- 真实验收的一次性脚本和原始终端日志未保留；精确复跑脚本待确认。
- 持续 warning 为 `.pytest_cache` 的 WinError 5，不影响测试结果，根因待确认。
