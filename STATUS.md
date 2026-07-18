# 项目状态

更新时间：2026-07-16（America/New_York）

## 当前检查点

- Day 1-8：已实现、验收并提交；当前提交基线为 `33689d3`（本地 `origin/master` 一致）。
- Day 9：检索优化已在本地工作区实现并验收，尚未暂存、提交或推送。
- Day 9 工作区：12 个已修改跟踪文件（6 个文档：`README.md`、`DECISIONS.md`、
  `STATUS.md`、`TODO.md`、`HANDOFF.md`、`docs/architecture.md`；6 个代码/测试：
  `backend/app/api/retrieval.py`、`backend/app/services/retrieval.py`、
  `backend/app/services/qdrant_store.py`、`backend/tests/test_retrieval.py`、
  `backend/tests/test_qdrant_store.py`、`backend/tests/test_qdrant_integration.py`），
  3 个新增未跟踪文件（确定性实验语料、实验测试、实验文档）；另有须排除的无关
  `.agents/`，未读取或修改；`.pytest-tmp/` 当前不存在。
- `PLAN.md`：本轮未修改 Day 9 复选框或日志，等待授权。
- Day 10 及以后：尚未开始，未经用户明确授权不得开始。

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
- 每次成功检索（含空结果）输出一条 `retrieval_search_completed` 单行 JSON 日志，
  进入 message（当前 formatter 不显示 bind extra）；字段为 query_sha256/query_len/
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
- 最终标准套件：`214 passed, 7 skipped, 1 warning in 14.12s`（7 个跳过均为真实集成
  开关；warning 仍为 `.pytest_cache` WinError 5）。
- `pip check`、`compileall -q backend`、`git diff --check`：通过；变更文件密钥模式
  扫描 0 匹配。
- 当前失败测试：无。

## 本轮发现的环境问题

- `%TEMP%\pytest-of-袁伟鑫` 目录 ACL 损坏（列目录即 WinError 5），导致所有使用
  `tmp_path` 的测试 ERROR。本轮通过 `PYTEST_DEBUG_TEMPROOT` 重定向到会话 scratchpad
  后全部通过。损坏目录未删除（需要管理员权限），根因与既有 `.pytest_cache`
  WinError 5 同族，待用户决定是否手工修复。

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

等待用户指定 Day 9 审查或检查点操作。不得修改 `PLAN.md`、暂存、commit、push 或
开始 Day 10，除非分别获得明确授权。
