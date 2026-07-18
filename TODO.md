# 后续任务

更新时间：2026-07-19（Asia/Shanghai）

## P0：Day 9 实现、验收与发布（已完成）

1. Day 9 实现提交 `4cccbe26688de33ff25756fc10584060c82fd03f` 已直接推送至
   `master`，远端核对相同，无 PR。
2. 实现提交共 16 个文件：13 个既有跟踪文件修改、3 个新增文件；第 13 个既有跟踪差异
   是审查修复涉及的 `backend/app/core/logging.py`。
3. 最终标准套件收集 222 项：`215 passed/7 skipped/0 warnings`，pytest 用时 `49.04s`；
   `pip check`、`compileall -q backend`、`git diff --check` 通过。
4. 历史真实 Qdrant 回归 `3 passed/1 warning`、真实 BGE + Qdrant chunk size 实验
   `3 passed/1 warning` 均保留为验收证据。

## P1：Day 9 状态刷新（已完成）

相关状态文档已改为 Day 9 实现提交已推送的真实状态，并补充审查后的 JSONL 输出设计；
状态刷新提交 `f3ca9ec1541d5e774f1eae92217d32160f15153f` 已推送。

## P2：计划状态更新（已完成）

用户于 2026-07-19 明确授权；`PLAN.md` 的 Day 9 五项复选框和开发日志已标记完成，
Day 10 及以后复选框未修改。

## P3：Day 10 及以后

当前工作区已有未提交的 Day 10 BM25 候选变更，来源、完成度与验收状态待确认。本轮
不得读取、修改、暂存或提交这些文件；先等待用户指定审查、继续实现或 Git 操作中的
唯一动作。Hybrid、RRF、Rerank、score threshold、多 doc_id 过滤、LangGraph、多轮记忆
或 trace 仍不得提前开始。

## 延后且待确认

- 使用更接近自然企业文档分布的语料复验 300/500/800；当前固定审计标识会被 BGE
  tokenizer 高度压缩，不能代表自然长文本的 BGE token 风险；
- 用更大正负样本集重新校准 `RAG_MIN_RELEVANCE_SCORE`；
- `%TEMP%\pytest-of-袁伟鑫` ACL 损坏目录的手工修复（需管理员），及 `.pytest_cache`
  WinError 5 根因；
- 真实 DeepSeek 四题全覆盖是否补充（需新授权）；
- 新环境 Qdrant/BGE 与完全离线复现；
- PostgreSQL/Qdrant outbox、删除同步和一致性修复；
- 孤儿上传文件启动清理与 SQLAlchemy 私有 `_state` 兼容性；
- `.gitattributes` 行尾规范和首次表结构迁移时是否引入 Alembic。
