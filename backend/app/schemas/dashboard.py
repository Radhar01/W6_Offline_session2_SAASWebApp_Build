"""Pydantic schemas for the Dashboard module.

Used by backend/app/routers/dashboard.py to expose aggregate stats and a
recent-activity feed combining videos and clips.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Aggregate counts and storage usage across the whole library."""

    total_videos: int
    total_clips: int
    storage_used_bytes: int


class ActivityItem(BaseModel):
    """A single row in the recent-activity feed (either a video or a clip)."""

    id: int
    type: Literal["video", "clip"]
    title: str
    status: str
    created_at: datetime


class ActivityResponse(BaseModel):
    """A collection of recent activity items, most-recent first."""

    items: list[ActivityItem]
