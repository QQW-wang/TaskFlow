"""任务 CRUD、筛选、分页与统计。"""

import math

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskList,
    TaskRead,
    TaskStats,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["任务"])


async def _get_owned_task(
    task_id: int,
    owner_id: int,
    db: AsyncSession,
) -> Task:
    """只允许操作自己的任务；不存在与无权限都返回 404。"""
    task = await db.get(Task, task_id)
    if task is None or task.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在",
        )
    return task


@router.get("", response_model=TaskList, summary="任务列表（筛选 + 分页）")
async def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> TaskList:
    filters = [Task.owner_id == current_user.id]

    if task_status is not None:
        filters.append(Task.status == task_status.value)

    if keyword:
        keyword = keyword.strip()
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(
                or_(
                    Task.title.ilike(pattern),
                    Task.description.ilike(pattern),
                )
            )

    total = int(
        await db.scalar(select(func.count(Task.id)).where(*filters)) or 0
    )
    pages = math.ceil(total / page_size) if total else 0

    statement = (
        select(Task)
        .where(*filters)
        .order_by(Task.created_at.desc(), Task.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.scalars(statement)).all())

    return TaskList(
        items=[TaskRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/stats", response_model=TaskStats, summary="任务统计")
async def task_stats(db: DbSession, current_user: CurrentUser) -> TaskStats:
    rows = (
        await db.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.owner_id == current_user.id)
            .group_by(Task.status)
        )
    ).all()

    counts = {item.value: 0 for item in TaskStatus}
    for status_value, count in rows:
        counts[status_value] = int(count)

    total = sum(counts.values())
    done = counts[TaskStatus.DONE.value]
    return TaskStats(
        total=total,
        todo=counts[TaskStatus.TODO.value],
        in_progress=counts[TaskStatus.IN_PROGRESS.value],
        done=done,
        completion_rate=round(done / total * 100, 1) if total else 0.0,
    )


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
)
async def create_task(
    payload: TaskCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    data = payload.model_dump()
    data["status"] = payload.status.value
    data["priority"] = payload.priority.value

    task = Task(owner_id=current_user.id, **data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead, summary="任务详情")
async def get_task(
    task_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    return await _get_owned_task(task_id, current_user.id, db)


@router.patch("/{task_id}", response_model=TaskRead, summary="更新任务")
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    task = await _get_owned_task(task_id, current_user.id, db)
    data = payload.model_dump(exclude_unset=True)

    # title / status / priority 在数据库里非空，显式传 null 时给出清晰错误。
    for field_name in ("title", "status", "priority"):
        if field_name in data and data[field_name] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} 不能为 null",
            )

    if "status" in data:
        data["status"] = payload.status.value  # type: ignore[union-attr]
    if "priority" in data:
        data["priority"] = payload.priority.value  # type: ignore[union-attr]

    for field_name, value in data.items():
        setattr(task, field_name, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除任务",
)
async def delete_task(
    task_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Response:
    task = await _get_owned_task(task_id, current_user.id, db)
    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)