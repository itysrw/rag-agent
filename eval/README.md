# Day 17 冻结评测数据集

样本版本：`day17-v1.1`；冻结语料版本仍为 `day17-v1`。正式样本是 [eval_dataset.jsonl](eval_dataset.jsonl)，恰好 50 条。六份来源 PDF 原样保存在 [corpus](corpus/)；[corpus_manifest.json](corpus_manifest.json) 固定官方地址、SHA-256 和物理页数。样本只记录问题、参考答案和最小充分的文件名／一基物理页码，不含运行结果。

语料来自美国联邦紧急事务管理署（FEMA）的 Ready.gov 灾害说明：地震、洪水、飓风、龙卷风、野火和冬季风暴。官方 [出版物复用条款](https://www.ready.gov/publications) 允许组织复制出版物，要求保持原内容、照片、图形和图表不变，且不得暗示 FEMA 或美国政府为本项目背书。仓库保存的是原版 PDF；中文问答是另行撰写的标注，不作为 FEMA 原文或官方译本。没有使用旧的 Day 9–12 合成调优题。

每行固定六字段：`id`（`qa_001` 至 `qa_050`）、`category`、自包含的 `question`、简洁的 `expected_answer`、始终为数组的 `expected_source` 和 `difficulty`。来源元素只有 `filename`、`page`。四类为 `simple_fact`（单处事实）、`cross_paragraph`（两处证据组合）、`multi_hop`（比较或条件推导）、`unanswerable`（整个冻结语料无答案）。难度是独立的 `easy`、`medium`、`hard`。无答案统一使用“知识库中没有相关信息”及空来源。

| 类别 | easy | medium | hard | 合计 |
|---|---:|---:|---:|---:|
| simple_fact | 12 | 6 | 0 | 18 |
| cross_paragraph | 2 | 7 | 3 | 12 |
| multi_hop | 0 | 4 | 6 | 10 |
| unanswerable | 1 | 3 | 6 | 10 |
| 合计 | 15 | 20 | 15 | 50 |

无答案题中，明显无关 3 条（41–43），同领域信息缺失 7 条（44–50）。多跳题至少六条跨文档。来源按回答所需的推理顺序记录；PDF 页码按文件从 1 开始的物理页码，不按印刷页码。问题、答案和来源依据原 PDF 逐页编写；没有从本项目 RAG 回答或检索排名反推真值。

`day17-v1.1` 仅替换 `qa_048`–`qa_050` 的问题：原题的前提可由 `earthquake.pdf`、`flood.pdf`、`winter-storm.pdf` 各自第 2 页的明确禁令纠正，不应标为无答案。新题分别询问语料未给出的电视固定、集水坑泵备用电池和水管保温参数。其余 47 条、类别及难度分布和冻结语料不变。

该语料为英文原文配中文问答，涉及美国灾害应对语境。本数据集不代表中国地区的应急指引。2026-11-07 用户确认 Day17 审查、测试与修复通过；本机已用与 manifest 哈希相同的六份文件完成上传与索引，其他环境仍需独立导入。入库与回归记录见[Day17 完成记录](../docs/day17-eval-completion.md)。Day17 完成时尚未测量回答质量，首份实测见[Day18 真实评测基线](../README.md#day18-真实评测基线)。任何后续事实标注修正均须记录理由并更新版本，不得按模型结果删题或改写困难样本。


## Day18 单轮评测

2026-11-08 用户确认审查、测试与修复通过；冻结 50 题的首份真实运行全部正常返回，65 次模型请求，规则准确率 11/50。Day18 五项计划已勾并形成本地提交。指标见[README 实测摘要](../README.md#day18-真实评测基线)；`eval_report.md` 与逐题运行记录被 Git 忽略，仅保存在本机。

从仓库根目录运行。模拟使用现有 LangGraph 图与固定替身，逐题验证执行、评分和报告。

~~~powershell
.\.venv\Scripts\python.exe -m eval.eval --mode mock
~~~

每次运行都有独立目录 data/eval/day18/<run_id>/，含 eval_results.jsonl、run_metadata.json 和 eval_report.md。报告标明模拟或真实，以及完成状态。模拟报告留在运行目录。

新的正式评测运行需要单独授权。启动进程须已提供 `POSTGRES_PASSWORD` 和 `LLM_API_KEY`，以及本机所需的其他项目环境变量。评测脚本从进程环境读取设置，使用 DeepSeek 官方端点和本机已缓存的固定版本 BGE 模型。

~~~powershell
.\.venv\Scripts\python.exe -m eval.eval --mode real --allow-paid --max-llm-requests 100
~~~

正式运行先核对六份已上传文件的哈希、PostgreSQL 全部 ready 文档及 Chunk 的 300/60 切分参数，以及 Qdrant 集合全部 Point 的身份和关键载荷。运行期间需要保持语料稳定。语料发生漂移、凭据无效或预算耗尽时停止，并保留已记录的题目。预算统计实际请求尝试，关闭 SDK 自动重试。完整真实运行通过末次语料核对后生成 eval/eval_report.md。

- 题集、清单和评分规则记录 SHA-256。文本哈希统一使用 LF，PDF 哈希按原始字节计算。
- 每题独立运行。当前候选覆盖同一次搜索的完整重排名单，最多 20 个片段。逐题文件记录物理页、得分及是否进入生成上下文。Day18 历史结果的候选口径为重排前 5 个片段。
- 整体规则准确率分母为 50。引用全命中和联合通过率分母为 40，要求覆盖全部必需页。正确拒答率分母为 10。执行错误和未运行题保留在分母中并分别计数。
- 首题单列，后续延迟给出 P50/P95。计时覆盖 Agent 工具选择、检索、重排和生成，不含 HTTP、会话落库、评分和写报告。
- 评分事实组的 any_of 列出可接受表达，none_of 列出明确冲突。文本先做 NFKC、大小写和空白规整。规则分数可结合逐题记录人工抽查。
