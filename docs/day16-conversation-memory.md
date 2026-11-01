# Day16：PostgreSQL 多轮记忆

日期：2026-11-01（Asia/Shanghai）。分支 codex/day16-conversation-memory。
父检查点 a006139f4ae1406c5f20144730c76fe122d0c2bc；独立本地实现提交的SHA以git log -1核对，不推送或合并。
功能实现与标准验收已完成，PLAN保持只读，Day16勾选仍等待用户独立确认。Day17未开始。

## 调用链和客户端

~~~text
POST /chat {message, stream, session_id?}
 -> PostgreSQL打开/创建会话，最近10条完整消息，关闭Session
 -> 最近5轮 / o200k_base 默认2000 token
 -> 有历史：rewrite_query_node -> select_tool_node
    无历史：select_tool_node
 -> tool_node（一个白名单工具） -> generate_node
 -> user/assistant同事务保存 -> 返回
~~~

JSON响应保留answer/model/sources，新增session_id；SSE新增X-Session-ID响应头。
首次不传session_id会创建UUID；后续携带它即可继续会话：

~~~json
{"message":"刚才那个文档还说了什么？","session_id":"首次响应返回的UUID","stream":true}
~~~

SSE仍为delta -> sources -> [DONE]，不输出历史、工具参数或State。
内部合法PreparedRAG仍直接generate_node，不创建、读取或保存会话。
实际编译图见[day16-conversation-memory.mmd](day16-conversation-memory.mmd)。

| 条件 | HTTP/流行为 |
|---|---|
| 非法UUID | 422 |
| 不存在session | 404，模型调用0 |
| 同session运行中 | 409，冲突请求不调用模型或工具 |
| PG配置/连接/超时或记忆配置错误 | 安全503 |
| 会话内部查询/写入错误 | 安全500 |
| 改写请求或JSON无效 | 安全502，不降级、不执行选择 |
| 流开始后的生成/保存错误 | error后停止，不发sources/DONE |

## 数据、截断和改写

- conversations为UUID及UTC aware created_at/updated_at。
- messages包含UUID、CASCADE外键、sequence_no、role、完整content和UTC时间。
- sequence_no>=1、会话内唯一并索引；数据库约束role=user/assistant与非空内容。
- ORM message_metadata对应数据库metadata/JSONB；user为{}，assistant仅保存当前可信sources的filename/page。
- 一轮是user+assistant，读取最新10条再按sequence_no升序；孤立、错序历史安全失败。
- 存储不截断；Prompt优先保留最新完整轮次，只有最新一轮超限才在合法Unicode token边界截内容。
- 预算包含role/content/sources的紧凑JSON；元数据本身过长时删除完整来源条目，不捏造截短文件名。
- MEMORY_MAX_TURNS固定5，MEMORY_MAX_TOKENS默认2000/范围128..16000，MEMORY_ENCODING_NAME固定o200k_base。

LLMClient.rewrite_query采用非流式JSON Output、thinking disabled、max_tokens256、SDK retry0，不发送tools。
只接受单choice、finish_reason=stop、非空JSON object及唯一字段standalone_query，strip后1..4096字符。
重复键、额外字段、坏JSON、错误类型、无效Unicode、过长或截断输出均拒绝，不静默降级。
依据：[DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)；本轮未运行真实改写能力探测。

AgentState分开保存原始query、standalone_query和截断history；节点不覆盖query，数据库保存规范化原问题。
选择和搜索使用独立问题；详情UUID只能来自原问题或截断历史，不能只靠改写凭空添加UUID。
有历史时最终Prompt包含历史、原问题、独立问题和当前工具结果，历史为不可信JSON，只用于理解指代。
事实与sources只取当前工具结果；无证据固定拒答，旧答案不能补充事实或来源。
保留Hybrid20 -> CPU BGE Rerank5 -> 原始vector_score默认0.46，BM25-only不生成。
第一轮选择1次；有历史增加改写1次；拒答只省最终生成。内部PreparedRAG拒答才是总LLM0次。

## 保存、并发与取消

读取DTO后关闭Session，不持有事务等待模型。成功时user+assistant和updated_at同事务提交，任一失败全回滚。
SSE校验最终answer与全部delta一致后才保存，成功后再发sources/DONE。
断流、生成失败、不完整消费均不保存部分答案。
保存期间仍持会话锁；取消可发信号，flush后提交前检测取消并整轮回滚，事务结束才释放锁。
已提交完整轮次后发生的网络失联不能撤回事务，不宣称提交与客户端收到DONE是原子操作。
互斥跨同一进程的服务实例共享，不同session可并行；不等于多worker分布式锁。

## 显式建表与测试

部署前使用已有安全配置，显式运行：

~~~powershell
.\.venv\Scripts\python.exe -m backend.app.models.init_db
~~~

init_db注册新表并create_all，不修改既有表，不在启动或health建表。
本轮未执行真实数据库建表、启动服务或读取项目.env。
新增test_conversation_postgres.py默认跳过，须单独启用RUN_CONVERSATION_POSTGRES_INTEGRATION=1并提供进程PG配置；
它使用_env_file=None，只创建缺失记忆表并验证两轮事务，清理自己创建的会话。
Day15付费选择入口继续关闭；本轮无真实改写、真实PG或付费调用。

- 开工完整离线基线：571 passed/13 skipped（16.85s）。
- 最终完整backend/tests：**644 passed / 14 skipped（18.83s），0失败/0警告**，Python3.11.15，退出码0。
- 取消落库定向回归：90 passed（17.90s）。
- .env读取/真实服务连接尝试0、付费0；无BGE模型下载或服务操作。
- 14跳过为原13项及新增PG入口，不代表全真实组合通过。
- 覆盖0/1/5/6轮、顺序、中文/Emoji/特殊词、Token预算、事务回滚、指代、JSON/SSE混用、UUID来源、双session隔离、404/409/500/502/503、ASGI断连/取消、提交前取消回滚及Day15行为。
- OpenAPI除ChatRequest.session_id外与开工快照完全一致。
- PLAN、requirements、底层检索/模型及旧实验报告不变；原六份交接正文与D-001至D-064保留。
- 初期失败与处理见[机器记录](day16-conversation-results.json)，没有放宽断言或使用假分词器。

完整测试由本机隔离运行器调用pytest.main(backend/tests -v)，禁dotenv/真实连接、缓存和LangSmith插件，使用新GUID临时目录。
本机目录权限限制通过获准的正常执行权限处理，没有修改ACL或清理旧缓存。
缺失的公共o200k_base词表单独取回并验证SHA256后用于离线测试，未下载检索模型。
运行器、原始日志、OpenAPI、六文档备份/diff在仓库外本次day16-validation目录；未来可用性和当前服务健康待确认。
不增加会话管理API、长期记忆、checkpointer、工具循环、新供应商、依赖或Day17内容。
