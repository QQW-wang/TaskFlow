"""认证相关测试。"""

from httpx import AsyncClient

from tests.utils import register_and_login


async def test_register_login_and_get_me(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "Alice@Example.com",
            "username": "alice",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201, register_response.text
    user = register_response.json()
    assert user["email"] == "alice@example.com"
    assert user["username"] == "alice"
    assert user["is_active"] is True
    assert "password" not in user
    assert "hashed_password" not in user

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200, login_response.text
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]
    assert token_data["user"]["username"] == "alice"

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"


async def test_duplicate_email_is_rejected(client: AsyncClient) -> None:
    await register_and_login(client, email="dup@example.com", username="first")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUP@example.com",
            "username": "second",
            "password": "password123",
        },
    )
    assert response.status_code == 409
    assert "邮箱" in response.json()["detail"]


async def test_wrong_password_is_rejected(client: AsyncClient) -> None:
    await register_and_login(client, email="wrong@example.com", username="wrong")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "邮箱或密码错误"


async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 401


async def test_short_password_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "username": "short", "password": "123"},
    )
    assert response.status_code == 422