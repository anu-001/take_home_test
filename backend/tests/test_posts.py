import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_posts_empty(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/posts", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "My first post",
            "platform": "youtube",
            "status": "draft",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "My first post"
    assert data["platform"] == "youtube"
    assert data["status"] == "draft"
    assert "id" in data
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_list_posts_returns_own(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "Post A", "platform": "instagram", "status": "draft"},
    )
    r = await client.get("/api/posts", headers=auth_headers)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["title"] == "Post A"


@pytest.mark.asyncio
async def test_get_post(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "Get me", "platform": "twitter", "status": "scheduled"},
    )
    post_id = create.json()["id"]
    r = await client.get(f"/api/posts/{post_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Get me"
    assert r.json()["platform"] == "twitter"


@pytest.mark.asyncio
async def test_update_post(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "Original", "platform": "youtube", "status": "draft"},
    )
    post_id = create.json()["id"]
    r = await client.patch(
        f"/api/posts/{post_id}",
        headers=auth_headers,
        json={"title": "Updated title", "status": "scheduled"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated title"
    assert r.json()["status"] == "scheduled"
    assert r.json()["platform"] == "youtube"


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "To delete", "platform": "tiktok", "status": "draft"},
    )
    post_id = create.json()["id"]
    r = await client.delete(f"/api/posts/{post_id}", headers=auth_headers)
    assert r.status_code == 204
    get_r = await client.get(f"/api/posts/{post_id}", headers=auth_headers)
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_posts_require_auth(client: AsyncClient):
    r = await client.get("/api/posts")
    assert r.status_code == 401

    r = await client.post(
        "/api/posts",
        json={"title": "No auth", "platform": "youtube", "status": "draft"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_post_404(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/posts/99999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_filter_posts_by_status(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "Draft", "platform": "youtube", "status": "draft"},
    )
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={"title": "Scheduled", "platform": "youtube", "status": "scheduled"},
    )
    r = await client.get("/api/posts?status=draft", headers=auth_headers)
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["status"] == "draft"


@pytest.mark.asyncio
async def test_create_post_rejects_platform_conflict(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Existing",
            "platform": "linkedin",
            "status": "scheduled",
            "scheduled_at": "2026-05-01T10:00:00Z",
        },
    )

    conflict = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Too close",
            "platform": "linkedin",
            "status": "scheduled",
            "scheduled_at": "2026-05-01T10:10:00Z",
        },
    )
    assert conflict.status_code == 409
    assert "within 15 minutes" in conflict.json()["detail"]


@pytest.mark.asyncio
async def test_update_post_rejects_platform_conflict(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Fixed slot",
            "platform": "instagram",
            "status": "scheduled",
            "scheduled_at": "2026-05-01T10:00:00Z",
        },
    )

    editable = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Move me",
            "platform": "instagram",
            "status": "scheduled",
            "scheduled_at": "2026-05-01T11:00:00Z",
        },
    )
    post_id = editable.json()["id"]

    conflict = await client.patch(
        f"/api/posts/{post_id}",
        headers=auth_headers,
        json={"scheduled_at": "2026-05-01T10:05:00Z"},
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_create_post_rejects_series_platform_mismatch(client: AsyncClient, auth_headers: dict):
    series = await client.post(
        "/api/series",
        headers=auth_headers,
        json={
            "name": "LinkedIn Series",
            "platform": "linkedin",
            "start_at": "2026-06-01T10:00:00Z",
            "cadence": "daily",
            "total_posts": 2,
            "status": "draft",
        },
    )
    series_id = series.json()["id"]

    create = await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Wrong platform",
            "platform": "instagram",
            "status": "draft",
            "series_id": series_id,
            "series_index": 1,
        },
    )
    assert create.status_code == 400
    assert "must match the series platform" in create.json()["detail"]