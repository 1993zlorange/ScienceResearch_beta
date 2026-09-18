# ScienceResearch Workbench Beta

可直接下载部署的本地科研工作台源码。目标运行时使用 FastAPI、PostgreSQL 16、Alembic、Vue 3 和 Nginx。仓库内置一份全新空白 SQLite 兼容库；默认容器部署会创建空 PostgreSQL 卷并由 Alembic 初始化 46 张业务表。仓库不包含业务数据、测试、CI、内部治理文件、缓存、依赖目录或真实秘密。

## 1. Docker Compose 部署（推荐）

### Windows PowerShell

```powershell
$env:POSTGRES_PASSWORD = "至少8位本机密码"
$env:SCIENCERESEARCH_WEB_PORT = "8765"
docker compose up --build -d
```

### macOS / Linux

```bash
export POSTGRES_PASSWORD='至少8位本机密码'
export SCIENCERESEARCH_WEB_PORT='8765'
docker compose up --build -d
```

打开：

- 应用：<http://127.0.0.1:8765/>
- 课题工作台：<http://127.0.0.1:8765/contexts>
- 技术说明：<http://127.0.0.1:8765/technical-docs>
- API 文档：<http://127.0.0.1:8765/docs>

健康检查：

```bash
curl -f http://127.0.0.1:8765/healthz
curl -f http://127.0.0.1:8765/readyz
```

`/healthz` 表示 API 进程可用；`/readyz` 返回 200 表示 PostgreSQL 与 Alembic 就绪。停止使用 `docker compose down`；确认清空本机试用数据时才使用 `docker compose down -v`。

## 2. Windows 本机隔离部署

需预装 PostgreSQL 16 客户端/服务工具、Nginx、uv、Node.js 24 和 npm；脚本不下载工具。Windows 建议将仓库放在较短可写路径，避免传统 MAX_PATH 限制。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated
```

自定义端口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated -WebPort 8767 -ApiPort 8879 -PostgresPort 55434
```

如需局域网访问，可显式指定本机 IPv4；脚本会保留 127.0.0.1 回环入口，PostgreSQL 和 FastAPI 仍仅绑定回环：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated -WebBindAddress 192.168.173.2
```

查看、停止和强制重建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command status -Mode local-isolated
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command down -Mode local-isolated
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated -ForceRestart
```

详细参数见 [目标栈一键部署运行脚本 API 说明](docs/operations/20260915-目标栈一键部署运行脚本-API说明.md)。

## 3. 数据边界

- `storage/runtime/scienceresearch.db` 是全新空白 SQLite，仅用于旧路径兼容层；46 张表、业务行 0。
- 默认 Docker 部署创建空 PostgreSQL 隔离卷，由 Alembic 初始化结构，不导入业务数据。
- 不要把正式科研数据库挂载或复制进仓库；正式数据迁移需单独授权和验证。
- 局域网部署只暴露 Nginx Web 入口；数据库和 API 进程仍保持本机回环。

## 4. 主要能力

- 深色主页同构结构树与导航。
- 课题工作台：工作包视图、12 工作流视图、状态色、筛选、结构树同步定位、详情/目录/筛选/摘要收起、一键全部展开/收起。
- 成效卡新增、重要标记、附件上传/下载/安全预览。
- 技术说明离线手册与 API 文档。
