from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.content_series import ContentSeries
from app.models.post import Post
from app.schemas.post import PostResponse
from app.schemas.series import SeriesCreate, SeriesResponse, SeriesWithPostsResponse
from app.services.scheduling import find_platform_conflict

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=list[SeriesResponse])
async def list_series(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(
        select(ContentSeries)
        .where(ContentSeries.owner_id == user_id)
        .order_by(ContentSeries.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    data: SeriesCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    series = ContentSeries(owner_id=user_id, **data.model_dump())
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


@router.get("/{series_id}", response_model=SeriesWithPostsResponse)
async def get_series(
    series_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(
        select(ContentSeries).where(ContentSeries.id == series_id, ContentSeries.owner_id == user_id)
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

    posts_result = await db.execute(
        select(Post)
        .where(Post.owner_id == user_id, Post.series_id == series_id)
        .order_by(Post.series_index.asc(), Post.scheduled_at.asc())
    )
    posts = list(posts_result.scalars().all())

    return SeriesWithPostsResponse(
        **SeriesResponse.model_validate(series).model_dump(),
        posts=posts,
    )


@router.post("/{series_id}/generate", response_model=list[PostResponse], status_code=status.HTTP_201_CREATED)
async def generate_series_posts(
    series_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(
        select(ContentSeries).where(ContentSeries.id == series_id, ContentSeries.owner_id == user_id)
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")

    existing = await db.execute(select(Post.id).where(Post.series_id == series_id, Post.owner_id == user_id))
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Series already has generated posts",
        )

    cadence_delta = timedelta(days=1) if series.cadence == "daily" else timedelta(weeks=1)
    generated_posts: list[Post] = []

    for index in range(1, series.total_posts + 1):
        scheduled_at = series.start_at + cadence_delta * (index - 1)
        conflict = await find_platform_conflict(
            db=db,
            owner_id=user_id,
            platform=series.platform,
            scheduled_at=scheduled_at,
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Platform scheduling conflict at step {index}: "
                    f"'{conflict.title}' is already scheduled within 15 minutes."
                ),
            )

        generated_posts.append(
            Post(
                owner_id=user_id,
                title=f"{series.name} #{index}",
                platform=series.platform,
                scheduled_at=scheduled_at,
                status="scheduled",
                series_id=series.id,
                series_index=index,
            )
        )

    db.add_all(generated_posts)
    await db.commit()
    for post in generated_posts:
        await db.refresh(post)
    return generated_posts
