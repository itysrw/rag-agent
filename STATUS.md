# 项目状态

更新时间：2026-07-16（America/New_York）

## 当前检查点

- Day 1-7：已实现、验收并提交；当前提交基线为 `683f516`。
- Day 8：基础 RAG 已在本地工作区实现并验收，尚未暂存、提交或推送。
- Day 8 工作区：14 个已修改跟踪文件、4 个 Day 8 新增未跟踪文件；另有须排除的无关
  `.agents/` 和测试产物 `.pytest-tmp/`，两者均未读取或删除。
- `PLAN.md`：Day 7 已更新；本轮按要求未修改 Day 8 复选框或日志。
- Day 9 及以后：尚未开始，未经用户明确授权不得开始。

## Day 8 已完成内容

- `/chat` 普通 JSON 与 SSE 均复用 Day 7 固定 Top 5 检索。
- `RAGSettings` 在生成层使用固定相关性门槛 `0.46`，不改变 `/retrieval/search`。
- 真实三页中文 PDF 校准：正样本 Top-1 最小 `0.688781`，负样本 Top-1 最大
  `0.326244`，当前六个样本可由 `0.46` 分离。
- `LLMClient.complete_messages()` 与 `stream_messages()` 支持结构化 system/user messages；
  原 `complete(message)` 和 `stream(message)` 保持兼容。
- Context 以 JSON 放在 user message，仅包含 filename/page/content；system prompt 明确把正文
  视为不可信数据并禁止使用知识库外信息。
- 只有达到门槛的 Chunk 进入 Prompt；没有相关内容时精确返回
  `知识库中没有相关信息`，且不调用 LLM 方法。
- JSON 响应返回 `answer/model/sources`；sources 由后端按 filename/page 去重生成。
- 模型自由文本中的文件名、页码和 `SNN` 类来源标记会在完整/流式输出中被清理；
  可信来源只取后端结构化 sources。
- SSE 成功顺序为 delta → sources event → DONE；流失败只发送安全 error event。
- 检索在创建 `StreamingResponse` 前完成，因此 BGE/Qdrant 错误保留 HTTP 422/502/503。
- 上传接口、显式 `index_document`、固定 Top 5 和 Day 7 存储契约均未改变。

## Day 8 验收证据

- 开发前基线：`153 passed, 4 skipped, 1 warning in 30.41s`。
- 定向 LLM/RAG/Chat 测试：`35 passed, 1 warning in 13.06s`。
- 初验标准套件：`178 passed, 5 skipped, 1 warning in 16.43s`。
- 加入模型来源清理回归后的当前标准套件：
  `181 passed, 5 skipped, 1 warning in 13.91s`（`186 collected`）。
- 修复中文 PDF fixture 后真实 Qdrant+BGE：`2 passed, 1 warning in 14.41s`。
- 真实 PostgreSQL+BGE+Qdrant、Stub LLM 端到端：`1 passed, 1 warning in 15.81s`。
- 真实 DeepSeek 付费冒烟：报销 JSON、VPN SSE、Python 门控拒答三条路径通过；临时
  Qdrant collection、PostgreSQL 文档行和上传文件已清理，详见 `docs/day8-rag-smoke.md`。
- `pip check`、`compileall -q backend`、`git diff --check`：通过；常见密钥模式匹配 0。
- 当前失败测试：无。

## 已修复的验收基础设施问题

旧中文 PDF fixture 使用 Type1 字体配 BOM UTF-16BE hex string，pypdf 提取结果包含 NUL，
会导致 PostgreSQL `DataError`，也会使分数校准基于乱码。现改为 Type0/CID 字体、
`UniGB-UCS2-H` 与无 BOM UTF-16BE，并增加中文精确提取和无 NUL 回归测试。

## 已知警告与残余风险

- `.pytest_cache` 仍出现 `PytestCacheWarning: [WinError 5] Access is denied`；不影响通过。
- 未跟踪 `.pytest-tmp/` 是否清理待确认，不得提交。
- `0.46` 只由当前 3 个正样本和 3 个负样本校准，不是通用概率或最终质量结论；
  后续需要更大评测集重新验证。
- 一个问题可能有多个 Chunk 超过门槛；sources 反映实际 Context，而不是只返回 Top 1。
- 真实 DeepSeek 一次性脚本和原始终端日志未保留；当前没有
  `RUN_DEEPSEEK_RAG_INTEGRATION` 开关或对应 pytest。年假真实生成、月球真实拒答未单独执行。
- PostgreSQL/Qdrant 仍无跨存储事务、outbox、删除同步或一致性修复任务。
- LF→CRLF 提示与 `.pytest_cache` 权限根因仍待确认。

## 唯一下一步

等待新会话完成只读状态复述，并由用户指定是否补充真实 DeepSeek 四题全覆盖或执行检查点操作。
不得再次调用付费 API、修改 `PLAN.md`、暂存、commit、push 或开始 Day 9，除非分别获得明确授权。
