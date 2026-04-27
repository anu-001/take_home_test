import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_series(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/series",
        headers=auth_headers,
        json={
            "name": "Launch Week",
            "platform": "linkedin",
            "start_at": "2026-06-01T10:00:00Z",
            "cadence": "daily",
            "total_posts": 4,
            "status": "draft",
        },
    )
    assert create.status_code == 201

    listing = await client.get("/api/series", headers=auth_headers)
    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 1
    assert data[0]["name"] == "Launch Week"


@pytest.mark.asyncio
async def test_generate_series_posts(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/series",
        headers=auth_headers,
        json={
            "name": "Product Drop",
            "platform": "instagram",
            "start_at": "2026-06-01T10:00:00Z",
            "cadence": "weekly",
            "total_posts": 3,
            "status": "draft",
        },
    )
    series_id = create.json()["id"]

    generate = await client.post(f"/api/series/{series_id}/generate", headers=auth_headers)
    assert generate.status_code == 201
    posts = generate.json()
    assert len(posts) == 3
    assert posts[0]["title"] == "Product Drop #1"
    assert posts[1]["series_index"] == 2

    detail = await client.get(f"/api/series/{series_id}", headers=auth_headers)
    assert detail.status_code == 200
    detail_data = detail.json()
    assert len(detail_data["posts"]) == 3
    assert detail_data["posts"][0]["series_index"] == 1


@pytest.mark.asyncio
async def test_generate_series_conflict(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "title": "Existing",
            "platform": "linkedin",
            "status": "scheduled",
            "scheduled_at": "2026-06-01T10:00:00Z",
        },
    )
    create = await client.post(
        "/api/series",
        headers=auth_headers,
        json={
            "name": "Conflict Series",
            "platform": "linkedin",
            "start_at": "2026-06-01T10:05:00Z",
            "cadence": "daily",
            "total_posts": 2,
            "status": "draft",
        },
    )
    series_id = create.json()["id"]

    generate = await client.post(f"/api/series/{series_id}/generate", headers=auth_headers)
    assert generate.status_code == 409
    assert "within 15 minutes" in generate.json()["detail"]


@pytest.mark.asyncio
async def test_generate_series_only_once(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/series",
        headers=auth_headers,
        json={
            "name": "Single Generate",
            "platform": "youtube",
            "start_at": "2026-06-01T10:00:00Z",
            "cadence": "daily",
            "total_posts": 2,
            "status": "draft",
        },
    )
    series_id = create.json()["id"]

    first = await client.post(f"/api/series/{series_id}/generate", headers=auth_headers)
    assert first.status_code == 201

    second = await client.post(f"/api/series/{series_id}/generate", headers=auth_headers)
    assert second.status_code == 400
    assert "already has generated posts" in second.json()["detail"]
