"""Pydantic schemas for the video upload/import API."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.video import SourceType, VideoStatus


class VideoResponse(BaseModel):
    """Serialized representation of a `Video` row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: SourceType
    original_filename: str | None
    source_url: str | None
    file_path: str
    duration: float
    size_bytes: int
    status: VideoStatus
    created_at: datetime
    updated_at: datetime


class VideoUrlIngestRequest(BaseModel):
    """Request body for ingesting a video from a remote URL."""

    source_url: str

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        """Ensure `source_url` is a well-formed http/https URL."""
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("source_url must be a valid http:// or https:// URL")
        return value
