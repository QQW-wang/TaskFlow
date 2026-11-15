"""TaskFlow API 入口。

启动命令（在项目根目录执行）：
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger("taskflow")

DESCRIPTION = """
TaskFlow 是一个用于学习 FastAPI 的个人任务管理 API。

* **认证**：先调用 `/api/v1/auth/register` 注册，再调用 `/api/v1/auth/login` 获取 JWT。
* **调试**：点击右上角 **Authorize**，填入邮箱和密码，即可在 Swagger 中调试受保护接口。
* **数据隔离**：每个用户只能看到、修改和删除自己的任务。
""".strip()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("%s 已启动，环境：%s", settings.app_name, settings.app_env)
    if settings.jwt_secret_key.startswith("dev-only"):
        logger.warning("当前使用默认 JWT_SECRET_KEY，仅适合本地学习，请勿用于生产。")
    yield
    await engine.dispose()
    logger.info("%s 已关闭", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "系统", "description": "健康检查与项目入口"},
        {"name": "认证", "description": "注册、登录、获取 JWT"},
        {"name": "用户", "description": "当前登录用户信息"},
        {"name": "任务", "description": "任务的增删改查、筛选、分页与统计"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["系统"], summary="项目入口")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check(db: DbSession) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("数据库健康检查失败")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库连接失败",
        ) from exc
    return {"status": "ok", "database": "up"}