"""Pydantic schemas for Clip resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.clip import AspectRatio, ClipStatus


class ClipResponse(BaseModel):
    """Serialized representation of a `Clip` row, returned by clip endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    start_time: float
    end_time: float
    title: str
    thumbnail_url: str | None
    file_path: str
    aspect_ratio: AspectRatio
    status: ClipStatus
    created_at: datetime
    updated_at: datetime


class ClipBoundariesUpdate(BaseModel):
    """Request body for `PUT /clips/{id}/boundaries` — adjusts a clip's time range."""

    start_time: float = Field(..., ge=0, description="New clip start time, in seconds.")
    end_time: float = Field(..., gt=0, description="New clip end time, in seconds.")


class ClipUpdate(BaseModel):
    """Request body for `PUT /clips/{id}` — partial update of editable clip metadata."""

    title: str | None = None
    thumbnail_url: str | None = None
