# 技术决策记录

更新时间：2026-07-15（America/New_York）

## D-001：以 25 天计划控制范围

- 状态：已确认
- 决策：`PLAN.md` 是每日范围和顺序的唯一计划基线。
- 原因：避免在早期同时引入数据库、检索、Agent 和前端，确保每个阶段可验收。
- 影响：未经用户明确要求不得跨 Day 实现；未经明确授权不得修改 `PLAN.md`。

## D-002：Day 2 起使用模块化 FastAPI 结构

- 状态：已确认
- 决策：入口位于 `backend/app/main.py`，路由位于 `backend/app/api/`，配置位于
  `backend/app/core/`，服务位于 `backend/app/services/`。
- 原因：后续 LLM、文档、检索和 Agent 可独立演进，避免所有逻辑堆积在 `main.py`。

## D-003：Day 3 只接 DeepSeek

- 状态：已确认
- 决策：Day 3 不同时接入 OpenAI API 或通义千问。
- 原因：用户已有 DeepSeek 额度；一次只验证一个供应商可降低配置、计费和测试复杂度。
- 已否决：Day 3 同时接 DeepSeek 和千问。

## D-004：使用 `deepseek-v4-flash`

- 状态：已确认
- 决策：模型名为 `deepseek-v4-flash`，Base URL 为 `https://api.deepseek.com`。
- 原因：DeepSeek 官方说明 `deepseek-chat` 和 `deepseek-reasoner` 将于北京时间
  2026-07-24 23:59 停用；V4 Flash 成本低、支持兼容接口、流式和工具调用。
- 已否决：继续使用 `.env.example` 原来的 `deepseek-chat`。

## D-005：Day 3 默认关闭 DeepSeek 思考模式

- 状态：已确认
- 决策：`LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}`。
- 原因：Day 3 的目标是普通对话和 SSE；默认思考会增加 `reasoning_content`、解析复杂度、延迟和费用。
- 影响：以后需要推理时可通过配置启用，不应改写客户端。

## D-006：LLM 客户端保持 OpenAI-compatible

- 状态：已确认
- 决策：`LLMClient` 使用 OpenAI Python SDK 的 `chat.completions.create`，只依赖
  API Key、Base URL、model、timeout 和不透明 `extra_body`。
- 原因：未来切换通义千问或 OpenAI-compatible 服务时不重写客户端。
- 禁止：在 `LLMClient` 中根据 `provider == "deepseek"` 编写分支。

## D-007：同一个 `/chat` 支持两种响应模式

- 状态：已确认
- 决策：`stream=false` 返回完整 JSON，`stream=true` 返回 SSE。
- 原因：保持接口数量小，并直接满足 Day 3 的非流式和流式要求。
- SSE 契约：增量为 `data: {"delta":"..."}`，最终为 `data: [DONE]`。

## D-008：同步 SDK 调用运行在 FastAPI 同步路由中

- 状态：已确认
- 决策：`chat()` 使用普通 `def`；FastAPI 在线程池运行同步路由。
- 原因：OpenAI-compatible 同步 SDK 足够满足 Day 3，避免阻塞事件循环，也不提前引入异步客户端双实现。

## D-009：配置和上游错误不得泄露供应商细节

- 状态：已确认
- 决策：缺少 Key 返回通用 `503`；普通上游失败返回通用 `502`；流错误返回通用 SSE error。
- 原因：避免将凭据、供应商响应体或内部异常暴露给调用方。

## D-010：真实 API 与单元测试分离

- 状态：已确认
- 决策：pytest 使用 `StubLLMClient` 和 fake SDK，不消耗外部额度；真实 DeepSeek 调用是独立验收步骤。
- 原因：测试必须稳定、快速、可离线运行，不能依赖账户余额或网络。

## D-011：ChatGPT Plus 不等于 OpenAI API 额度

- 状态：已确认
- 决策：当前 ChatGPT Plus 仅作为开发辅助，不作为项目后端 API 来源。
- 原因：ChatGPT 与 OpenAI API 分开管理和计费；用户尚未确认 OpenAI API 余额。

## D-012：Day 6 Embedding 供应商延后决定

- 状态：待确认
- 候选：OpenAI、阿里云百炼/通义千问、本地 `BAAI/bge-small-zh-v1.5`。
- 原因：当前没有文档语料、运行环境和质量/成本测试，不能提前做可靠选择。
- 禁止：在 Day 3 提前实现 Embedding。

## D-013：Day 18 千问对比是可选评测亮点

- 状态：待确认
- 决策候选：在评测阶段增加千问与 DeepSeek 的质量、延迟和成本对比。
- 原因：通义千问在中文、长文本和阿里云模型生态方面有价值，但现在接入会扩大 Day 3 范围。
- 禁止：未到 Day 18 且未获确认前实现该对比。

## D-014：阶段检查点必须写入交接文档

- 状态：已确认
- 决策：每个阶段更新 `STATUS.md`、`HANDOFF.md`、必要时更新 `DECISIONS.md`，并指定唯一下一步。
- 原因：跨会话时不能依赖聊天记忆推断精确项目状态。

## D-015：Day 4 保留 PDF 页边界

- 状态：已确认
- 决策：解析层返回一基页码的 `PageText` 列表；PDF 空白页也必须保留，存库时以 `\f` 拼接。
- 原因：Day 5 需要在页内切分并写入 chunk page，Day 8 需要可靠生成来源页码。
- 文本文件：Markdown/TXT 使用 UTF-8（支持 BOM）并视为第 1 页。
- 失败：只有全部页面均为空白时返回 `400`；扫描 PDF 的 OCR 不属于 Day 4。

## D-016：Day 4 使用同步 SQLAlchemy 2.x 与 psycopg 3

- 状态：已确认
- 决策：上传路由为普通 `def`，使用同步 Session 和 `postgresql+psycopg` 驱动。
- 原因：FastAPI 在线程池执行同步路由，可容纳同步文件 I/O、pypdf 与数据库操作，并为后续表扩展保留 ORM 模型。
- 数据库初始化：仅通过 `python -m backend.app.models.init_db` 显式执行，不得放入应用启动或 `/health`。

## D-017：文档主键、状态和文本字段

- 状态：已确认
- 决策：`documents` 使用 PostgreSQL UUID 主键，成功状态为 `ready`，增加 `extracted_text TEXT`。
- 不增加：`storage_path`、`content_type`、`error_message`。
- 路径：统一由存储服务根据 UUID 与标准化扩展名推导。
- 失败记录：Day 4 不保存；解析或持久化失败时回滚并清理文件。

## D-018：Day 4 上传资源与错误契约

- 状态：已确认
- 限制：实际上传字节最多 20 MiB、PDF 最多 500 页、读取块为 1 MiB。
- HTTP：成功 `201`；无效内容 `400`；超限 `413`；不支持类型 `415`；PostgreSQL 不可用 `503`；未预期存储错误 `500`。
- 一致性：先写 UUID `.part`、解析、数据库 `flush`，再 `os.replace`，最后提交；异常时回滚并删除临时/最终文件。
- 已知残余风险：进程恰好在移动后崩溃可能留下孤儿文件，后续可增加启动清理任务，但不在 Day 4 扩展。
