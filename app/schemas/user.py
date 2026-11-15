"""用户相关的请求 / 响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = r"^[A-Za-z0-9_\u4e00-\u9fa5]+$"


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=2,
        max_length=50,
        pattern=USERNAME_PATTERN,
        examples=["xiaoming"],
    )
    password: str = Field(min_length=8, max_length=128, examples=["password123"])

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime