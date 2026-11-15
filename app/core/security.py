"""密码哈希与 JWT 工具。

密码只保存 Argon2 哈希；JWT 中只放用户 id，不放密码等敏感信息。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

# pwdlib 会根据当前环境选择推荐的密码哈希算法（默认 Argon2id）。
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        # 数据库中的哈希格式异常时按验证失败处理，避免 500。
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """创建访问令牌。subject 通常放用户 id。"""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解析并校验令牌；无效或过期时返回 None。"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError:
        return None

    if payload.get("type") != "access":
        return None
    return payload