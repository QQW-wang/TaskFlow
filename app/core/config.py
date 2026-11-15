"""应用配置：统一从环境变量 / .env 读取，避免把密钥写死在代码里。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 基础信息
    app_name: str = "TaskFlow API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL 异步连接串，驱动必须是 asyncpg
    database_url: str = "postgresql+asyncpg://taskflow:taskflow@127.0.0.1:5432/taskflow"
    sql_echo: bool = False

    # JWT 配置
    jwt_secret_key: str = "dev-only-change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # 前端地址（多个用英文逗号分隔）
    cors_origins: str = "http://127.0.0.1:5500,http://localhost:5500"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，整个进程只读取一次环境变量。"""
    return Settings()


settings = get_settings()