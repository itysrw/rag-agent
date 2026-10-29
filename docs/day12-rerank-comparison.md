# Day 12 本地 Rerank 实现与真实对比

**完成确认（2026-10-29）**：用户确认Day12已完成并授权勾选PLAN四项与开发日志。
本次标准回归403 passed/12 skipped（45.66s），覆盖ReadError及质量退化普通回归；
下文指标及413 passed全真实证据保留2026-10-28原记录。本次本地提交包含Day12实现，
提交前标准回归重新通过403 passed/12 skipped（15.93s）；未重跑真实集成，尚未推送。

日期：2026-10-28（Asia/Shanghai）。Day11 已独立发布为 b68b590；Day12 位于
codex/day12-rerank 工作区，当时尚未提交；2026-10-29后续本地提交收录本报告。机器证据见
[day12-rerank-results.json](day12-rerank-results.json)。

## 实现契约

- 固定本地 BAAI/bge-reranker-base，revision
  2cfc18c9415c912f9d8155881c133215df768a70，CPU，默认 batch=4（允许1..8），512 token。
- 只匿名下载六个配置/tokenizer/safetensors 文件；缓存优先、瞬时错误最多重试3次；
  trust_remote_code=False、use_safetensors=True、首次请求懒加载，空候选不加载模型。
- 向量/BM25各20 → 原有等权RRF60取20 → CrossEncoder全部评分 → 最多5条。
  Identity显式关闭默认Sigmoid；score是原始logit，仅用于排序，不是概率或拒答阈值。
- 稳定排序键为(-logit, hybrid_rank, doc_id, chunk_index, chunk_id)；
  rank_change=hybrid_rank-rerank_rank，正数表示上升。数量、身份唯一性、有限分数均校验。
- 模型tokenizer成对预检；完整query无法容纳时安全422。包装CrossEncoder内部tokenizer，
  将truncation=True明确转换为only_second/max_length512，只截passage并记录截断数量。
- POST /retrieval/rerank/search仅接收query和可选单UUID doc_id，禁止top_k/candidate_k/mode；
  results含共享Chunk字段、logit、hybrid_rank、rerank_rank、rank_change。
- Hybrid内部保留vector_score/bm25_score；不参与RRF、不进入Hybrid公共响应。
  /chat在Rerank Top5后仅用vector_score>=0.46作证据门；BM25-only不作为生成依据。
  无通过项固定拒答“知识库中没有相关信息”，不调用LLM。
- JSON answer/model/sources、SSE delta→sources→[DONE]及后端来源/引用清理保持原样。
  SSE开始前完成检索；LLM流失败只发送安全error，不发送sources或DONE。
- 完成日志记录哈希、ID、全部候选前后名次、logit、数量、截断数和耗时；不含query、
  正文、metadata、文件名或凭据。任一分支失败不降级。
- 错误：请求/模型输入超限422；非法结果/重复ID/payload冲突502；模型、分支或配置
  不可用503；BM25索引/内部融合错误500，响应不包含原始异常。

## 真实环境与方法

Python3.11.15；复用sentence-transformers==5.3.0、qdrant-client==1.18.0、
rank-bm25==0.2.2，没有新增依赖。既有PostgreSQL和Qdrant均在运行，本轮未重启。

沿用Day11的8页自撰手册、500/100 o200k_base、相同24个Chunk ID/payload、12正样本和
3负样本；保留问题、顺序和expected_phrase。命中仍只按NFKC+strip后正文包含固定短语
判定。Hybrid评估Top5，Reranker看到Hybrid Top20，正式collection不参与实验。
全部真实验收使用离线模型缓存和LLM替身，没有付费API调用。

## 聚合与逐题结果

| 方法 | Hit@1 | Hit@5 | MRR@5 |
|---|---:|---:|---:|
| Hybrid | 0.917 | 1.000 | 0.944 |
| Hybrid + Rerank | 0.917 | 1.000 | 0.958 |

Hit@5满足不低于1.000的要求；Hit@1没有提升。MRR收益来自远程接入正确目标3→2，
该题Top1仍未命中。不能据此宣称重排普遍优于Hybrid。

| 问题 | Hybrid首次命中 | Rerank首次命中 |
|---|---:|---:|
| 6203 | 1 | 1 |
| 五万元采购 | 1 | 1 |
| 网络组 | 1 | 1 |
| 全量备份 | 1 | 1 |
| 远程接入工具坏了应该找谁处理？ | 3 | 2 |
| 新人多久能拿到办公设备？ | 1 | 1 |
| 差旅单据交财务的截止日是什么时候？ | 1 | 1 |
| 周末什么时候做整库备份？ | 1 | 1 |
| VPN 出错后拨打哪个 6203 服务？ | 1 | 1 |
| 采购超过五万元要找最高负责人审批吗？ | 1 | 1 |
| 访客登记后如何进入办公区？ | 1 | 1 |
| 会议室最多能占用多久？ | 1 | 1 |

完整分类、expected_phrase、Top5候选的chunk_index/页码/原始logit和名次见机器证据。

## 三个具体名次变化案例

| 查询 / 候选 | 页 / chunk_index | Hybrid→Rerank | 变化 | 原始logit |
|---|---|---:|---:|---:|
| 远程接入 / 正确分机目标 | 3 / 6 | 3→2 | +1 | -1.914435 |
| 网络组 / 同页另一候选（非目标短语） | 3 / 7 | 4→2 | +2 | -2.459871 |
| 6203 / 年假页无关候选 | 2 / 5 | 17→2 | +15 | -3.641886 |

第三例保留了一次无关候选升位，该题正确目标仍为第1。首次命中指标不代表Top5每条
都正确；远程接入的首位错误也没有解决。没有删除失败样本或改变判据。

## 耗时、截断与拒答

| 观测 | 秒 |
|---|---:|
| 新RerankerService实例首次装载模型 | 2.832 |
| 该实例首次20候选predict | 6.562 |
| 同一首题热推理predict | 6.291 |
| 12正样本平均predict | 6.392 |

权重和tokenizer已缓存；同pytest进程中BGE/模型依赖已先加载，OS文件页缓存可能预热。
这不是系统重启后的物理冷启动，不含下载或完整HTTP耗时。未做p50/p95、QPS或batch2/4/8对比。

12正样本累计截断候选0；独立真实模型测试使用超长passage验证截断计数1。
三个知识库外负样本经完整真实链路及向量证据门后固定拒答率1.000，LLM调用数0。
Rerank调试接口仍返回排序结果，拒答来自RAG向量门，不来自logit阈值。

## 测试、失败修复与清理

- 2026-10-28最终标准：401 passed, 12 skipped in 17.93s；12项真实集成默认显式跳过。
- 同日开启全部真实集成：413 passed in 158.94s，无跳过。覆盖真实模型、同语料比较、
  rerank API/doc_id/空结果、上传/索引/Chat、JSON/SSE和负样本拒答。
- 首次定向回归157 passed/2 errors/1 warning：新测试临时目录父路径未创建，另有
  重复路由注册。已创建独占父目录、移除重复注册并增加回归；最终全量均通过。
- Xet首次权重下载未及时完成；停止后使用带超时的标准HTTPS下载同一固定safetensors，
  未更换模型/revision。pip check通过。
- finally删除临时day12_rerank_compare_* collection并验证不存在；独立finally删除
  临时Document并验证Chunk级联清理，不触及正式collection或用户数据。

## 复验

从仓库根目录执行，真实验收先准备完整缓存并保证既有服务可用：

```powershell
$rerankTestRoot='C:\Users\Public\codex-pytest-rag-agent-day12'
New-Item -ItemType Directory -Path $rerankTestRoot -Force | Out-Null
$rerankTestRun=Join-Path $rerankTestRoot ('verify-' + [guid]::NewGuid().ToString('N'))
$env:RUN_POSTGRES_INTEGRATION='1'
$env:RUN_QDRANT_INTEGRATION='1'
$env:RUN_LOCAL_EMBEDDING_INTEGRATION='1'
$env:RUN_RAG_INTEGRATION='1'
$env:RUN_RERANKER_INTEGRATION='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m pytest backend/tests -v --basetemp=$rerankTestRun -p no:cacheprovider -p no:langsmith_plugin
```

本机需为pytest指定新独占basetemp，先创建其父目录；不复用未知目录。标准回归将五个
RUN_*开关全部设为0。禁用langsmith_plugin用于隔离无关外部跟踪，anyio保留。
若需新的机器证据，显式设置DAY12_RERANK_REPORT_JSON到不存在的路径，测试独占创建，
不覆盖既有报告。原RAG真实集成现也要求RUN_RERANKER_INTEGRATION=1。

## 局限与范围

含合成审计标识的受控小样本不能外推自然长文档、表格或多跳。CPU重排约六秒；
Reranker只能重排已有候选，BM25全扫描/多worker快照及跨库无outbox/删除同步仍在。
BM25-only生成证据保守排除可能损失回答召回。

10月28实现与实验阶段曾保持PLAN原样；10月29用户确认后已勾选Day12四项及日志。
没有Day13/LangGraph、Query Rewrite、
记忆、前端、切分更换或付费API；requirements、Compose和schema未变。

依据：[BAAI模型卡](https://huggingface.co/BAAI/bge-reranker-base)、
[固定revision](https://huggingface.co/BAAI/bge-reranker-base/tree/2cfc18c9415c912f9d8155881c133215df768a70)、
[CrossEncoder文档](https://www.sbert.net/docs/package_reference/cross_encoder/model.html)。
实现同时核对了本机固定5.3.0的代码。

## 收尾核验

2026-10-28全量测试后独立只读检查：Day12临时Document=0、Chunk=0、专用collection=0。
当时GitHub实时master为b68b590；Day12当时保留16个tracked修改与9个相关新增文件，暂存区空。
git diff --check通过，本轮检查的34个本地Markdown链接无失效；模型缓存由Git忽略，
.env和.agents未进入跟踪。当时PLAN字节与Day11发布版本一致；10月29完成标记已按用户授权更新，依赖与Compose仍未改。
