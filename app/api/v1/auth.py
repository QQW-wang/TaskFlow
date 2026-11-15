"""注册、登录、获取令牌。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["认证"])


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """校验邮箱和密码，失败时统一返回 401，避免泄露账号是否存在。"""
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被停用",
        )
    return user


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
)
async def register(payload: UserCreate, db: DbSession) -> User:
    email = payload.email.lower()

    existing = (
        await db.scalars(
            select(User).where(
                or_(User.email == email, User.username == payload.username)
            )
        )
    ).first()
    if existing is not None:
        if existing.email.lower() == email:
            detail = "该邮箱已被注册"
        else:
            detail = "该用户名已被占用"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    user = User(
        email=email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # 并发注册时，上面的查询可能同时通过，数据库唯一约束是最后防线。
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱或用户名已被注册",
        ) from None

    await db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="JSON 登录（前端使用）")
async def login(payload: UserLogin, db: DbSession) -> Token:
    user = await authenticate_user(db, payload.email, payload.password)
    return Token(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


@router.post(
    "/token",
    response_model=Token,
    summary="表单登录（Swagger Authorize 使用）",
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    # OAuth2 表单规范要求字段名是 username，这里让用户填邮箱即可。
    user = await authenticate_user(db, form_data.username, form_data.password)
    return Token(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )