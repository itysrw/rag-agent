# 后续任务

更新时间：2026-07-15（America/New_York）

## P0：恢复状态并等待用户指令

Day 4 已由提交 `623989f feat: complete Day 4 document upload` 完成。当前没有获授权的开发任务。

新会话只允许：

1. 完整阅读 `HANDOFF.md`、`STATUS.md`、`DECISIONS.md`、`TODO.md`、`AGENTS.md`、`README.md`、`PLAN.md`、`docs/architecture.md` 和 Day 4 关键代码/测试；
2. 只读核对 Git 状态；
3. 准确复述并报告差异；
4. 等待用户下一条明确指令。

当前禁止：读取 `.env` 或 `.agents/`、自行修改代码、修改 `PLAN.md`、提交、推送、开始 Day 5。

## 当前工作区

- Day 1 至 Day 4 和三份交接刷新均已本地提交，因 GitHub 网络不可达而尚未发布；
- 另一个编辑流程正在产生配置、依赖和 Day 5 相关本地修改，实时清单以 `git status` 为准，
  均未纳入本次发布；
- `.agents/` 是无关未跟踪目录，不属于项目提交。

禁止读取可能含密钥的 `.env.example`，也不得修改、提交或删除上述本地改动和 `.agents/`，
除非用户另行明确授权。

## P1：仅在用户明确授权后开始 Day 5

`PLAN.md` Day 5 原始范围：

- 安装 `langchain-text-splitters`，不用完整 LangChain；
- 实现 `RecursiveCharacterTextSplitter`；
- Chunk 字段：`doc_id`、`chunk_id`、`content`、`page`、`metadata`；
- 对比 300 / 500 / 800 token 三种 chunk size；
- 建立 `chunks` 表，切分结果写入 PostgreSQL。

开工前待确认：token 计数器、chunk overlap、chunk 主键/顺序、metadata 结构和类型、外键/删除/索引、建表或迁移方式、对比语料与指标。禁止自行补全。

## 延后且待确认

- 网络恢复后重试 `master` 首次推送并配置上游；
- 孤儿文件启动清理任务；
- 首次表结构变更时引入 Alembic；
- pytest `.pytest_cache` 权限警告；
- `.gitattributes` 行尾规范；
- Day 6 Embedding 供应商；
- Day 18 千问质量/成本对比。

## Day 4 验收记录

- 真实 PDF/PostgreSQL 往返：通过；
- 全量 pytest：`44 passed, 1 warning in 3.22s`；
- 发布前常规 pytest：`43 passed, 1 skipped, 1 warning in 3.29s`；
- 当前失败测试：无；
- `pip check`、compileall、Compose、差异和密钥检查：通过；
- `GET /health` 与 Day 3 `/chat`：回归通过；
- PostgreSQL 本次交接查询：`Up (healthy)`。
