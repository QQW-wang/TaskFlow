"""当前用户信息。"""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserRead, summary="获取当前登录用户")
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)