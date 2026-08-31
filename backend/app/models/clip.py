"""Clip model — represents a generated short clip/reel derived from a Video."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.video import Video


class AspectRatio(str, enum.Enum):
    """Target output aspect ratio for a clip."""

    vertical = "9:16"
    square = "1:1"
    horizontal = "16:9"


class ClipStatus(str, enum.Enum):
    """Lifecycle status of a clip's generation pipeline."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Clip(Base, TimestampMixin):
    """A short, logically-segmented clip generated from a source Video."""

    __tablename__ = "clips"
    __table_args__ = (Index("ix_clips_video_id_start_time", "video_id", "start_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    aspect_ratio: Mapped[AspectRatio] = mapped_column(
        Enum(AspectRatio, name="aspect_ratio_enum"), nullable=False
    )
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, name="clip_status_enum"),
        nullable=False,
        default=ClipStatus.pending,
        server_default=ClipStatus.pending.value,
        index=True,
    )

    # Relationships
    video: Mapped[Video] = relationship("Video", back_populates="clips")

    def __repr__(self) -> str:
        return f"<Clip id={self.id} video_id={self.video_id} status={self.status}>"
