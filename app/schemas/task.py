"""任务相关的请求 / 响应模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["完成 FastAPI 练习"])
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    """PATCH 请求：只传需要修改的字段。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int
    pages: int


class TaskStats(BaseModel):
    total: int
    todo: int
    in_progress: int
    done: int
    completion_rate: float