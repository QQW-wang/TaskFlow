"""任务 CRUD、筛选、分页、统计与数据隔离测试。"""

from httpx import AsyncClient

from tests.utils import create_task, register_and_login


async def test_task_crud_and_stats(client: AsyncClient) -> None:
    headers = await register_and_login(client)

    first = await create_task(
        client,
        headers,
        title="写项目文档",
        description="整理接口说明和运行步骤",
        priority="high",
    )
    assert first["status"] == "todo"
    assert first["owner_id"] == 1

    second = await create_task(
        client,
        headers,
        title="复习异步 SQLAlchemy",
        status="in_progress",
    )

    list_response = await client.get("/api/v1/tasks", headers=headers)
    assert list_response.status_code == 200, list_response.text
    body = list_response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 2

    todo_response = await client.get(
        "/api/v1/tasks",
        params={"status": "todo"},
        headers=headers,
    )
    assert todo_response.json()["total"] == 1
    assert todo_response.json()["items"][0]["title"] == "写项目文档"

    keyword_response = await client.get(
        "/api/v1/tasks",
        params={"keyword": "异步"},
        headers=headers,
    )
    assert keyword_response.json()["total"] == 1
    assert keyword_response.json()["items"][0]["id"] == second["id"]

    update_response = await client.patch(
        f"/api/v1/tasks/{first['id']}",
        json={"status": "done", "title": "  完成项目文档  "},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "done"
    assert update_response.json()["title"] == "完成项目文档"

    stats_response = await client.get("/api/v1/tasks/stats", headers=headers)
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats == {
        "total": 2,
        "todo": 0,
        "in_progress": 1,
        "done": 1,
        "completion_rate": 50.0,
    }

    delete_response = await client.delete(
        f"/api/v1/tasks/{first['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    missing_response = await client.get(
        f"/api/v1/tasks/{first['id']}",
        headers=headers,
    )
    assert missing_response.status_code == 404


async def test_tasks_are_isolated_between_users(client: AsyncClient) -> None:
    alice_headers = await register_and_login(
        client,
        email="alice@example.com",
        username="alice",
    )
    bob_headers = await register_and_login(
        client,
        email="bob@example.com",
        username="bob",
    )

    alice_task = await create_task(client, alice_headers, title="Alice 的私人任务")

    forbidden_response = await client.get(
        f"/api/v1/tasks/{alice_task['id']}",
        headers=bob_headers,
    )
    assert forbidden_response.status_code == 404

    bob_list = await client.get("/api/v1/tasks", headers=bob_headers)
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0

    bob_delete = await client.delete(
        f"/api/v1/tasks/{alice_task['id']}",
        headers=bob_headers,
    )
    assert bob_delete.status_code == 404


async def test_pagination(client: AsyncClient) -> None:
    headers = await register_and_login(client)
    for index in range(3):
        await create_task(client, headers, title=f"任务 {index}")

    response = await client.get(
        "/api/v1/tasks",
        params={"page": 2, "page_size": 2},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["page"] == 2
    assert len(body["items"]) == 1


async def test_invalid_task_payload(client: AsyncClient) -> None:
    headers = await register_and_login(client)

    empty_title = await client.post(
        "/api/v1/tasks",
        json={"title": "   "},
        headers=headers,
    )
    assert empty_title.status_code == 422

    bad_page = await client.get(
        "/api/v1/tasks",
        params={"page_size": 500},
        headers=headers,
    )
    assert bad_page.status_code == 422

    task = await create_task(client, headers)
    null_status = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"status": None},
        headers=headers,
    )
    assert null_status.status_code == 422