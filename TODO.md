# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：Day 5 检查点已完成

Day 5 功能、验收、`PLAN.md` 状态更新和本地实现提交均已完成：

- 实现提交：`a989837bbf8bae1cf866beda034130a514152378`
- 提交摘要：`a989837 feat: complete Day 5 text chunking`
- 标准测试：`60 passed, 1 skipped, 1 warning`
- 真实 PostgreSQL：`61 passed, 1 warning`
- `PLAN.md`：Day 5 五项任务和开发日志已更新；Day 6 未修改
- `.env`、`.agents/`：未读取、未修改、未提交
- 推送：未执行

本交接刷新提交是 Day 5 实现提交的直接后继。新会话先只读核对最新 HEAD、工作区和远端状态，
不得重新实现 Day 1-5。

## P1：仅在用户明确授权后处理远端

- 当前远端名称为 `origin`，但 `master` 没有上游跟踪分支；
- 本地没有远端跟踪引用，远端实时状态待确认；
- fetch、上游配置和 push 的具体动作必须按用户授权执行；
- 不得将 `.env` 或 `.agents/` 纳入任何提交或推送。

## P2：仅在用户明确授权后开始 Day 6

`PLAN.md` 下一阶段是 Embedding，但供应商仍为待确认：OpenAI、阿里云百炼/通义千问，
或本地 `BAAI/bge-small-zh-v1.5`。在供应商、模型、维度、费用和运行环境确认前禁止实现。

## 延后且待确认

- 远端实时状态、是否配置 `master` 上游及推送；
- 新环境的 `o200k_base` 词表预热/离线缓存策略；
- 孤儿上传文件启动清理；
- 首次修改既有表结构时引入 Alembic；
- pytest `.pytest_cache` 权限警告；
- Docker 状态查询权限/超时；
- `.gitattributes` 行尾规范；
- Day 6 Embedding 供应商、模型和维度；
- Day 18 千问质量/成本对比。
