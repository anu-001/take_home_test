from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.post import PostResponse


class SeriesBase(BaseModel):
    name: str
    platform: str
    start_at: datetime
    cadence: str = Field(pattern="^(daily|weekly)$")
    total_posts: int = Field(ge=1)
    status: str = "draft"


class SeriesCreate(SeriesBase):
    pass


class SeriesResponse(SeriesBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SeriesWithPostsResponse(SeriesResponse):
    posts: list[PostResponse]
