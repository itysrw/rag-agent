# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：报告 Day 4 检查点并等待用户指令

Day 4 上传、分页解析、安全存储、PostgreSQL 持久化、真实 PDF 验收和全量回归均已完成。
`PLAN.md` 已按用户授权同步，Day 4 已形成本地提交检查点，尚未推送。

当前允许的下一选择均需用户单独明确：

1. 推送当前本地检查点并配置上游；
2. 按 `PLAN.md` 开始 Day 5；
3. 继续暂停。

当前禁止：自行推送、修改检查点或开始 Day 5。

## Day 4 最终验收记录

- 上传协议：multipart，必填 `file`
- 类型：PDF、Markdown、TXT
- 限制：20 MiB、500 PDF 页、1 MiB 读取块
- 分页：PDF 空白页保留，`\f` 序列化；文本文件为第 1 页
- 存储：UUID `.part` → 解析 → `flush` → `os.replace` → `commit`
- 失败补偿：rollback 并清理临时/最终文件
- 数据库：PostgreSQL 16、SQLAlchemy 2.x、psycopg 3、UUID 主键
- 建表：显式 `python -m backend.app.models.init_db`
- 真实 PDF/PostgreSQL 往返：通过
- 全量 pytest：`44 passed, 1 warning`
- `pip check`、compileall、Compose、差异和密钥检查：通过
- `GET /health` 与 Day 3 `/chat`：回归通过

## P1：仅在用户明确要求后开始 Day 5

Day 5 必须严格按 `PLAN.md` 实现文本切分和 chunks 表，不得提前进入 Embedding 或 Qdrant。

## 延后且待确认

- 孤儿文件启动清理任务；
- 首次表结构变更时引入 Alembic；
- pytest `.pytest_cache` 权限警告；
- `.gitattributes` 行尾规范；
- Day 6 Embedding 供应商；
- Day 18 千问质量/成本对比；
- 是否配置 `master` 上游并推送。
