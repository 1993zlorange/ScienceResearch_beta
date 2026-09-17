# ScienceResearch Workbench Beta

本地优先科研工作台的可直接部署源码。目标运行时是 FastAPI + PostgreSQL 16 + Alembic + Vue 3 + Nginx。仓库包含一份全新空白 SQLite 兼容库；默认容器部署使用 PostgreSQL，Alembic 从空库创建全部 46 张业务表。仓库不含业务数据、测试、CI、内部治理文件、缓存、依赖目录或真实秘密。

## 1. Docker Compose 部署

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
- 工作包目录：<http://127.0.0.1:8765/work-packages>
- 课题工作台：<http://127.0.0.1:8765/contexts>
- 技术说明：<http://127.0.0.1:8765/technical-docs>
- API 文档：<http://127.0.0.1:8765/docs>

健康检查：

```bash
curl -f http://127.0.0.1:8765/healthz
curl -f http://127.0.0.1:8765/readyz
```

`/healthz` 表示 API 可用；`/readyz` 返回 200 表示 PostgreSQL 和 Alembic 就绪。停止使用 `docker compose down`；确认清空试用数据时使用 `docker compose down -v`。

## 2. Windows 本机隔离部署

本机需预装 PostgreSQL 16 客户端/服务工具、Nginx、uv、Node.js 24 和 npm；脚本不下载工具。在仓库根执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated
```

自定义端口示例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated -WebPort 8767 -ApiPort 8879 -PostgresPort 55434
```

查看和停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command status -Mode local-isolated
powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command down -Mode local-isolated
```

参数与退出码见 [目标栈一键部署运行脚本 API 说明](docs/operations/20260915-目标栈一键部署运行脚本-API说明.md)。部署拓扑概述见 [目标栈运行部署运维说明](docs/operations/20260914-目标栈运行部署-运维说明.md)。

## 3. 数据边界

- `storage/runtime/scienceresearch.db` 是全新空白 SQLite，仅用于旧路径兼容层；46 张表、业务行 0。
- 默认 Docker 部署创建空 PostgreSQL 隔离卷，由 Alembic 初始化结构，不导入业务数据。
- 不要把正式科研数据库挂载或复制进仓库；正式数据迁移需要单独授权和验证。
- Windows 建议把仓库 clone/unzip 到较短可写路径，避免 PostgreSQL 工具遇到传统 MAX_PATH 限制。
