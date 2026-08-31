"""SQLAlchemy models package.

Import all models here so that:
  - `Base.metadata` is fully populated for Alembic autogenerate.
  - String-based relationship references (e.g. "Video", "Clip") resolve correctly.
"""

from app.models.base import Base, TimestampMixin
from app.models.clip import AspectRatio, Clip, ClipStatus
from app.models.video import SourceType, Video, VideoStatus

__all__ = [
    "AspectRatio",
    "Base",
    "Clip",
    "ClipStatus",
    "SourceType",
    "TimestampMixin",
    "Video",
    "VideoStatus",
]
