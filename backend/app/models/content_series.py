from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ContentSeries(Base):
    __tablename__ = "content_series"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    platform = Column(String(64), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    cadence = Column(String(32), nullable=False)  # daily | weekly
    total_posts = Column(Integer, nullable=False)
    status = Column(String(32), default="draft", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="series")
    posts = relationship("Post", back_populates="series")
