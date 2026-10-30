# Day15：单次 Agent 工具调用

日期：2026-10-30（Asia/Shanghai）。分支 `codex/day15-agent-tools`，父检查点 `b76987934663f7d90603dbc4abb2432d52baf91f`。
Day14 已独立提交并发布；附件 Gate 0 的“Day14 未提交”是旧状态，本轮未重复提交 Day14。
本交付只形成独立本地 Day15 提交，不推送、不合并。原六份交接整理继续留在工作区。

## 当前行为

- “有哪些文档？”交由选择模型选择 `list_documents()`；不调用检索，来源为空。
- 用户给出 UUID 的详情问题选择 `get_document_detail(doc_id)`，UUID 必须出现在原问题中。
- 知识内容问题选择 `search_knowledge_base(query)`，实际搜索始终使用规范化原问题。
- 公共请求为 START→select_tool_node→tool_node→generate_node→END；内部 PreparedRAG 直接生成。
- 选择器非流式，`tool_choice="required"`，thinking disabled；SDK 重试为0。
  模型可能提出多个调用，后端只接受恰好一个；未知名称、错误字段、重复JSON键、非对象、坏UUID均安全502。
- 参数JSON最多64KiB UTF-8，查询1..4096字符，调用ID1..128字符；本地再次验证后执行固定白名单。

工具定义和执行位于 [tools.py](../backend/app/agent/tools.py)，选择协议位于
[llm.py](../backend/app/services/llm.py)，目录查询位于
[document_catalog.py](../backend/app/services/document_catalog.py)。
实际编译图见 [day15-agent-tools.mmd](day15-agent-tools.mmd)。

## 数据与安全契约

目录只选择 ready 文档的 id/filename/size/status/created_at，详情聚合 chunk_count；
不查询 extracted_text 或 Chunk.content，不暴露路径。列表按 created_at DESC、id ASC，
数据库最多读取51条、返回50条，并报告 truncated。Session 只在目录工具执行时创建。
缺配置、连接与超时安全503；内部SQL错误安全500；空列表/不存在文档安全200固定拒答。

文档名、结果和用户问题作为不可信JSON放入 user message，system prompt只保存静态规则。
目录工具 sources=()，生成清理保留作为答案数据的文件扩展名，继续移除页码/来源ID；
搜索及内部旧适配器保留原完整来源清理。
搜索继续 Hybrid20→CPU BGE Rerank5→原始vector_score默认0.46；不使用RRF/logit套阈值。
空结果只调用一次选择模型，生成模型0次；有上下文通常选择与生成各1次。

JSON与SSE外形不变。流在HTTP建立前依次预取选择和工具执行两个update；
随后继续同一迭代器，只暴露delta→sources→[DONE]。工具错误保持真实HTTP状态码，
生成流错误保持既有error并停止。逐段背压、跨线程推进、取消和上游关闭继续有效。
逐次关闭tracing，内部State、工具参数和工具事件不进入HTTP。

## 实际验证

| 阶段 | 结果 | 范围 |
|---|---|---|
| 图迁移前原套件 | 453 passed / 12 skipped，45.80s | 原有完整backend/tests；新增选择/目录定义尚未接入图 |
| 首次定向 | 178 passed / 1 failed | 计数测试包装器未转发新增关键字；已修正并保留断言 |
| 全量中间验收 | 562 passed / 12 skipped，62.66s | 完整标准回归通过 |
| 最终完整标准 | **563 passed / 12 skipped，44.52s，0失败/0警告** | 完整backend/tests，含4096字符转义Unicode边界 |

使用Python 3.11.15；完整suite由隔离运行器调用 `pytest.main(backend/tests -v)`，
禁用缓存和LangSmith插件，使用新独占basetemp。最终dotenv读取尝试0、外部服务连接尝试0，
离线模型、付费调用0。Windows内部socketpair仅在框架创建期间放行。
开头的目录权限和socketpair隔离器错误不是通过记录；没有通过修改业务规则或降低断言来处理。

三工具完整/流式、工具执行次数、空结果、JSON/UUID/参数校验、数据库错误分类、
安全元数据SQL、列表0/1/50/51、大小写UUID、来源清理、流预取顺序、背压、取消、
公共/内部最终调用数量、tracing和health回归均覆盖。
OpenAPI与图迁移前快照精确一致。原37项保护集中22项未变，其他项目均为规划授权的Day15改动；
PLAN、requirements、底层检索、模型/schema与历史验收文件不变。

机器结果与源文件哈希见 [day15-agent-tools-results.json](day15-agent-tools-results.json)。
原始运行器、日志和OpenAPI仅保存在本地验证产物目录，未收入仓库。

## 证据边界与剩余事项

本轮没有真实DeepSeek能力探测，也没有连接PostgreSQL/Qdrant或下载模型。
三类意图的路由由受控LLM/SDK替身验证；不能声称已经测量真实模型的选择准确率。
最近真实局部仍为2026-10-29的3项，历史全部真实仍为2026-10-28的413项，均使用LLM替身。
当前服务、模型缓存、代理和仓库外历史学习/备份现状待确认。

不修改PLAN、不开始Day16，不增加工具循环、会话/记忆、HTTP路由、表或依赖。
不读取/收录.env、.agents、无关PDF，不自动推送或合并。
DeepSeek普通工具调用与本地验证的依据：[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。
required不能在thinking开启时使用，因此选择阶段显式关闭thinking；没有启用beta strict mode。
