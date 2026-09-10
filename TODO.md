# 后续任务

更新时间：2026-09-10（Asia/Shanghai）

## P0：Day 10 本地实现与验收（已完成）

1. `rank-bm25==0.2.2`、确定性中英混合 tokenizer、PostgreSQL corpus loader、SHA-256
   指纹刷新、进程内 `BM25Okapi` 和独立 API 已实现。
2. `POST /retrieval/bm25/search` 复用严格 query/top_k/doc_id 契约；token-overlap 门控、
   Top-K 前 doc_id 过滤、有限 raw score 和安全 JSONL 已覆盖。
3. Day 10 真实模块合并验收 `4 passed`；覆盖真实 PostgreSQL 刷新/过滤及相同 24 个
   Chunk ID 的真实向量/BM25 对比。
4. 最终标准套件 `264 passed/9 skipped`；开启全部真实集成开关后 `273 passed`；
   `pip check`、`compileall`、`git diff --check` 通过。
5. `docs/day10-vector-vs-bm25.md` 已记录逐题排名、聚合指标、负样本返回率和局限。

## P1：Day 10 检查点（已完成）

- Day 10 实现提交为 `a614a365ff52b8fa087ce651614c23e2e1017c0b`。
- `PLAN.md` Day 10 四项复选框与开发日志已更新；Day 11 未触及。
- `.env`、`.agents/`、测试临时目录、项目内 tiktoken 缓存和 `data/models/` 均未纳入提交。

## P2：Day 11 及以后

尚未授权。不得开始 Hybrid、RRF、统一 mode、score 融合、Rerank、LangGraph、多轮记忆
或 trace。Day 10 的两路对比只提供后续研究动机，不代表已实现 Hybrid。

## 延后且待确认

- 用更大、更难且接近自然企业文档分布的评测集复验 BM25 tokenizer 与向量/BM25 排名；
- 当前每请求全量扫描 PostgreSQL 指纹的扩展性方案，以及多 worker 索引一致性；
- PostgreSQL/Qdrant outbox、删除同步和一致性修复；
- 中文停用词、领域词典或替代 tokenizer 是否值得在后续评测后引入；
- 用更大正负样本集重新校准 `RAG_MIN_RELEVANCE_SCORE`；
- `%TEMP%` pytest ACL、`.pytest_cache` 和 LF→CRLF 根因；
- 真实 DeepSeek 四题全覆盖是否补充（需新付费授权）；
- 首次表结构变化时是否引入 Alembic。
