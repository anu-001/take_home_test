from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post


CONFLICT_WINDOW_MINUTES = 15


async def find_platform_conflict(
    db: AsyncSession,
    owner_id: int,
    platform: str,
    scheduled_at: Optional[datetime],
    exclude_post_id: Optional[int] = None,
) -> Optional[Post]:
    if scheduled_at is None:
        return None

    lower_bound = scheduled_at - timedelta(minutes=CONFLICT_WINDOW_MINUTES)
    upper_bound = scheduled_at + timedelta(minutes=CONFLICT_WINDOW_MINUTES)

    query = select(Post).where(
        Post.owner_id == owner_id,
        Post.platform == platform,
        Post.scheduled_at.is_not(None),
        Post.scheduled_at >= lower_bound,
        Post.scheduled_at <= upper_bound,
    )
    if exclude_post_id is not None:
        query = query.where(Post.id != exclude_post_id)

    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()
