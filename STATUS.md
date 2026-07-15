# 项目状态

更新时间：2026-07-15（America/New_York）

## 当前检查点

**Day 1 至 Day 5 的功能实现、验收和本地提交均已完成。Day 6 尚未开始，当前暂停开发。**

Day 5 在不改变 `POST /documents/upload` 成功响应契约的前提下，为每个新上传文档生成
按页、有序、带 token 元数据的 Chunks，并与 Document 在同一 PostgreSQL 事务中提交。

## Git 精确状态

- 分支：`master`
- Day 5 实现提交：`a989837bbf8bae1cf866beda034130a514152378`
- Day 5 提交摘要：`a989837 feat: complete Day 5 text chunking`
- Day 5 基线提交：`a64a0cc docs: refresh Day 4 handoff`
- 本交接刷新提交是 `a989837` 的直接后继；完整当前 HEAD 以 `git rev-parse HEAD` 为准
- 远端名称：`origin`
- 上游跟踪：未配置
- 本地远端跟踪引用：无
- 远端实时状态：待确认；本轮未 fetch、未 push
- Day 5 相关文件已提交；交接提交完成后暂存区和项目工作区应为空
- `PLAN.md`：经用户明确授权，Day 5 五项任务已勾选，开发日志已标记完成；Day 6 未修改
- `.agents/`：无关目录，未读取、未修改、未提交
- `.env`：未查看、未输出、未修改、未提交；真实验收通过现有配置由应用读取

## Day 5 已完成

- 依赖：`langchain-text-splitters>=1.1,<1.2`、`tiktoken>=0.13,<0.14`
- 配置：默认 `CHUNK_SIZE=500`、`CHUNK_OVERLAP=100`、`CHUNK_ENCODING_NAME=o200k_base`
- `split_pages()`：逐页切分，空白页跳过，原页码保留，文档内 `chunk_index` 从 0 连续递增
- `Chunk`：UUID 主键、Document 外键、级联删除、唯一顺序、JSONB 元数据、`doc_id` 索引
- 上传事务：Document 第一次 flush → Chunks 第二次 flush → 文件移动 → commit
- 失败补偿：切分、两次 flush、文件移动或 commit 失败均不留下半完成数据
- 成功响应仍只有 `id/filename/size/status/created_at`
- 300/500/800 token 结构实验已记录，不包含检索质量结论
- 只对新上传文档切分，不回填 Day 4 历史数据
- 未实现 Embedding、Qdrant、检索或其他 Day 6+ 功能

## 最终验收

- Python：`3.11.15`
- 标准测试：`60 passed, 1 skipped, 1 warning in 5.26s`
- 真实 PostgreSQL：`61 passed, 1 warning in 4.67s`
- PostgreSQL JSONB、Chunk 页码/顺序、Document 删除级联：通过
- `python -m backend.app.models.init_db`：既有验收通过，可新建缺失的 `chunks` 表
- `pip check`：既有验收为 `No broken requirements found.`
- compileall：既有验收通过
- `git diff --check`：本轮通过，仅有既存 LF→CRLF 提示
- 当前失败测试：无

旧交接记录中的 `58 passed` / `59 passed` 是新增两个切分兜底测试前的数字；本轮重新执行
全部 61 个测试项后，标准环境跳过 PostgreSQL 用例，真实 PostgreSQL 环境全部通过。

## 当前错误与风险

- pytest 仍有 `.pytest_cache` 的 `[WinError 5] 拒绝访问` 警告；根因待确认，不影响测试通过。
- `docker compose ps postgres` 普通权限报 Docker config/named pipe `Access is denied`；授权后两次查询超时。
  但显式建表及真实 PostgreSQL 测试均成功，数据库本身可用。
- `o200k_base` 第一次使用需要下载词表；本机已完成缓存。新环境的预热/离线缓存策略待确认。
- 文件移动后进程立即崩溃仍可能留下孤儿文件；启动清理任务未实现。
- `_cleanup_failed_upload()` 读取 SQLAlchemy 私有事务 `_state`，未来升级需验证兼容性。
- Git 持续提示部分文件未来可能由 LF 转为 CRLF；是否加入 `.gitattributes` 待确认。
- 远端实时状态、是否配置上游及是否推送仍待确认。

## 唯一下一步

保持暂停。等待用户明确选择是否检查/配置远端并推送，或另行授权开始 Day 6。
推送和 Day 6 必须分别获得明确授权。
