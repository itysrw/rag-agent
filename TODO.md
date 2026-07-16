# 后续任务

更新时间：2026-07-16（America/New_York）

## P0：Day 8 工作区核验

1. 核对 `master`、基线 HEAD `683f516777345a1a000c6f94ade5fb4232a3a58e`、暂存区和
   Day 8 工作区差异。
2. 阅读 `docs/day8-rag-smoke.md`、RAG/Chat/LLM 实现与新增测试。
3. 确认当前标准测试 `181 passed/5 skipped/1 warning`、真实 Qdrant+BGE `2 passed`、
   真实上传→索引→RAG `1 passed`。
4. 确认 `PLAN.md`、`docker-compose.yml` 无差异，并排除 `.env`、`.agents/`、
   `.pytest-tmp/`、`data/models/`。

## P1：可选真实 DeepSeek 验收

已在一次明确授权下完成付费冒烟：报销 JSON、VPN SSE、Python 门控拒答通过。一次性脚本未提交，
当前没有 `RUN_DEEPSEEK_RAG_INTEGRATION` 开关或对应 pytest。年假真实生成和月球真实拒答未单独
执行；是否补充四题全覆盖待确认。任何补充调用都需要新的明确授权，不得打印 API Key、完整
Prompt 或知识库全文，不得把真实调用加入标准 pytest。

## P2：计划状态更新

`PLAN.md` Day 8 尚未更新。只有用户明确授权后才能勾选并写入真实完成事实，不得修改 Day 9。

## P3：Day 8 检查点 Git 操作

暂存、commit、实时远端核验和 push 是独立动作，必须分别获得明确授权。暂存时必须排除
`.env`、`.agents/`、`.pytest-tmp/`、`data/models/`，并在提交前重新运行 pytest、pip check、compileall 和
`git diff --check`。

## P4：Day 9 及以后

尚未授权。不得提前开放 top_k、doc_id filter、score threshold，不得开始 BM25、Hybrid、
Rerank、LangGraph、多轮记忆或 trace。

## 延后且待确认

- 用更大正负样本集重新校准 `RAG_MIN_RELEVANCE_SCORE`；
- `.pytest_cache` WinError 5 权限警告根因；
- 新环境 Qdrant/BGE 与完全离线复现；
- PostgreSQL/Qdrant outbox、删除同步和一致性修复；
- 孤儿上传文件启动清理与 SQLAlchemy 私有 `_state` 兼容性；
- `.gitattributes` 行尾规范和首次表结构迁移时是否引入 Alembic。
