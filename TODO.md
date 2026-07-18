# 后续任务

更新时间：2026-07-16（America/New_York）

## P0：Day 9 工作区核验

1. 核对 `master`、基线 HEAD `33689d3`、暂存区为空和 Day 9 工作区差异（12 个修改 +
   3 个新增，另有须排除的 `.agents/`）。
2. 阅读 `docs/day9-retrieval-tuning.md`、检索/适配层实现与新增测试。
3. 确认标准测试 `214 passed/7 skipped/1 warning`、真实 Qdrant 回归 `3 passed`、真实
   chunk size 实验 `3 passed`。
4. 确认 `PLAN.md`、`/chat`、RAG 层无差异，并排除 `.env`、`.agents/`、`.pytest-tmp/`、
   `data/models/`。

## P1：计划状态更新

`PLAN.md` Day 9 尚未更新。只有用户明确授权后才能勾选并写入真实完成事实，不得修改
Day 10。

## P2：Day 9 检查点 Git 操作

暂存、commit、实时远端核验和 push 是独立动作，必须分别获得明确授权。暂存时必须排除
`.env`、`.agents/`、`.pytest-tmp/`、`data/models/`，并在提交前重新运行 pytest、
pip check、compileall 和 `git diff --check`。

## P3：Day 10 及以后

尚未授权。不得开始 BM25、Hybrid、RRF、Rerank、score threshold、多 doc_id 过滤、
LangGraph、多轮记忆或 trace。

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
