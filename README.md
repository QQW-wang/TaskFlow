# TaskFlow · 个人任务管理 API

一个面向 FastAPI 初学者的前后端分离练手项目。后端完整覆盖异步数据库、JWT 认证、依赖注入、参数校验、分页筛选、Alembic 迁移和自动化测试；前端使用原生 HTML/CSS/JavaScript，启动即可使用。

> 建议先阅读 [项目构建文档](docs/项目构建文档.md)，其中按“从零到一”的顺序解释了每个文件为什么这样写。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0（异步） |
| 数据库 | PostgreSQL + asyncpg |
| 迁移 | Alembic |
| 认证 | JWT（PyJWT）+ Argon2 |
| 校验 | Pydantic v2 + pydantic-settings |
| 测试 | pytest + pytest-asyncio + httpx + aiosqlite |
| 前端 | 原生 HTML / CSS / JavaScript |

## 功能

- 用户注册、JSON 登录、Swagger 表单登录
- 访问令牌鉴权，每个用户的数据完全隔离
- 任务创建、列表、详情、更新、删除
- 按状态筛选、关键词搜索、分页、排序
- 任务统计与完成率
- 健康检查、CORS、统一错误响应
- 9 个后端自动化测试，不依赖本地 PostgreSQL

## 快速开始

### 1. 准备 PostgreSQL

推荐使用 Docker：

```powershell
docker compose up -d db
```

如果本机已经安装 PostgreSQL，也可以手动创建数据库和用户：

```sql
CREATE USER taskflow WITH PASSWORD 'taskflow';
CREATE DATABASE taskflow OWNER taskflow;
```

> 本机 5432 端口被占用时，使用 `POSTGRES_PORT=5433 docker compose up -d db`，并同步修改 `.env` 中的端口。

### 2. 创建虚拟环境并安装依赖

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

如果 PowerShell 禁止执行脚本，可先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

> 如果 `python -m venv .venv` 报 `ensurepip` 失败，通常是 Microsoft Store 版 Python 的 `venv` 组件不完整；请安装 python.org 的官方 Python 3.12/3.13，并勾选“Add python.exe to PATH”。

### 3. 配置环境变量

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

把生成的随机字符串填入 `.env` 的 `JWT_SECRET_KEY`。

### 4. 执行数据库迁移

```powershell
alembic upgrade head
```

### 5. 启动后端

```powershell
uvicorn app.main:app --reload
```

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

### 6. 启动前端

另开一个终端，在项目根目录执行：

```powershell
python -m http.server 5500 --directory frontend
```

打开 <http://127.0.0.1:5500>，注册账号后即可使用。

## 运行测试

```powershell
pytest -q
```

测试使用内存 SQLite 和依赖覆盖，不会读写你的 PostgreSQL 数据库。

## 目录结构

```text
taskflow/
├── app/
│   ├── api/
│   │   ├── deps.py              # 当前用户、数据库会话等依赖
│   │   └── v1/                  # auth / users / tasks 路由
│   ├── core/
│   │   ├── config.py            # 环境变量配置
│   │   └── security.py          # 密码哈希、JWT
│   ├── db/                      # 声明式基类、异步引擎与 Session
│   ├── models/                  # SQLAlchemy ORM 模型
│   ├── schemas/                 # Pydantic 请求 / 响应模型
│   └── main.py                  # FastAPI 应用入口
├── alembic/                     # 数据库迁移
├── frontend/                    # 原生前端
├── tests/                       # 异步接口测试
├── docs/项目构建文档.md
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 常用接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | JSON 登录 |
| POST | `/api/v1/auth/token` | OAuth2 表单登录（Swagger） |
| GET | `/api/v1/users/me` | 当前用户 |
| GET | `/api/v1/tasks` | 任务列表（status / keyword / page / page_size） |
| POST | `/api/v1/tasks` | 创建任务 |
| GET | `/api/v1/tasks/{id}` | 任务详情 |
| PATCH | `/api/v1/tasks/{id}` | 更新任务 |
| DELETE | `/api/v1/tasks/{id}` | 删除任务 |
| GET | `/api/v1/tasks/stats` | 任务统计 |

## 学习建议

1. 先跑通项目，再用 Swagger 手动调用每一个接口。
2. 阅读 `docs/项目构建文档.md`，按章节自己重写关键代码。
3. 从“练习清单”里挑一个功能独立完成，例如标签、软删除或刷新令牌。
4. 修改代码后先运行 `pytest -q`，再刷新 Swagger 验证接口。

## 注意

- `.env` 不要提交到 Git；`JWT_SECRET_KEY` 必须替换成随机值。
- 本项目用于学习，默认允许本地前端跨域。生产部署还需要 HTTPS、反向代理、更严格的 CORS、限流和日志审计。