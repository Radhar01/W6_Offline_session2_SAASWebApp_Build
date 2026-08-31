"""Clip Library endpoints: list, retrieve, update metadata, download, delete.

Clip *generation* (creating clips from a source video) is owned by the
separate Clip Generation module (`app.routers.clip_generation`). This module
only manages clips that already exist in the database.
"""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.exceptions import NotFoundError, ValidationAppError
from app.models.clip import Clip, ClipStatus
from app.schemas.clip import ClipResponse, ClipUpdate
from app.services import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clips"])

_SORT_OPTIONS = {
    "created_at_desc": (Clip.created_at, desc),
    "created_at_asc": (Clip.created_at, asc),
    "start_time_asc": (Clip.start_time, asc),
    "start_time_desc": (Clip.start_time, desc),
}


def _get_clip_or_404(db: Session, clip_id: int) -> Clip:
    """Fetch a clip by id or raise `NotFoundError`."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip", clip_id)
    return clip


def _safe_filename(title: str, source_path: str) -> str:
    """Derive a safe download filename from the clip title, keeping the original extension."""
    extension = Path(source_path).suffix or ".mp4"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_") or "clip"
    return f"{slug}{extension}"


@router.get("/clips", response_model=list[ClipResponse])
async def list_clips(
    video_id: int | None = Query(default=None, description="Filter clips by source video id"),
    status: str | None = Query(default=None, description="Filter clips by status"),
    sort: str = Query(default="created_at_desc", description="Sort order for results"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Clip]:
    """List clips, optionally filtered by video id and/or status, and sorted.

    Paginated via `skip`/`limit` (matching the `/videos` endpoint's convention)
    so the result set stays bounded as the clip library grows.
    """
    query = db.query(Clip)

    if video_id is not None:
        query = query.filter(Clip.video_id == video_id)

    if status is not None:
        try:
            status_value = ClipStatus(status)
        except ValueError as exc:
            valid = ", ".join(s.value for s in ClipStatus)
            raise ValidationAppError(
                f"Invalid status '{status}'. Valid values: {valid}"
            ) from exc
        query = query.filter(Clip.status == status_value)

    if sort not in _SORT_OPTIONS:
        valid_sorts = ", ".join(_SORT_OPTIONS)
        raise ValidationAppError(f"Invalid sort '{sort}'. Valid values: {valid_sorts}")
    column, direction = _SORT_OPTIONS[sort]
    query = query.order_by(direction(column))

    return query.offset(skip).limit(limit).all()


@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: int, db: Session = Depends(get_db)) -> Clip:
    """Retrieve a single clip by id."""
    return _get_clip_or_404(db, clip_id)


@router.put("/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: int, payload: ClipUpdate, db: Session = Depends(get_db)
) -> Clip:
    """Update editable metadata (title and/or thumbnail_url) on a clip."""
    clip = _get_clip_or_404(db, clip_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clip, field, value)

    db.commit()
    db.refresh(clip)
    logger.info("Updated clip %s: fields=%s", clip_id, list(update_data))
    return clip


@router.get("/clips/{clip_id}/download")
async def download_clip(
    clip_id: int,
    inline: bool = Query(default=False, description="Serve inline instead of as an attachment"),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream the clip's video file from disk.

    Defaults to an attachment download; pass `?inline=true` to serve it for
    inline `<video>` playback instead (used by the clip preview player).
    """
    clip = _get_clip_or_404(db, clip_id)

    absolute_path = storage_service.get_absolute_path(clip.file_path)
    if not absolute_path.exists():
        logger.error("Clip %s file missing on disk: %s", clip_id, absolute_path)
        raise NotFoundError("Clip file", clip_id)

    filename = _safe_filename(clip.title, clip.file_path)
    return FileResponse(
        path=absolute_path,
        media_type="video/mp4",
        filename=filename,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.delete("/clips/{clip_id}", status_code=204)
async def delete_clip(clip_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a clip's file from storage and remove its database record."""
    clip = _get_clip_or_404(db, clip_id)

    storage_service.delete_file(clip.file_path)
    db.delete(clip)
    db.commit()
    logger.info("Deleted clip %s", clip_id)
