# Day20 本机 Streamlit 演示

## 环境与启动

在仓库根目录执行。前端依赖锁定到 Streamlit 1.52.2、HTTPX 0.28.1，使用项目的 Python 3.11。

```powershell
.\.venv\Scripts\python.exe -m pip install -r frontend/requirements.txt
```

前端进程读取 `RAG_BACKEND_URL`，默认使用 `http://127.0.0.1:8000`。演示时两个进程都绑定回环地址。页面调用普通聊天及文档 API，管理员 trace、数据库与模型凭据由后端环境管理。

## 无付费录屏

在第一个 PowerShell 窗口启动替身后端。替身使用现有后端依赖中的 FastAPI 和 Uvicorn，文档元数据存在内存，上传内容不会保留。

```powershell
.\.venv\Scripts\python.exe -m uvicorn frontend.demo_backend:app --host 127.0.0.1 --port 8010
```

在第二个窗口启动前端，打开 [http://127.0.0.1:8501](http://127.0.0.1:8501)。

```powershell
$env:RAG_BACKEND_URL = 'http://127.0.0.1:8010'
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

| 操作 | 录屏检查 |
| --- | --- |
| 问「设备如何借用？」 | 中栏先出现「先在系统登记设备」，约一秒后追加下一段。第三段后，本轮工具显示 `search_knowledge_base`，右栏显示「演示手册.txt · 第 1 页」。 |
| 紧接着发送「文档列表」 | 沿用同一会话。左侧工具切换成 `list_documents`，右栏显示「本轮无引用」。 |
| 发送「演示断流」或「演示错误」 | 中栏保留已收到的片段并显示失败状态，工具和引用区标记本轮未确认。重跑不会重发该请求。 |
| 选一个非空、无敏感内容的 TXT，再点「上传文件」 | 左侧列表刷新并显示上传信息及文档 ID。提示向量索引需单独执行。在替身演示中，这一步只验证界面交互。 |
| 点「新建对话」 | 当前页面清除本地历史、旧来源、工具和会话 ID。 |

如已有完成配置的本机 FastAPI，可把前端的 `RAG_BACKEND_URL` 指向该服务。真实上传的 `ready` 表示解析入库。需要验证该文档参与检索时，在具备配置的本机测试环境单独运行已有命令：

```powershell
.\.venv\Scripts\python.exe -m backend.app.commands.index_document --document-id <UUID>
```

真实后端上的聊天会使用已配置的模型，请在确认使用范围后运行。页面会话保存在当前 Streamlit 会话中，整页刷新后可重新开始。发生断流时，已提交的后端状态可能已变化。

## 回归测试

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe -m pytest frontend/tests -v
```

前端测试覆盖 SSE 分包、中文、来源与完成确认、状态码、断流、采用同一会话 ID、上传后刷新失败和页面重跑。录屏验收需直接观察实际浏览器中的分段渲染。

## 2026-11-19 验收与恢复记录

- Windows Codex 配置已切换为 `windows.sandbox = "elevated"`，工作区 PowerShell 命令已恢复。
- 当前项目虚拟环境为 Python 3.11.15、Streamlit 1.52.2、HTTPX 0.28.1。PyPI 索引探测仍超时。本次从 `files.pythonhosted.org` 下载官方 wheel，核对哈希后离线安装，`pip check` 通过。代理配置所需的 `socksio` 1.0.0 已安装。
- 安装后的离线回归共 754 passed / 14 skipped，其中后端 736 passed，前端 HTTP 与 SSE 18 passed。替身服务回环实测在 0.02、1.14、2.27 秒收到三段正文，3.38 秒确认完成。上传、会话复用、同轮来源与工具、提前 EOF 和错误事件均通过。
- Streamlit 进程启动和健康检查已通过。当前会话的 AppTest 命令被自动审查阻止，原因是潜在遥测请求的发送内容无法核实。沙箱内 Chrome 的 GPU 进程退出，浏览器界面的逐段渲染与录屏仍需验收。
- 真实后端的 8000、PostgreSQL 的 5432、Qdrant 的 6333 本轮均未连通。Docker 引擎命名管道此前返回访问拒绝。无鉴权的 DeepSeek `/models` 连通性探测超时，付费模型调用 0 次。

恢复真实链路时，先根据 [Docker 恢复记录](docker-desktop-recovery.md) 核对原有 PostgreSQL、Qdrant 容器，再验证 FastAPI 的 `/health`、`/documents` 和 DeepSeek 连通性。依赖就绪后，使用一条针对已索引公开文档的合成问题验证 `POST /chat` 的 `X-Agent-Tool`、流式正文、`sources` 与 `[DONE]`。浏览器演示可以独立使用上面的无付费替身流程。

## 2026-11-20 上传格式与会话验收

前端文件选择器、multipart 请求和替身后端均使用真实后端的扩展名契约。接受 .pdf、.md、.txt，后缀匹配忽略大小写。前端按后缀发送 application/pdf、text/markdown 或 text/plain，避免浏览器 MIME 缺失导致 415。真实后端继续兼容 .md 的 text/x-markdown 与 text/plain。替身使用相同元数据校验和默认 20 MiB 上限，文件内容只用于合成流程，不进行生产解析或索引。

安装后的离线回归为 765 passed / 14 skipped。实际 Streamlit WebSocket 会话中分别上传合成 TXT、MD、PDF，各获一次 201，列表刷新后仍可见。两段输出相隔约 1.09 秒，成功后工具和引用出现。目录轮空引用、两类失败保留部分正文与避免重发、新建会话均已验证。

替身后端和 Streamlit 的健康检查均返回 200。Firefox 在 Windows 沙箱内无法创建标签页子进程，返回 GeckoChildProcessHost SpawnTarget 错误（-2147024809）。浏览器中的视觉渲染和原生文件选择仍待验证。替身验收的付费模型调用为 0。

## 2026-11-20 浏览器现场核对

用户提供的本机浏览器照片确认了成功轮的正文、左侧本轮工具 `search_knowledge_base`、上传成功提示以及刷新后的 Markdown 文档列表。两张照片未覆盖右侧引用窗格，也不能确定正文在浏览器中出现的时间顺序。左侧选择器曾显示 Streamlit 默认的 200 MB，而演示后端限制为 20 MiB。

仓库的 `.streamlit/config.toml` 使用 `server.maxUploadSize = 20`，从仓库根目录启动新的 Streamlit 进程后，选择器与演示后端使用同一默认上限。已有会话可先保留验收现场。若真实后端配置不同的上传上限，前端启动时可用 `--server.maxUploadSize` 指定对应值。

独立启动的 Streamlit 会话已确认文件选择器下发 20 MiB，并成功重新完成三种文件的上传、列表刷新和完整会话流程。本次完整回归在运行中被自动审查拦截，原因是 Visual Studio 外部遥测的载荷未获授权。保留此前已完成的 765 passed / 14 skipped 记录。

## 2026-11-20 浏览器验收结论

**本机无付费演示页面验收通过。** 两张现场照片确认了问答正文、本轮工具和 Markdown 上传后的目录刷新。用户随后在对话中确认浏览器中的正文逐段出现，右侧同轮引用符合预期。逐段显示与右侧引用的视觉结论依据用户确认，照片用于核对其余可见项。

替身 WebSocket 验证仍覆盖三种格式、会话复用、目录轮空引用、断流和错误处理、新建对话。

## 2026-11-20 AppTest 与真实联调预检

- `frontend/tests/test_app.py` 使用 `FakeRagClient`，通过项目虚拟环境执行等效于 `pytest -q -p no:cacheprovider frontend/tests/test_app.py` 的 `pytest.main` 调用。测试进程关闭 pytest 插件自动加载和 Streamlit 使用统计，在导入前添加 Python 审计钩子，限制网络与子进程创建。复跑为 **3 passed in 0.59s**，退出码 0，无网络访问被拦截。拦截到的 3 次子进程尝试来自 `streamlit.env_util` 导入时 `platform._syscmd_ver` 查询 Windows 版本。
- `127.0.0.1:5432`、`:6333`、`:8000` 均未监听，演示服务 `:8010` 和 `:8501` 仍在监听。`dockerDesktopLinuxEngine` 与 `docker_engine` 命名管道返回 `permission denied`，执行进程的 Windows 管理员角色检查为 `False`。
- 无鉴权的 `GET https://api.deepseek.com/models` 在 9 秒时超时。鉴权、真实检索与生成、SSE 同轮来源和工具、目标 PostgreSQL trace 均待在线验证。预检未发送真实模型请求，付费调用 0 次。

## 2026-11-20 容器启动后真实联调

- 用户在本机执行 `docker start rag-agent-postgres-1 rag-agent-qdrant` 后，PostgreSQL `SELECT 1` 通过，Qdrant `/readyz` 返回 200，已配置集合为绿色且有 25 个点。FastAPI 通过 `TestClient` 验证 `/health`、`/documents` 均返回 200，目录含 6 份已索引公开 PDF。真实 `POST /retrieval/rerank/search` 返回 200，首个结果为 `earthquake.pdf` 第 2 页。
- 通过仓库的 `backend.app.models.init_db` 新建缺失的 `conversations`、`messages` 和 `request_logs`，确认五张项目表均存在。
- DeepSeek 无鉴权 `GET /models` 返回 401，后续带鉴权请求返回 200。项目配置为 `deepseek-v4-flash`，此次模型列表提供 `deepseek-flash` 和 `deepseek-v4-pro`。针对公开地震资料的一轮测试只在测试进程中临时使用 `LLM_MODEL=deepseek-flash`，不更改项目配置。
- 自动审核以未获授权且载荷无法核实的 Visual Studio 遥测为由拦截 Uvicorn 启动。改用受限的进程内 FastAPI 测试后，真实检索成功，`POST /chat` 走到 DeepSeek 工具选择时再被自动审核终止。仅观察到一次工具选择请求开始，没有供应商响应，是否计费待确认。真实生成、SSE 终态及同轮持久化未验收。按测试问题只读查询 `request_logs`，匹配记录为 0。

## 2026-11-20 真实 HTTP SSE 和 trace 验收通过

用户明确授权此次联调涉及的 Visual Studio 遥测后，使用进程环境变量 `LLM_MODEL=deepseek-flash` 启动真实后端。

```powershell
$env:LLM_MODEL = 'deepseek-flash'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

- 通过本机 HTTP 验证 `/health` 与 `/documents` 均为 200，目录返回 6 份公开文档。向真实 `/chat` 发送一次公开地震资料问题。SSE 返回 200、有效 `X-Session-ID`、`X-Agent-Tool: search_knowledge_base`、34 段正文、5 条引用和 `[DONE]`。引用包含 `earthquake.pdf` 第 1 和第 2 页，答案命中预期词。HTTP 正文的首个及最后数据块分别于请求后 27.656 与 27.969 秒收到。
- 按同一 `X-Session-ID` 读取 PostgreSQL，`messages` 中为 `user` 与 `assistant` 两条记录，`request_logs` 显示 `success`、`sse`、HTTP 200、`business_committed=true`，来源与 SSE 一致。trace 记录 `tool_selection`、`generation` 两阶段，合计输入 2,244、输出 87 token，供应商用量完整。此前被拦截的工具选择是否计费仍待确认。
- 执行 `pytest -q -p no:cacheprovider frontend/tests/test_sse.py frontend/tests/test_api_client.py`，22 passed，0.26 秒。真实链路验收使用 HTTP 客户端，浏览器验收仍来自原有无付费替身。此次使用数据库只读查询验收 trace 落库，管理员读取接口未纳入测试。
