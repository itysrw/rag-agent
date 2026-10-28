# 本机 Docker Desktop 启动恢复记录

日期：2026-10-27（Asia/Shanghai）。以下为本机已执行操作，不是通用安装要求。

## 故障与已确认事实

原版本 Docker Desktop `4.49.0.208700` 在初始化 `dockerInference` 时无法删除 AF_UNIX
socket；只移动该运行目录后，会继续在 Secrets Engine 的 `engine.sock` 处失败。
关闭 `EnableDockerAI` 不能跳过监听器初始化。

经用户明确同意，使用官方安装包原位升级到 `4.97.0.244584`，安装日志确认成功，当前
Engine 为 `29.9.2`。升级后在默认运行时目录重启，Secrets Engine 仍无法把 engine.sock
重命名为 `.stale`。因此升级没有单独解决本机问题；同类跨版本报告可参见
[Docker 官方问题库 #554](https://github.com/docker/desktop-feedback/issues/554) 和
[for-win #15064](https://github.com/docker/for-win/issues/15064)。

Windows 报错 `ERROR_CANT_ACCESS_FILE`；Secrets Engine 目录具有 EFS Encrypted 属性，
但不能据此认定 EFS、中文用户名、磁盘损坏或某个内核缺陷就是根因。
普通及管理员重命名、仅对运行目录执行 cipher /d、WSL 目录访问均未成功。未尝试修改
整个用户目录的 ACL、加密策略或系统驱动。

## 可用的本机启动方式

启动脚本保存在仓库外：`D:\Docker\Start-DockerDesktop.ps1`。

```powershell
& 'D:\Docker\Start-DockerDesktop.ps1'
```

执行前应关闭 Docker Desktop 及其错误对话框。脚本不强杀进程；若仍有 Docker 进程，
会提示先关闭。脚本仅为新启动的 Docker 进程设置：

```text
LOCALAPPDATA=D:\Docker\codex-runtime-20261027
```

它会在该专用路径内，将仅含零字节运行端点的 `Docker\run` 和 `docker-secrets-engine`
目录重命名保留，再创建新目录；若发现非零文件、子目录或链接，停止处理。脚本不删除
旧运行目录，不更改系统/用户级环境变量，仍沿用原来的 Roaming 配置。

此启动方式已经完成：启动引擎 → 找到原有容器 → 正常停止 → 再次通过脚本启动 →
找回原有容器并启动 PostgreSQL/Qdrant。随后完成真实检索实验。
这是本机已验证的规避方案，不代表默认快捷方式或 Windows socket 根因已修复。
不要在 Docker 正常运行时反复点击默认快捷方式重新启动。

## 数据盘与备份

- 原有数据盘：`D:\Docker\DockerDesktopWSL\disk\docker_data.vhdx`。
- 恢复前完整备份：`D:\Docker\docker_data.codex-pre-recovery-20261027.vhdx`，
  `5,602,541,568` 字节，启动前 SHA-256 与源盘一致。
- 已将 Roaming 配置中的 `CustomWslDistroDir` 恢复到 `D:\Docker\DockerDesktopWSL`。
  升级后首次启动使用了 C 盘新建空数据盘；确认后恢复 D 盘路径，原有容器、镜像和卷
  随即重新可见。C 盘新空盘仍保留，未覆盖旧盘。
- 原始配置备份：`%APPDATA%\Docker\settings-store.codex-backup-20261027.json`。
- 升级后配置备份：`D:\Docker\settings-store.codex-post-upgrade-20261027.json`。
- 原 C 盘 socket 目录及本轮重命名成功的运行目录保留在相邻 `.codex-stale-*` 目录。
  部分失败移动创建了空目录；这些不应被误认为完整 socket 备份。

只启动了 `rag-agent-postgres-1` 与 `rag-agent-qdrant`；其他原有容器保持停止。
没有 factory reset、WSL unregister、volume prune 或数据库恢复/覆盖。
Docker 数据盘与停机备份原则可参考
[官方备份文档](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/)。

## 剩余事项

保留完整 VHDX 备份供回滚。默认 C 盘 socket 路径仍有访问故障；后续应单独诊断 Windows
文件访问/加密与 socket 生命周期，或向 Docker 提交经脱敏的故障信息。未上传任何诊断
归档或本地日志。官方版本说明见
[Docker Desktop release notes](https://docs.docker.com/desktop/release-notes/)。
