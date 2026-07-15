# 项目状态

更新时间：2026-07-15（America/New_York）

## 当前检查点

**Day 1 至 Day 3 均已完成；Day 3 代码、单元测试和真实 DeepSeek 非流式/SSE 验收已形成本地提交检查点，尚未推送。**

## Git 状态

- 分支：`master`
- HEAD：包含本文件的 Day 3 本地检查点；精确哈希使用 `git log -1 --oneline` 查询
- HEAD 摘要：`feat: complete Day 3 DeepSeek chat integration`
- 远端：`origin https://github.com/itysrw/rag-agent.git`
- 上游跟踪：未配置
- 工作区：Day 3 提交完成后应为干净状态
- 暂存区：Day 3 提交完成后应为空
- `.env`：存在，被 `.gitignore` 忽略且未被 Git 跟踪；验收过程未读取或输出 Key

## 已完成并提交

### Day 1

- 项目边界、目录、README、Mermaid 架构图、GitHub 远端。

### Day 2

- FastAPI 应用与三个固定路由；
- 应用配置、Loguru、请求日志；
- `/health` 测试及真实 HTTP 验收。

## 已完成验收并提交

### Day 3

- `LLMSettings` 与 `LLMClient`；
- 默认模型 `deepseek-v4-flash`；
- `LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}`；
- `/chat` 非流式 JSON 和 SSE 流式输出；
- 配置缺失 `503`、上游失败 `502`、流错误 SSE event、空白消息 `422`；
- 流正常结束、消费者中断和上游异常时关闭资源；
- Stub/Fake 测试与本地 `.env` 隔离；
- 真实 DeepSeek 非流式和 SSE 验收通过；
- 未实现 Day 4 或更晚功能。

## 真实验收结果

| 验收项 | 结果 |
|---|---|
| `GET /health` | `200`，响应体精确为 `{"status":"ok"}` |
| 非流式 `/chat` | `200`，`answer` 非空，`model=deepseek-v4-flash` |
| 流式 `/chat` | `200`，`Content-Type: text/event-stream; charset=utf-8` |
| SSE 增量 | 3 个 delta，最后事件为 `[DONE]`，无 error 事件 |
| 空白消息 | `422` |
| `POST /documents/upload` | `501`，仍为 Day 4 占位 |
| 日志安全 | 未发现 API Key、Authorization、Bearer 或请求正文 |
| 进程清理 | 临时验收端口已停止监听 |

受限沙箱内的真实上游请求因网络策略返回非流式 `502` 和 SSE error；在获准的沙箱外环境运行同一脱敏验收后全部通过，因此该次 `502` 不属于代码或 DeepSeek 配置故障。

## 当前测试状态

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

验收前后复测结果均为：`12 passed, 1 warning`。

失败测试：无。

警告：pytest 无法写入 `.pytest_cache`，`[WinError 5] 拒绝访问`。当前不影响测试通过，根因仍待确认。

依赖检查：`No broken requirements found.`

Python：`3.11.15`。

额外检查：Python 编译通过，`git diff --check` 通过；仅有 LF/CRLF 非阻断提示。

## 当前接口状态

| 接口 | 状态 |
|---|---|
| `GET /health` | 已完成并验收 |
| `POST /chat` 非流式 | 已完成模拟测试和真实 DeepSeek 验收 |
| `POST /chat` SSE | 已完成模拟测试和真实 DeepSeek 验收 |
| `POST /documents/upload` | Day 4 占位，当前返回 `501` |

## 计划状态

- 用户已明确授权按 `PLAN.md` 和规范文件修正 Day 3 状态；`PLAN.md` 的 Day 3 已勾选完成。
- Day 3 已创建本地提交，但尚未推送。
- 用户明确要求前不推送，也不开始 Day 4。

## 唯一下一步

等待用户决定是否推送 Day 3 本地检查点；推送和开始 Day 4 都需要单独明确授权。
