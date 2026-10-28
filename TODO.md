# 后续任务

更新时间：2026-10-28（Asia/Shanghai）

## 当前唯一下一步：新会话只读恢复

功能开发已暂停。按 `HANDOFF.md` 的 A/B/C 核对 Day 11 完成检查点：本地 Git、15 个
相关未提交文件、空暂存区、PLAN 已完成、最新标准 335/10 与历史真实集成 343 的区别。
先复述状态，列矛盾/待确认项及最多 5 个步骤，再等待用户指定唯一动作。
本轮交接不重跑代码测试、不探测/重启服务、不查询远端、不改代码或 PLAN、不执行 Git 写操作。

## P0：Day 11 每日任务（已完成，Git 发布待用户指定）

1. 独立 Hybrid API、标准等权 RRF k=60、两路候选 20、chunk_id 一致性和安全日志已完成。
2. 真实三路对比已完成：Hybrid Hit@1/Hit@5/MRR@5 为 0.917/1.000/0.944，补回向量
   Top 5 漏检 1 题；负样本仍全部返回，局限与逐题排名已记录。
3. 2026-10-28 标准测试 `335 passed/10 skipped`；2026-10-27 真实集成记录 `343 passed`，
   本轮未重跑真实集成；既有静态检查通过。
4. 6 份既有交接文档合并更新，新代码/测试/实验文档仍未暂存、提交或推送。
5. 2026-10-28 用户确认审查、测试与修复通过；已授权勾选 `PLAN.md` Day 11 四项任务，
   并将开发日志标记为已完成。Git 发布与 Day 12 仍待用户指定，不自动开始。
6. Docker 4.97.0 已安装；本机通过 `D:\Docker\Start-DockerDesktop.ps1` 在 D 盘创建运行时
   目录恢复启动，已验证重启与原有容器。默认 C 盘 socket 故障的长期修复另行处理。

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
- `PLAN.md` Day 10 四项复选框与开发日志已更新；Day 11 于 2026-10-28 单独授权标记完成。
- `.env`、`.agents/`、测试临时目录、项目内 tiktoken 缓存和 `data/models/` 均未纳入提交。

## P1b：Day 10 发布状态（已完成）

- Day 11 开工门禁中已推送 `a614a36`、`98ff9d3`，并独立查询实时远端确认。
- 本地 HEAD 与 `origin/master` 均为 `98ff9d3860e845f47df91e366811663c71a0ec5d`。
- 该发布只包含 Day 10 已有提交，不包含 Day 11 工作区或原有未提交交接文档。
- 收尾 `git ls-remote` 再次遇到 GitHub 443 连接失败；网络恢复后只读复查实时 HEAD，
  不把 tracking ref 当作实时远端结论。

## P2：Day 12 及以后（未开始）

Day 11 独立 Hybrid/RRF 已完成；不得自动开始 Rerank、Hybrid 接入 /chat、统一 mode、
score 融合、LangGraph、多轮记忆或 trace。Day 12 需用户明确指定。

## 延后且待确认

- 用更大、更难且接近自然企业文档分布的评测集复验 BM25 tokenizer 与向量/BM25 排名；
- 当前每请求全量扫描 PostgreSQL 指纹的扩展性方案，以及多 worker 索引一致性；
- PostgreSQL/Qdrant outbox、删除同步和一致性修复；
- 中文停用词、领域词典或替代 tokenizer 是否值得在后续评测后引入；
- 用更大正负样本集重新校准 `RAG_MIN_RELEVANCE_SCORE`；
- `%TEMP%` pytest ACL、`.pytest_cache` 和 LF→CRLF 根因；
- 真实 DeepSeek 四题全覆盖是否补充（需新付费授权）；
- 首次表结构变化时是否引入 Alembic。
