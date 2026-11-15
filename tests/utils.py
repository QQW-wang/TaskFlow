"""测试辅助函数。"""

from httpx import AsyncClient

DEFAULT_PASSWORD = "password123"


async def register_and_login(
    client: AsyncClient,
    *,
    email: str = "demo@example.com",
    username: str = "demo",
    password: str = DEFAULT_PASSWORD,
) -> dict[str, str]:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_task(
    client: AsyncClient,
    headers: dict[str, str],
    **overrides: object,
) -> dict:
    payload = {
        "title": "学习 FastAPI",
        "description": "完成依赖注入和异步数据库练习",
        "status": "todo",
        "priority": "medium",
        **overrides,
    }
    response = await client.post("/api/v1/tasks", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()