"""Video model — represents a source video ingested via upload or URL."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.clip import Clip


class SourceType(str, enum.Enum):
    """How a video entered the system."""

    upload = "upload"
    url = "url"


class VideoStatus(str, enum.Enum):
    """Lifecycle status of a video's CLIP GENERATION pipeline (not ingestion).

    A `Video` row is only ever created once its file is fully uploaded/
    downloaded and probed — ingestion itself has no separate row-level
    status. So this tracks what happens *after* that:
      pending    -> ingested, clip generation not yet started (the initial
                    value set by the videos.upload / videos.from-url
                    endpoints; the frontend's processing page auto-triggers
                    generation only when it sees this value)
      processing -> a generation job is currently running
      completed  -> generation finished successfully
      failed     -> generation raised an error
    """

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Video(Base, TimestampMixin):
    """A long-form source video that clips are generated from."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"), nullable=False
    )
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status_enum"),
        nullable=False,
        default=VideoStatus.pending,
        server_default=VideoStatus.pending.value,
        index=True,
    )

    # Relationships
    clips: Mapped[list[Clip]] = relationship(
        "Clip",
        back_populates="video",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} status={self.status} source_type={self.source_type}>"
