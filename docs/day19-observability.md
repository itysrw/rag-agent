# Day19：请求 trace 与查询

更新时间：2026-11-14。生产 `POST /chat` 的已校验业务请求在入口创建独立 trace，JSON 返回或 SSE 真正终结时，尽力写入 PostgreSQL `request_logs`。Day19 本地实现与离线测试已完成；真实 PostgreSQL 的 trace 建表及在线验收尚未执行。另有获授权的付费完整 RAG 分块对照，结果单列在[实验记录](day19-full-comparison.md)。

## 记录内容与边界

一条 trace 使用同一个 UUID 关联原问题、独立检索问题、已验证工具调用、同次搜索的重排候选、原向量证据门结果、最终答案和可信 `sources`、每次模型调用的阶段及 provider token 用量、UTC 起止时间、端到端耗时、HTTP 状态、业务结果、错误类别和整轮会话是否已提交。候选中的 `included_in_context` 表示是否通过现有 `vector_score >= 0.46` 门槛；候选和最终引用是两份不同证据。

不保存 Chunk 正文、完整 Prompt、向量、原始异常文本或密钥。`prompt_tokens` 和 `completion_tokens` 仅汇总实际供应商响应；任一次调用用量缺失或流被中断，两项合计均为 `null`，`usage_complete=false`。固定拒答没有生成阶段 token，但仍可能有工具选择及多轮改写调用。

SSE 的 `http_status=200` 只表示 HTTP 响应已启动。流内错误记 `outcome=error`；客户端在 `[DONE]` 前离开记 `outcome=cancelled`。如果答案已保存但来源事件未送达，`business_committed=true` 且结果仍为取消。会话整轮保存和 trace 写入使用独立事务；trace 数据库写失败只记录安全的异常类别，不改变已成功的聊天响应，因此它不是零丢失审计日志。

请求体校验失败的 422、RAG 依赖在路由函数前无法构造等入口拒绝，当前不创建 trace，也不保存未校验的原始请求体。`/health`、上传和检索调试接口不创建聊天 trace。

## 启用与查询

先在目标 PostgreSQL 上执行现有显式建表入口 `python -m backend.app.models.init_db`，由它创建尚不存在的 `request_logs`。`create_all()` 不迁移已有表；既有部署需按实际数据库状态检查。未建表或数据库不可用时，聊天仍按原契约响应，但 trace 无法持久化。

`GET /admin/traces?limit=20` 按 `created_at DESC, id DESC` 返回最近记录，`limit` 为 1–100。由于记录含原问题和答案，必须通过进程环境变量 `ADMIN_TRACE_TOKEN` 设置独立管理员密钥，并以 `X-Admin-Token` 请求头提交。密钥不从项目 `.env` 读取，不出现在响应或普通日志中；未配置时接口返回 503，密钥错误返回 403。该接口的成功与错误响应均设置 `Cache-Control: no-store`。普通 `/chat` 不依赖管理员密钥。

## 本地验收与面试表述

本次完整后端测试：`724 passed, 14 skipped, 0 failed`，退出码 0；14 项真实集成等跳过项不计为通过。测试使用 SQLite、模型替身及分块指标的确定性样例；[不付费向量对照](day19-chunk-comparison.md)实际调用本机缓存的 BGE 模型。[完整 RAG 对照](day19-full-comparison.md)另在隔离 PG/Qdrant 环境中使用真实模型完成 150 条逐题结果；这不等于生产 `/chat` trace 在线验收。

可据实表述：Day18 的真实 50 题中，有答案题的候选来源全命中为 30/40，最终引用全命中为 6/40。Day19 因此加入请求级 trace，区分工具选择、同次检索候选、证据门、生成和持久化阶段。[不付费向量对照](day19-chunk-comparison.md)发现原 o200k-token 500/100 有 7 个块超过 BGE 上限；合格三组的纯向量 Top5 全页命中为 21/40、16/40、22/40。另经授权的[完整 RAG 对照](day19-full-comparison.md)中，200/40（o200k）与 500/100（BGE token）最终来源命中均为 7/40，300/60（o200k）为 6/40。BGE-token 500/100 不是超限的原方案；对照并非通过生产 trace 得到，也未显示 500 独占最高。Day18 真实语料使用一次性的 300/60 分块。
