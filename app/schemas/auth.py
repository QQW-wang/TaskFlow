"""认证接口的响应模型。"""

from pydantic import BaseModel

from app.schemas.user import UserRead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead