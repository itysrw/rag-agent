# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：当前唯一任务——决定是否推送 Day 3 检查点

Day 3 代码、12 项测试、真实 DeepSeek 非流式/SSE 验收和本地提交检查点均已完成，`PLAN.md` 已在用户明确授权后同步。

下一步严格按以下顺序执行：

1. 向用户报告 Day 3 本地提交哈希和最终验证结果。
2. 用户决定是否推送并为 `master` 设置上游。
3. 未获推送授权时保持本地提交不变。
4. 用户明确要求开始 Day 4 后，才按 `PLAN.md` 进入下一阶段。

当前禁止：未经授权推送或开始 Day 4。

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

## P1：仅在 Day 3 建立检查点后开始 Day 4

Day 4 范围以 `PLAN.md` 为准：

- 安装 `pypdf2` 或 `pdfminer.six`、`python-multipart`；
- 支持 PDF、Markdown、TXT 上传与文本提取；
- Docker 启动 PostgreSQL；
- 创建 `documents` 表；
- 保存文档元数据和上传文件。

开始条件：已满足 Day 3 可恢复提交检查点；仍需用户明确要求开始 Day 4。

## 延后且待确认

- Day 6 Embedding：OpenAI、通义千问或本地 BGE；
- Day 18：是否增加千问质量/成本对比；
- pytest `.pytest_cache` 权限警告的根因与是否修复；
- 是否为 `master` 配置上游并推送；
- 是否增加 `.gitattributes` 统一行尾。
