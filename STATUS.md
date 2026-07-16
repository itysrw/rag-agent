# 项目状态

更新时间：2026-07-16（America/New_York）

## 当前检查点

- Day 1-7：已实现并验收；本文件随 Day 7 检查点提交。
- Day 7：显式 PostgreSQL Chunk→本地 BGE→Qdrant 索引与独立固定 Top 5 检索 API 已完成。
- `PLAN.md`：Day 7 五项已按明确授权勾选，开发日志已更新；Day 8 及以后未修改。
- Day 8 及以后：尚未开始，必须等待用户明确授权。

## Git 状态说明

- 仓库：`D:\2019\rag-agent`
- 分支：`master`
- Day 7 提交前基线：`eefd397db1e20947016c22ffa26d1fefc894949d`
- Day 7 最终提交：包含本文件的当前 HEAD；精确 SHA 必须用 `git rev-parse HEAD` 读取。
- 提交前 GitHub 实时 `master` 已确认等于 `eefd397`，不存在远端分叉。
- Day 7 检查点推送后应确认 `origin/master` 与本地 HEAD 相同且 ahead/behind 为 `0/0`。
- 无关 `.agents/` 未读取、未修改、未暂存，必须排除。
- `.env` 未读取或纳入 Git；`data/models/` 是 Git 忽略的本地模型缓存。

## Day 7 已完成内容

- 固定 `qdrant-client==1.18.0` 和 `qdrant/qdrant:v1.18.1`。
- 容器仅绑定 `127.0.0.1:6333`，命名卷 `rag-agent-qdrant-data` 持久化通过。
- `documents` collection 固定 unnamed 512/Cosine，并校验模型与 schema metadata。
- `QdrantVectorStore` 严格 initialize/validate/upsert/search。
- Point ID 等于 Chunk UUID，payload 保存来源字段，`upsert(wait=True)` 且每批最多 32。
- `backend.app.commands.init_qdrant` 显式初始化 collection。
- `backend.app.commands.index_document --document-id <UUID>` 在关闭 PostgreSQL Session 后执行 BGE/Qdrant。
- `EmbeddingClient.embed_query()` 只在查询侧添加固定 BGE instruction。
- `RetrievalService.search()` 与 `POST /retrieval/search` 固定 Top 5，不返回向量。
- 上传接口和 `/chat` 未接入 Qdrant；未提前实现 Day 8/9。

## 最终验收证据

- 标准套件：`153 passed, 4 skipped, 1 warning in 16.42s`。
- 真实 BGE + 真实 Qdrant 合并复验：`3 passed, 1 warning in 13.55s`。
- 三个受控中文问题分别命中预期页 1、2、3，均为 Top 1。
- `pip check`、`compileall -q backend`、`git diff --check`：通过。
- Qdrant `/healthz`：通过。
- 24 个 Day 7 审查文件的常见密钥模式匹配：0。
- 当前失败测试：无。

## 已知警告与残余风险

- `.pytest_cache` 出现 `PytestCacheWarning: [WinError 5] Access is denied`；不影响测试，根因待确认。
- 新机器的 Qdrant、模型缓存和完全离线复现待确认。
- PostgreSQL/Qdrant 无跨存储事务，尚无 outbox、删除同步或一致性修复任务。
- LF→CRLF 提示持续存在；是否增加 `.gitattributes` 待确认。

## 唯一下一步

只读确认 Day 7 检查点和本地/远端一致，然后等待用户明确授权 Day 8。
