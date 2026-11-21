# 当前架构：四服务部署与 RAG 问答

## Day21 Docker Compose

`docker compose up --build --wait` 构建前后端并等待四个服务健康。PostgreSQL 和 Qdrant 就绪后，后端先执行 `init_db` 再启动 FastAPI。Streamlit 等待后端健康，并通过容器网络访问 `http://backend:8000`。启动命令与端口设置见 [README.md](../README.md#docker-compose-启动day21)。

~~~mermaid
flowchart LR
    PG[(PostgreSQL)] -->|健康后启动| API[FastAPI]
    Q[(Qdrant)] -->|健康后启动| API
    API -->|健康后启动| UI[Streamlit]
    Browser[浏览器] --> UI
    UI -->|HTTP 与 SSE| API
~~~

PostgreSQL、Qdrant 和后端数据各有命名卷。后端数据卷保存上传、模型及分词缓存。前端、后端和 PostgreSQL 的宿主机端口绑定回环地址，Qdrant 通过容器网络访问。Compose 的数据卷配对和管理员令牌转发已通过配置测试。[Compose 配置](../docker-compose.yml)

## Day20 Streamlit、同轮工具与引用

2026-11-20 检查点。Streamlit 的 `frontend/app.py` 通过服务端 `frontend/api_client.py` 请求 FastAPI。目录走 `GET /documents`，上传走 `POST /documents/upload`，问答走 `POST /chat`。SSE 正文增量直接呈现，`X-Agent-Tool` 和本轮 `sources` 随收到合法 `[DONE]` 一起确认。工具名来自同请求 recorder。Day19 的独立管理员 trace 继续供管理侧使用。

页面会话状态由 `UiSession` 管理。回环替身 `frontend/demo_backend.py` 复用同样的普通接口，用于已通过的无付费浏览器验收。真实单轮 HTTP 验收覆盖 FastAPI、Qdrant、DeepSeek 和 PostgreSQL 同会话 trace，管理员读取另行验证。启动、验收边界和记录见 [Day20 本机演示](day20-streamlit.md) 和 [HANDOFF.md](../HANDOFF.md)。下方 Day19 章节记录检索与 trace 的既有架构。

---

## Day19 请求 trace、来源页筛选与评测

`003e0a1` 发布的补页规则保留同次重排的完整候选，聊天与评测共享证据选择器，生成最多使用 5 个片段。独立重排接口返回前 5。离线 50 题的生成前来源页全命中为 31/40，改良后的全量生成质量待评估。[证据筛选对照](day19-evidence-gate.md)

后端使用 PostgreSQL 业务会话与四节点 LangGraph。Day18 评测复用单轮图，输入为 Day17 冻结的六份 Ready.gov 英文 PDF 和 `day17-v1.1` 的 50 道中文题。Day19 的 `/chat` recorder 记录同轮检索、模型用量及 JSON/SSE 终态，通过独立短事务写入 `request_logs`。管理员查询由独立密钥保护。[评测说明](../eval/README.md) · [Day19 可观测性](day19-observability.md)

~~~mermaid
flowchart LR
    Chat[POST /chat] --> Trace[请求级 TraceRecorder]
    Chat --> Graph[LangGraph 四节点]
    Graph -->|改写/选择/生成| Usage[同次供应商 usage]
    Graph -->|工具执行| Candidates[同次重排候选与入选证据]
    Graph --> Memory[(会话整轮事务)]
    Usage --> Trace
    Candidates --> Trace
    Memory --> Trace
    Trace -->|JSON 返回或 SSE 终结| Logs[(request_logs 独立事务)]
    Admin[GET /admin/traces + 管理员密钥] --> Logs
~~~

~~~mermaid
flowchart LR
    Inputs[冻结 QA / PDF 清单 / 评分规则] --> Validate[输入结构与哈希预检]
    Validate --> Stores[只读核对 PG 六文档及 Qdrant 25 点]
    Stores --> Models[核对固定本地 BGE 缓存]
    Models --> Graph[单轮 LangGraph 真实工具选择]
    Graph --> Capture[同次 search 记录重排候选与入选证据]
    Capture --> Score[40/10 固定分母的规则评分]
    Score --> Rows[逐题 eval_results.jsonl]
    Rows --> FinalCheck[末次语料核对]
    FinalCheck --> Report[运行清单与 eval_report.md]
~~~

[load_inputs](../eval/scoring.py#L197) 验证题集和规则，[verify_corpus](../eval/real.py#L106) 检查全部 ready 文档和目标集合，[EvalAgent](../eval/agent.py#L167) 调用 `RAGGraphRunner.complete(question, history=())`，[run_evaluation](../eval/eval.py#L263) 写逐题结果与报告。历史 Day18 真实基线 50/50 正常、65 次实际请求、规则准确率 11/50、前 5 候选来源 30/40、最终引用 6/40。摘要和本地报告位置见 [Day18 基线](../README.md#day18-真实评测基线)。

2026-11-20 的真实单轮 SSE 已验证向 PostgreSQL 写入同轮会话消息与 trace。管理员查询接口的真实环境读取待单独验收。Day21 的 Compose 启动顺序及配置验证见上文。[真实联调记录](day20-streamlit.md#2026-11-20-真实-http-sse-和-trace-验收通过)

---

# 历史档案：Day17 交接时的架构说明

> **当前检查点（2026-11-08）**：Day17 只增加六份原版评测语料、`day17-v1.1` 的 50 条 QA 与离线验证，不改变 Day16 运行图。分支 `codex/day17-eval-dataset` 的 `6f252c2` 已推送；11月8日离线标准 660 passed/14 skipped、退出0。本机六文档于11月7日入库、索引 25 Point，临时 300/60，默认配置未变。50 题真实准确率和实时服务健康待确认。架构图描述当前实现，详细状态见[HANDOFF](../HANDOFF.md)与[Day17 完成记录](day17-eval-completion.md)。
> 下方 2026-11-02 的分支、HEAD 和“Day17 未开始”属于历史交接快照。

---

# 当前架构：Day16短期多轮记忆

更新时间：2026-11-02（Asia/Shanghai）

功能开发暂停。当前分支codex/day16-conversation-memory，HEAD 115d9a228cae8580a1d7ab1ca5d23ab5e41ea49d，
父74949214e8f163fbdfa2e035993a640ab866026e。Day16五项/日志已勾，两次提交仅本地、无上游；远端未见Day15/16。
最新标准652 passed / 14 skipped（45.43s），历史644/14不是当前结果。
本轮仅同步六文档，不重跑测试/服务、不提交推送；下一步最小改动0，等只读核对后的状态确认和唯一动作。
完整符号/行号/错误/命令见[HANDOFF](../HANDOFF.md)，理由见[DECISIONS](../DECISIONS.md)，规范见[AGENTS](../AGENTS.md)。
[PLAN](../PLAN.md)本轮只读，Day13四项/日志未勾、Day17以后未开始。

## 目标与已实现范围

最终目标是企业知识库RAG Agent：FastAPI、PG/Qdrant、CPU本地模型、compatible LLM、LangGraph，
再交付自然50条QA/答案评测、完整trace、Streamlit和完整Docker Compose。
当前后端具备上传/切分/显式索引、四类检索调试API、单工具Chat、PG业务消息与短期指代记忆。
没有长期画像/总结/向量记忆、图checkpointer/PostgresSaver、循环/并行工具、会话管理HTTP API或用户认证。

## 数据导入与检索

~~~mermaid
flowchart TD
    Upload[PDF / MD / TXT] --> Parse[按页解析与大小限制]
    Parse --> Split[o200k_base 500 / 100]
    Split --> PG[(PostgreSQL documents / chunks)]
    PG -->|用户显式索引命令| Read[读DTO并关闭Session]
    Read --> BGE[CPU BGE 512维与长度预检]
    BGE --> Q[(Qdrant documents)]
    Question[独立问题] --> Vector[向量候选20]
    Q --> Vector
    Question --> BM25[BM25候选20]
    PG --> BM25
    Vector --> RRF[等权RRF60取20]
    BM25 --> RRF
    RRF --> Rerank[CPU BGE 重排最多20个候选]
    Rerank --> Gate[筛选并选取最多5个证据片段]
    Gate --> Generate[当前结果生成或固定拒答]
~~~

上传以1MiB分块、实际≤20MiB，PDF≤500页；UUID.part完成后os.replace。
Document与Chunk同事务两次flush，页边界不混合；不在上传时自动Embedding/索引。
init_db只显式create_all缺失表，不迁移/回填；init_qdrant验证既有collection，不自动重建。
PG和Qdrant无跨库事务/outbox，删除同步未做；多worker BM25各自维护快照。
BM25读全局ready数据，完整指纹刷新、全局IDF；token overlap门，doc_id在TopK前过滤；刷新失败不返回旧数据。
Hybrid顺序执行两路各20，按chunk UUID等权Σ1/(60+rank)，稳定排序；重复/冲突失败，不静默降级。
Rerank对完整最多20候选打原logit，取5；rank_change=hybrid_rank-rerank_rank，query不截断。
Chat 先在前五名建立初始证据，再用完整的重排名单补不同来源页。生成仍最多使用五个片段。规则及验证见[证据过滤对照](day19-evidence-gate.md)。

## 会话与图编排

~~~mermaid
flowchart TD
    Chat[POST /chat] --> Open[验证配置 / 取得lease / 读取会话DTO]
    Open --> History[最近5个完整轮次 / 2000 token]
    History --> Start{START条件}
    Start -->|公共无历史| Select[select_tool_node]
    Start -->|公共有历史| Rewrite[rewrite_query_node]
    Start -->|内部合法PreparedRAG| Gen[generate_node]
    Rewrite --> Select
    Select --> Tool[tool_node 恰好一个工具]
    Tool --> Gen
    Gen --> Complete{完整成功}
    Complete -->|公共| Save[(user + assistant 同事务保存)]
    Complete -->|内部| End[END / 不读写会话]
    Save --> Reply[JSON 或 sources / DONE]
~~~

4个注册业务节点；首轮只运行选择/工具/生成3个，有历史再先改写。
内部PreparedRAG不创建/读取/保存会话，不改写/选择/执行工具，复用原生成及拒答。
RAGService负责业务调用和事务回调，RAGGraphRunner负责图事件/预取与安全协议；图不决定HTTP细节。
业务消息持久化与图运行State分开；服务、客户端、DB Session、lease/control均不进入State。

| AgentState | 不变量 |
|---|---|
| query | strip后的原问题1..4096字符，节点不覆盖，数据库存它 |
| standalone_query | 首轮同query；改写后供选择/搜索 |
| history | 截断后不可变DTO，最多10条，仅用于指代，不是当前事实 |
| needs_query_rewrite | 公共有历史True，改写后False；首轮/内部False |
| retrieved_docs | 同次搜索的完整重排候选，最多20个，目录为空 |
| prepared | PreparedRAG或None，含question/messages/sources/has_relevant_context |
| answer | 完整清理后的答案 |
| tool_calls | 公共最终1，内部0 |
| needs_tool_selection | 公共True，选择后False；内部False |

AgentUpdate不包含query/history；AgentContext仅response_mode=complete/stream；无message reducer/checkpointer/thread_id。
实现图见[Day16 MMD](day16-conversation-memory.mmd)及[验收MD](day16-conversation-memory.md)。
旧[Day14图](day14-agent-graph.mmd)、[Day15图](day15-agent-tools.mmd)保留原阶段含义，不当作当前编排。

## PG业务消息、Token预算与一致性

Conversation：conversations表，UUID主键、UTC aware created_at/updated_at。
ConversationMessage：messages表，UUID、conversation_id外键ON DELETE CASCADE、sequence_no>=1、role=user/assistant、
非空content、created_at；UNIQUE(conversation_id,sequence_no)及组合索引。
message_metadata属性映射SQL metadata，PG JSONB/SQLite JSON；user={}，assistant仅当前安全sources。
不存Prompt、Chunk、工具参数、分数、Token用量、延迟、长期画像或图checkpoint。

open_session(None)先创建空会话；已有ID必须存在。最新10条按sequence_no DESC读取后反转，
验证奇数起始/连续序号/user-assistant成对，损坏历史安全失败；DTO返回前关闭Session。
每轮2条，最多5轮；token计数包含role/content/sources的紧凑JSON，默认o200k_base/2000，范围128..16000。
从最新完整轮向旧轮累加，输出恢复时间顺序；只在最新轮单独超限时裁内容，保证Unicode，来源过长删完整条目。
DB保留全文。空历史不加载词表。o200k是近似口径，不是DeepSeek精确tokenizer。

process-global集合+Lock分配ConversationLease，同UUID冲突409，跨本进程服务实例共享；lease幂等释放。
append_turn短事务锁会话行，检查末序号偶数，原始user/完整assistant/updated_at同事务；flush后检查取消，失败整轮回滚。
保存时持流RLock及lease到commit/rollback结束；DB行锁保证追加序号，不是多worker生成请求级锁。
首轮选择/生成/保存异常补偿delete_empty_session：只删除本次新建且无消息会话，已有/非空不动，补偿失败不盖主错误。
正常close/GeneratorExit/断开不保证删除空会话；已提交完整轮次后网络失联不能撤回，不保证DB与DONE传输原子。
UUID隔离不是多用户鉴权；本轮没有检查真实PG新表是否已建或运行数据。

## 改写、单工具与可信来源

LLMClient.rewrite_query先于工具选择，仅有历史时执行；非流式JSON Output、thinking关闭、SDK retry0，
max_tokens=4096，严格单choice/stop、无tools调用、UTF-8≤64KiB、仅standalone_query一个字段、无重复键，
结果strip后1..4096字符。失败安全502，不重试/降级，不修改原query。
原256 token属于D-067原实现，已由D-070修为4096 token；输出token数与结果字符上限不同。

选择非流式tool_choice=required、thinking关闭、SDK retry0；本地严格一调用、function白名单、ID/字段/类型/64KiB及重复键校验。
普通生成沿用原客户端行为，不宣称所有请求retry0。

| 工具 | 执行边界 |
|---|---|
| search_knowledge_base | 使用 state.standalone_query，重排混合检索候选并筛选最多5个证据片段 |
| get_document_detail | doc_id必须出现在原问题或本次截断历史，不接受仅改写新造UUID；ready安全列+chunk_count |
| list_documents | arguments严格{}；ready，created_at DESC/id ASC，最多51返回50+truncated |

目录仅id/filename/size/status/created_at；详情只聚合chunks ID，不读取正文/路径；sources=[]。
工具schema深拷贝、additionalProperties=false仍要本地校验；不动态反射或eval。
原问题/独立问题/历史/当前工具结果放user JSON，system只静态规则，防止数据提升为系统指令。
规则把当前工具结果规定为唯一事实依据；后端sources仅来自本轮实际结果，拒绝旧来源混入，实际模型遵循率待确认。
没当前证据固定拒答“知识库中没有相关信息”。首轮公共仍选择1次，有历史再改写1次；只省生成。
内部PreparedRAG拒答才是LLM总调用0。真实DeepSeek选择/改写准确率尚无结论。
目录完整/SSE保留S99.pdf/page 99.pdf/第1页.pdf/[S99.pdf]；8条回归不等于任意文件名穷举保证。

## JSON/SSE、背压与安全错误

ChatRequest message/stream/session_id；JSON answer/model/sources/session_id；SSE X-Session-ID。
RAGGraphRunner.start_stream沿同一graph.stream(updates/custom,version=v2)迭代器在HTTP前消费必要rewrite/select/tool更新，
PreparedRAG就绪后才建立流，错误保持原HTTP码；继续该迭代器，不重复工具或检索。
只发custom delta，逐段ack背压；PreparedRAGStream独立Context+RLock可跨线程推进。
完整答案须等于所有delta拼接；on_success保存完成后sources/DONE；on_failure一次补偿，close取消并幂等关闭图/sanitizer/上游。
ASGI取消保护清理；取消唤醒背压，阻塞同步I/O受已有timeout约束，不承诺任意I/O立即中断。

不存在会话404/忙409；记忆配置连接503/内部500；LLM缺配置503/选择改写生成502；非法输入422；
检索非法结果502/不可用503/内部500；目录503/500；图协议500。
流开始后安全error不发sources/DONE；不输出SQL/私有上游错误/工具参数/State/历史。
精确错误字符串和HTTP表见HANDOFF第8节，入口符号见第7节。
每次invoke/stream禁tracing与callbacks；health不触发图编译/服务/DB/模型。
排名日志是query哈希/长度、ID/rank/score/耗时等最小数据，不是Day19完整trace/request_logs，DB业务消息不存trace。

## 固定资源与验证边界

| 资源 | 源码默认/固定值 |
|---|---|
| Python | 3.11，最新标准3.11.15 |
| LLM | api.deepseek.com / deepseek-v4-flash / timeout60s，实际配置待确认 |
| BGE | bge-small-zh-v1.5 / revision 4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4 / CPU / 512维归一化 |
| Reranker | bge-reranker-base / revision 2cfc18c9415c912f9d8155881c133215df768a70 / CPU / max512 / batch4范围1..8 |
| Qdrant | documents、unnamed512/Cosine、localhost:6333、timeout10s、batch≤32/wait=True |
| PG | localhost:5432 / ragagent / postgres；不读取或输出密码 |
| 依赖 | sentence-transformers5.3.0、qdrant-client1.18.0、rank-bm25 0.2.2、langgraph1.2.16；Day16无新增 |

Reranker固定匿名六文件/safetensors/local_files_only/trust_remote_code=False，有限下载重试1/2/4s，无不安全回退。
Embedding与Reranker白名单不同，不互套。模型/词表/测试缓存和运行器属于本机资源，不能假设异机会有。
启动、建表、索引、标准和真实入口命令统一见HANDOFF第13节与[README](../README.md)，命令示例不等于执行许可。

最新验收见[Day16 JSON](day16-conversation-results.json)的completion_checkpoint：11月2日652/14，45.43s，
0失败/警告/dotenv/真实连接尝试/付费。顶层644/14、256 token与PLAN未变为11月1日历史，非现状。
[Day15 JSON](day15-agent-tools-results.json)最新历史571/13，顶层563/12更早；
最近真实局部仍10月29日3，历史全部本地真实仍10月28日413，均LLM替身，不能外推当前Day16。
真实PG记忆和付费选择入口已收录未执行；当前会话表、服务、缓存、代理及Docker根因待确认。
Day12受控24 Chunk/12正/3负，Hybrid 0.917/1/0.944、Rerank 0.917/1/0.958，Hit@1未提升且有无关候选升位；
不等于自然50QA或全链路性能。自然长文/表格/多跳、多worker锁、BM25扫描和跨库一致性待后续范围。

本轮保护104项源码/测试/规范/配置/PLAN/依赖/验收文件和70条决策正文；只有六份交接文档未暂存、暂存区空。
先只读复述状态/矛盾/最多5步，然后等用户确认唯一动作，不开始Day17。
