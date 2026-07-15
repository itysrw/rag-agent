# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：当前唯一任务——暂停并等待用户指令

Day 3 代码、12 项测试、真实 DeepSeek 非流式/SSE 验收和本地提交检查点均已完成，提交为 `177ad2b`。当前没有获准继续执行的开发任务。

恢复工作时严格按以下顺序执行：

1. 完整阅读 `HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`AGENTS.md`、`README.md` 和当前任务相关代码。
2. 只读运行 `git status --short --branch` 与 `git log -1 --oneline`。
3. 预期基线：`master`、HEAD `177ad2b`、无上游跟踪；仅 `HANDOFF.md`、`STATUS.md`、`TODO.md` 为未暂存的交接刷新。
4. 向用户复述状态、缺失或矛盾信息，并给出最多 5 个步骤。
5. 等待用户明确选择：提交交接刷新、推送 Day 3、开始 Day 4，或继续暂停。

当前禁止：未经授权修改代码、提交交接刷新、推送或开始 Day 4。

## Day 3 验收记录

- 真实非流式状态码：`200`
- 真实非流式 model：`deepseek-v4-flash`
- 真实非流式 answer 是否非空：是
- 真实 SSE 状态码：`200`
- SSE Content-Type：`text/event-stream; charset=utf-8`
- SSE 是否出现 delta：是，共 3 个
- SSE 是否以 `[DONE]` 结束：是
- SSE error 事件：无
- pytest：`12 passed, 1 warning`
- `pip check`：`No broken requirements found.`
- 密钥泄漏检查：未发现；`.env` 被忽略且未跟踪，`.env.example` 为占位符
- 日志检查：未发现 API Key、Authorization、Bearer 或请求正文
- Day 4 边界：`POST /documents/upload` 仍为 `501`
- `git diff --check`：通过，仅有 LF/CRLF 非阻断提示

## P1：仅在用户明确要求后开始 Day 4

Day 4 范围以 `PLAN.md` 为准：

- 安装 `pypdf2` 或 `pdfminer.six`、`python-multipart`；
- 支持 PDF、Markdown、TXT 上传与文本提取；
- Docker 启动 PostgreSQL；
- 创建 `documents` 表；
- 保存文档元数据和上传文件。

开始条件：Day 3 检查点已经满足；仍需用户明确要求开始 Day 4，并先处理或明确保留当前三份未提交的交接刷新。

## 延后且待确认

- Day 6 Embedding：OpenAI、通义千问或本地 BGE；
- Day 18：是否增加千问质量/成本对比；
- pytest `.pytest_cache` 权限警告的根因与是否修复；
- 是否为 `master` 配置上游并推送；
- 是否增加 `.gitattributes` 统一行尾。
