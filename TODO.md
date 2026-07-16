# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：只读恢复与范围确认

新会话必须先完成以下检查，不得立即改代码：

1. 完整阅读 HANDOFF.md、STATUS.md、DECISIONS.md、README.md、PLAN.md 和 docs/architecture.md。
2. 阅读 Day 6 直接相关的配置、Embedding 服务、命令和测试文件。
3. 核对 master、HEAD ecadc3296b038bad169b2bb78238f8ffd77e43d8、暂存区和全部工作区差异。
4. 确认 PLAN.md 的 Day 6 五项和开发日志已更新，但 Day 6 代码仍未提交或推送。
5. 明确排除 .env、无关 .agents/ 和 data/models/。

完成后先复述状态并等待用户指定唯一下一动作。

## P1：可选的修复后真实 BGE 验收

仅在用户要求继续验证，并允许必要的本地模型读取或网络下载后执行：

    $env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_embedding_integration.py -v

验收点：

- 使用固定 revision；
- device=cpu；
- 两条中文文本各返回一个 512 维向量；
- 向量有限且单位范数；
- 不需要 OpenAI 或 DeepSeek Key；
- 不打印正文或完整向量。

P2 修复前该测试及 HF_HUB_OFFLINE=1 缓存重跑曾通过；P2 修复后尚未重跑，当前状态为待确认。

## P2：可选的真实文档命令验收

命令：

    .\.venv\Scripts\python.exe -m backend.app.commands.embed_document --document-id <UUID>

当前真实数据库曾扫描到 chunk_count=0，因此缺少可直接复用的 Document UUID。
是否上传或创建验收文档会修改真实文件和数据库，必须先获得明确授权；不得自行补造数据。

验收点：

- 按 chunk_index 读取；
- 无 Chunk 时在模型加载前失败；
- 输出仅包含 document_id、model、revision、device、chunk_count、
  embedding_dimension、normalized 和 status；
- 不写 PostgreSQL、Qdrant 或文件；
- 配置错误不得误报为数据库不可用。

## P3：完成 Day 6 项目检查点

PLAN.md 的 Day 6 五项复选框和开发日志已经按用户授权更新。以下剩余操作互相独立，
必须分别获得明确授权：

1. 暂存明确的 Day 6、PLAN.md 与交接文件，排除 .env、.agents/ 和 data/models/；
2. 创建本地提交；
3. 实时核对远端状态；
4. 推送 master。

在授权提交前，建议重新执行：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v
    .\.venv\Scripts\python.exe -m pip check
    .\.venv\Scripts\python.exe -m compileall backend
    git diff --check

## P4：Day 7，仅在 Day 6 检查点完成且用户明确授权后

PLAN.md 的下一阶段是 Qdrant。当前禁止提前实现：

- Qdrant 容器或 collection；
- Chunk 与 Embedding 持久化；
- POST /retrieval/search；
- 查询向量、top-k 或检索质量验证。

Day 7 的精确范围必须以当时的 PLAN.md 和用户指令为准。

## 延后且待确认

- pytest .pytest_cache 的 WinError 5 权限警告；
- GitHub 远端实时查询超时；
- 新环境的模型与 o200k_base 离线缓存策略；
- 孤儿上传文件启动清理；
- SQLAlchemy 私有事务 _state 的升级兼容性；
- .gitattributes 行尾规范；
- 首次修改既有表结构时是否引入 Alembic；
- Day 18 千问质量与成本对比。
