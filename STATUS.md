# 项目状态

更新时间：2026-07-19（Asia/Shanghai）

## 当前检查点

- Day 1-9：均已实现、验收并提交推送至 `master`。
- Day 9 实现提交为 `4cccbe26688de33ff25756fc10584060c82fd03f`，已直接推送；远端
  `master` 已实时核对为同一提交，无 PR。
- Day 9 实现提交共 16 个文件：13 个既有跟踪文件修改、3 个新增文件；审查修复使
  `backend/app/core/logging.py` 成为第 13 个既有跟踪差异。相关状态文档随本次状态提交
  刷新；提交 `f3ca9ec1541d5e774f1eae92217d32160f15153f` 已推送。
- `PLAN.md`：用户于 2026-07-19 明确授权，Day 9 五项复选框和开发日志已标记完成；
  Day 10 及以后复选框未修改。
- 当前工作区另有 9 个未提交的 Day 10 BM25 候选文件：已跟踪修改为
  `backend/app/main.py`、`backend/requirements.txt`；新增文件为 `backend/app/api/bm25.py`、
  `backend/app/services/bm25.py`、`backend/tests/day10_bm25_cases.py`、
  `backend/tests/test_bm25.py`、`backend/tests/test_bm25_api.py`、
  `backend/tests/test_bm25_comparison_integration.py`、`backend/tests/test_bm25_postgres.py`。
  本轮未读取、未验收、未暂存，来源和完成度待确认。

## Day 9 已完成内容

- `POST /retrieval/search` 新增 `top_k`：Pydantic `Field(strict=True, ge=1, le=20)`，
  默认 5；`0/21/true/"5"/5.0/null` 均返回 422；非法 UUID `doc_id` 返回 422。
- `RetrievalService.search(query, *, top_k=5, doc_id=None)`：旧调用（Day 8 RAG）行为
  完全不变；非法 top_k 在 Embedding 调用前以 `ValueError` 拒绝。
- `QdrantVectorStore.search(vector, *, limit, doc_id=None)`：`doc_id` 非空时把顶层
  `doc_id` 字段的 `MatchValue(str(doc_id))` 过滤器传给 `query_points(query_filter=...)`，
  在 Qdrant 内先过滤再取 limit；`None` 时不传该参数。解析后防御性校验所有结果属于
  请求文档，越界抛 `QdrantResultError`（HTTP 502）。
- 合法但无匹配的 `doc_id` 返回 200 空数组，不引入 404。
- 每次成功检索（含空结果）输出一条 `retrieval_search_completed` 单行 JSON 日志；
  `backend/app/core/logging.py` 用 `JSONL_LOG_MARKER` 标记这类事件，普通 human handler
  排除该标记，独立 `{message}` handler 只接收标记事件，保证完整单行 JSON 且不重复。
  字段为 query_sha256/query_len/
  top_k/filter_doc_id/result_count/results（rank/chunk_id/doc_id/filename/page/score）；
  不含 query 原文、正文、metadata、向量或凭据。
- Day 7 遗留的"拒绝 Day 9 参数"测试已更新为接受合法 top_k/doc_id。
- `backend/tests/day9_tuning_corpus.py` 固定保存自撰、可公开提交的 8 页语料和 8 个带
  `expected_phrase` 的问题；导入不读取文件、环境或网络，也不使用随机数。标准测试在
  BGE/Qdrant 前验证每页大于 800 o200k token、问题字段非空、expected phrase 唯一且
  三配置 Chunk 数互不相同。
- 命中判据唯一固定为 NFKC + strip 后的 expected_phrase 子串包含；Hit@1、Hit@5、
  MRR@5 对全部问题平均。平均 Chunk token 与 Top-5 上下文 token 总量统一使用
  `o200k_base`、`disallowed_special=()`。
- 300/500/800 真实检索质量对比完成（真实本地 BGE + 三个一次性 Qdrant collection、
  固定 Top 5）：Chunk 数 40/24/16；三配置 Hit@1、Hit@5、MRR@5 均为 1.0；平均 Chunk
  token 为 199.3/332.9/499.9；Top-5 上下文 token 总量为 7986/13590/18576。
- 受控语料使用固定长审计标识拉开 o200k 长度，该标识会被 BGE tokenizer 高度压缩；
  三配置最大 BGE token 为 62/114/213。此结果不能外推为自然 800-token Chunk 一定可用。
- `README.md` 新增"检索优化实验"摘要；新增 `docs/day9-retrieval-tuning.md` 完整记录。
- `/chat`、RAG 门槛 `0.46`、上传、索引命令、Qdrant collection 契约均未修改。

## Day 9 验收证据

- 开发前门禁：HEAD `33689d3`、本地 `origin/master` 一致、工作区仅 `.agents/` 未跟踪。
- 检索/适配层与实验前置校验：`68 passed, 1 skipped, 1 warning in 12.14s`。
- Day 8 定向回归：`27 passed`（test_rag.py + test_chat.py）。
- 真实 Qdrant 完整模块（幂等、双文档 filter、Day 7 中文相关性）：
  `3 passed, 1 warning in 12.40s`；其中 filter 用例通过，临时 collection 已清理。
- 真实 BGE + Qdrant chunk size 实验：`3 passed, 1 warning in 13.90s`，三个 `day9_tuning_*`
  collection 均在 finally 中删除。
- 审查修复后的最终标准套件：收集 222 项，`215 passed, 7 skipped, 0 warnings`，pytest
  用时 `49.04s`；7 个跳过均为真实集成开关。
- `pip check`、`compileall -q backend`、`git diff --check`：通过。
- 发布证据：实现提交 `4cccbe26688de33ff25756fc10584060c82fd03f` 已直接推送至
  `master`，远端核对相同。
- 当前失败测试：无。

## 历史环境问题

- `%TEMP%\pytest-of-袁伟鑫` 目录 ACL 损坏（列目录即 WinError 5），导致所有使用
  `tmp_path` 的测试 ERROR。本轮通过 `PYTEST_DEBUG_TEMPROOT` 重定向到会话 scratchpad
  后全部通过。损坏目录未删除（需要管理员权限），根因与既有 `.pytest_cache`
  WinError 5 同族，待用户决定是否手工修复。审查修复后的最新标准套件为 0 warning；
  这不等于上述 ACL 根因已经修复。

## 已知警告与残余风险

- `top_k` 上限 20 是为 Day 12 Rerank 预留的召回规模，当前未实现 Rerank。
- chunk size 实验语料为受控构造文本（8 页、8 个单页事实问题），固定长审计标识使
  o200k 与 BGE token 比例不同于自然中文；三配置满分不能外推为普遍等价或最优。
- Top-5 上下文 token 总量随 chunk size 增大，但更大、更难且接近真实文档分布的评测集
  尚未建立，生产默认仍保持 `500/100`。
- `query_sha256` 只降低日志直接泄露，不等于匿名化。
- PostgreSQL/Qdrant 仍无跨存储事务、outbox、删除同步或一致性修复任务。
- LF→CRLF 提示与 pytest 临时目录/缓存权限根因仍待确认。

## 唯一下一步

Day 9 实现、发布和 `PLAN.md` 状态更新均已完成。下一步先只读审计现有 Day 10 BM25
候选变更的来源、范围与测试状态；用户指定唯一动作前不得继续修改或提交这些文件。
