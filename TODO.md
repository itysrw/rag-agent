# 后续任务

更新时间：2026-07-16（America/New_York）

## P0：Day 7 检查点恢复

新会话第一轮只读：

1. 完整阅读 `HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`AGENTS.md`、
   `README.md`、`PLAN.md`、`docs/architecture.md` 和 `docs/day7-retrieval-smoke.md`。
2. 用 `git rev-parse HEAD`、`git status` 和远端实时查询核对 Day 7 最终提交及本地/远端一致性。
3. 确认 `PLAN.md` Day 7 五项和开发日志已更新，Day 8 及以后未修改。
4. 确认标准测试 `153 passed/4 skipped/1 warning`、真实 BGE/Qdrant `3 passed`。
5. 明确排除 `.env`、无关 `.agents/` 和 `data/models/`。

完成后先复述状态，等待用户指定下一动作。

## P1：Day 8

Day 8 尚未授权。只有用户明确授权后，才可按当时的 `PLAN.md` 实现基础 RAG；
不得从 Day 7 交接包自行扩大范围。

## 延后且待确认

- `.pytest_cache` WinError 5 权限警告根因；
- 新环境的 Qdrant 和 BGE 离线复现；
- PostgreSQL/Qdrant 的 outbox、自动重试、删除同步和一致性修复；
- 孤儿上传文件启动清理；
- SQLAlchemy 私有事务 `_state` 的升级兼容性；
- `.gitattributes` 行尾规范；
- 首次修改既有表结构时是否引入 Alembic；
- 后续 BM25、Hybrid/RRF、Rerank、RAG、LangGraph、评测和 Streamlit。
