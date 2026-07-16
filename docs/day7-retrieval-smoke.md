# Day 7 Qdrant 检索验收记录

更新时间：2026-07-16（America/New_York）

## 实现边界

- PostgreSQL Document/Chunk 仅由显式 `index_document` 命令读取。
- 数据库 Session 在 BGE 推理和 Qdrant 写入前关闭。
- Qdrant collection 固定为 unnamed 512/Cosine；Point ID 等于 Chunk UUID。
- 在线接口只接受 query，固定 Top 5，不返回向量。
- 上传接口、`/chat`、可调 top_k、filter、BM25、Hybrid、Rerank 和 RAG 均未修改。

## 自动化验证

标准测试命令：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v

本轮结果：

- collected 157
- 153 passed
- 4 skipped
- 1 warning
- 16.42 秒

四个跳过项分别为真实 PostgreSQL、真实 BGE，以及两个显式开关控制的真实 Qdrant 测试。
现有 warning 仍是 `.pytest_cache` 的 WinError 5，不影响测试通过。

## 真实 Qdrant 与相关性验收

测试入口：

    $env:RUN_QDRANT_INTEGRATION='1'
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_qdrant_integration.py -v

受控三页 PDF 的 BGE 相关性测试还需同时设置：

    $env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'

受控问题与期望页码：

| 问题 | 期望页码 | 当前结果 |
|---|---:|---|
| 报销票据最晚什么时候交？ | 1 | Top 1，正确页为 1 |
| VPN 连不上应该联系谁，分机是多少？ | 2 | Top 1，正确页为 2 |
| 年假需要提前多久申请？ | 3 | Top 1，正确页为 3 |

真实测试结果：`2 passed, 1 warning in 19.59s`。验证内容包括：

- 固定 512/Cosine collection 创建与校验；
- 相同 Chunk UUID 重复 upsert 后仍只有两个 Point；
- retrieve 返回 payload 且不返回向量；
- `query_points()` 返回完整来源字段；
- 受控三页中文 PDF 经真实 BGE 和 Qdrant 后，三个期望页面均为 Top 1；
- 两个唯一临时 collection 均在 `finally` 中删除。

2026-07-16 推送前将真实 BGE 和两个真实 Qdrant 用例合并复验，结果为
`3 passed, 1 warning in 13.55s`。

Docker 环境也已确认：镜像为 `qdrant/qdrant:v1.18.1`，容器仅绑定
`127.0.0.1:6333`，命名卷为 `rag-agent-qdrant-data`，`/healthz` 返回通过。
生产名 `documents` collection 已按 512/Cosine 初始化；容器重启后再次校验仍存在，命名卷
持久化验证通过。
