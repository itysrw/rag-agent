# 项目状态

更新时间：2026-07-15（America/New_York）

## 当前检查点

Day 1 至 Day 5 已实现、验收、提交并推送。Day 6 本地 BGE Embedding 已在工作区实现，
完成两轮审查并修复两个 P2；当前标准测试通过，没有代码阻断项。

Day 6 尚未提交或推送；PLAN.md 已获得用户明确授权并完成 Day 6 状态更新，因此必须区分：

- 功能实现状态：Day 6 已实现并通过范围受限二次审查；
- Git 状态：Day 6 全部改动仍在工作区；
- 项目计划状态：PLAN.md 的 Day 6 五项已勾选，开发日志已标记“已完成”；
- 当前动作：暂停功能开发，只维护交接包并等待用户指定下一动作。

## Git 精确状态

- 仓库：D:\2019\rag-agent
- 分支：master
- 当前 HEAD：ecadc3296b038bad169b2bb78238f8ffd77e43d8
- HEAD 摘要：ecadc32 docs: refresh Day 5 handoff
- Day 5 实现提交：a989837bbf8bae1cf866beda034130a514152378
- 上游：origin/master
- 本地跟踪引用 origin/master：ecadc3296b038bad169b2bb78238f8ffd77e43d8
- 基于本地跟踪引用的 ahead/behind：0/0
- 暂存区：空
- Day 6 提交：无
- Day 6 推送：无
- 本次远端实时查询：连接 GitHub 失败后，授权查询继续超时；远端此刻的实际 HEAD 待确认
- 上一次已成功确认的远端状态：Day 5 交接时 origin/master 与本地 HEAD 相同

### 当前相关工作区差异

已修改的跟踪文件：

- .env.example
- DECISIONS.md
- HANDOFF.md
- PLAN.md
- README.md
- STATUS.md
- TODO.md
- backend/app/core/config.py
- backend/requirements.txt
- docs/architecture.md

Day 6 新增且未跟踪的文件：

- backend/app/commands/__init__.py
- backend/app/commands/embed_document.py
- backend/app/services/embedding.py
- backend/tests/test_embedding.py
- backend/tests/test_embedding_integration.py

另有一个无关的未跟踪 .agents/ 文件。它未被读取、修改、暂存或纳入交接范围，后续也必须排除。
.env 未被读取、输出、修改或提交。data/models/ 为 Git 忽略的本地模型缓存。

## 已完成内容

### Day 1 至 Day 5

- Day 1：项目边界、目录、README、目标架构和 Git 远端。
- Day 2：FastAPI 骨架、GET /health、路由、配置和请求日志。
- Day 3：OpenAI-compatible LLMClient、DeepSeek 普通 JSON 与 SSE 对话。
- Day 4：PDF/Markdown/TXT 上传、解析、文件补偿与 PostgreSQL 文档持久化。
- Day 5：按页 o200k_base token 切分，默认 500/100；有序 Chunk、JSONB、级联删除和同事务持久化。

### Day 6 工作区实现

- 固定本地模型 BAAI/bge-small-zh-v1.5。
- 固定 revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4。
- CPU、512 维、归一化、每批最多 32 条。
- 不依赖 OpenAI，不使用 DeepSeek Key 做 Embedding。
- 使用 BGE 自身 tokenizer，在推理前包含特殊 token 计数并拒绝超长输入，禁止静默截断。
- 缓存优先；只对连接、超时、HTTP 429 和 5xx 做最多 3 次重试，退避 1/2/4 秒。
- 模型只从固定 snapshot 本地加载，local_files_only=True、trust_remote_code=False，并在进程内复用。
- embed_chunks() 按输入位置把向量绑定回 Chunk UUID，校验数量、512 维、有限数值和单位范数。
- 只读命令按 chunk_index 查询 PostgreSQL，向量仅存内存，只输出安全摘要。
- 未修改上传接口，未写 PostgreSQL 向量，未接入 Qdrant、pgvector 或 Day 7 能力。

### 已修复的两个 P2

1. backend/app/commands/embed_document.py
   - client_factory() 抛出的 Embedding ValidationError 不再落入数据库不可用分支；
   - embed_document() 将它转换为 EmbeddingConfigurationError；
   - 数据库配置错误和 SQLAlchemyError 仍保持数据库错误分类。
2. backend/app/services/embedding.py
   - cache_dir.mkdir() 的 OSError 已纳入异常边界；
   - 转换为不含本机路径的 ModelDownloadError；
   - 目录创建失败发生在 downloader 调用前，不尝试联网。

## 当前验证证据

本次交接刷新实际执行：

    .\.venv\Scripts\python.exe -m pytest backend/tests -v

结果：

- Python 3.11.15
- collected 112
- 110 passed
- 2 skipped
- 1 warning
- 用时 26.93 秒

两个跳过项：

- backend/tests/test_documents_postgres.py 的真实 PostgreSQL 集成测试；
- backend/tests/test_embedding_integration.py 的真实 BGE CPU 集成测试。

修复报告提供的额外证据：

- 两个目标回归测试：2 passed；
- backend/tests/test_embedding.py：50 passed，1 warning；
- 真实 PostgreSQL 集成：1 passed，1 warning；
- pip check：通过；
- compileall：通过；
- git diff --check：通过，仅有既存 LF→CRLF 提示。

真实 BGE 的证据边界：

- P2 修复前曾完成首次下载、CPU 推理及 HF_HUB_OFFLINE=1 缓存重跑；
- P2 修复后的审查轮没有启用 RUN_LOCAL_EMBEDDING_INTEGRATION；
- 因此“修复后真实 BGE CPU 集成测试”当前标记为待确认，不能写成刚刚通过。

## 当前错误与残余风险

- 当前失败测试：无。
- pytest 持续出现 .pytest_cache 的 PytestCacheWarning：
  [WinError 5] 拒绝访问；不影响测试通过，根因待确认。
- 本次 git ls-remote origin refs/heads/master 无法连接 GitHub，授权后查询仍超时；
  远端实时 HEAD 待确认。
- 真实 PostgreSQL 测试在修复报告中通过，但标准套件默认跳过。
- 当前真实数据库历史扫描曾得到 chunk_count=0，尚无可直接用于真实 CLI 验收的既存 Chunk；
  是否创建新的验收文档待确认，且不得未经授权修改真实数据库。
- P2 修复后真实 BGE CPU 集成测试未重跑，待确认。
- 模型首次下载依赖 Hugging Face 网络；缓存损坏、磁盘空间、代理和离线部署策略仍需后续运维验证。
- o200k_base 是 Day 5 切分基准，不等于 BGE tokenizer；当前通过独立预检避免静默截断。
- 文件移动后进程立即崩溃仍可能留下孤儿上传文件；启动清理任务未实现。
- _cleanup_failed_upload() 读取 SQLAlchemy 私有事务 _state，升级兼容性待确认。
- Git 持续提示 LF→CRLF；是否增加 .gitattributes 待确认。
- PLAN.md 已按用户授权更新 Day 6；后续修改仍需新的明确授权。

## 唯一下一步

保持暂停。新会话先只读核对本交接包、Git 差异、PLAN.md 已更新状态和测试证据，
然后等待用户明确选择：是否重跑修复后真实 BGE 验收、是否授权提交 Day 6。
提交与推送必须分别获得授权，Day 7 不得提前开始。
