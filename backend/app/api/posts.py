from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.content_series import ContentSeries
from app.models.post import Post
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.services.scheduling import find_platform_conflict

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=list[PostResponse])
async def list_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
):
    q = select(Post).where(Post.owner_id == user_id).order_by(Post.scheduled_at.desc().nulls_last(), Post.created_at.desc())
    if status:
        q = q.where(Post.status == status)
    if platform:
        q = q.where(Post.platform == platform)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    if data.series_id is not None:
        series_result = await db.execute(
            select(ContentSeries).where(ContentSeries.id == data.series_id, ContentSeries.owner_id == user_id)
        )
        series = series_result.scalar_one_or_none()
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
        if data.platform != series.platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post platform must match the series platform",
            )

    conflict = await find_platform_conflict(
        db=db,
        owner_id=user_id,
        platform=data.platform,
        scheduled_at=data.scheduled_at,
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Platform scheduling conflict: '{conflict.title}' is already scheduled within 15 minutes.",
        )

    post = Post(
        title=data.title,
        platform=data.platform,
        scheduled_at=data.scheduled_at,
        status=data.status,
        owner_id=user_id,
        series_id=data.series_id,
        series_index=data.series_index,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.owner_id == user_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.owner_id == user_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    update_data = data.model_dump(exclude_unset=True)
    next_platform = update_data.get("platform", post.platform)
    next_scheduled_at = update_data.get("scheduled_at", post.scheduled_at)
    next_series_id = update_data.get("series_id", post.series_id)

    if next_series_id is not None:
        series_result = await db.execute(
            select(ContentSeries).where(ContentSeries.id == next_series_id, ContentSeries.owner_id == user_id)
        )
        series = series_result.scalar_one_or_none()
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
        if next_platform != series.platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post platform must match the series platform",
            )

    conflict = await find_platform_conflict(
        db=db,
        owner_id=user_id,
        platform=next_platform,
        scheduled_at=next_scheduled_at,
        exclude_post_id=post.id,
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Platform scheduling conflict: '{conflict.title}' is already scheduled within 15 minutes.",
        )

    for k, v in update_data.items():
        setattr(post, k, v)
    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.owner_id == user_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    await db.delete(post)
    await db.commit()
