"""Clip generation endpoints: trigger AI segmentation, list clips, regenerate, adjust boundaries.

Paths are designed as if mounted under `/api/v1` (the orchestrator decides
the actual mount point / router registration in `app.main`).
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.dependencies import get_db
from app.exceptions import NotFoundError, ValidationAppError
from app.models.clip import Clip, ClipStatus
from app.models.video import Video, VideoStatus
from app.schemas.clip import ClipBoundariesUpdate, ClipResponse
from app.services import segmentation_service
from app.workers.clip_generation_worker import run_clip_generation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clip-generation"])


class VideoStatusResponse(BaseModel):
    """Minimal Video representation returned by the generate-clips endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: VideoStatus


@router.post("/videos/{video_id}/generate-clips", response_model=VideoStatusResponse)
async def trigger_clip_generation(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Video:
    """Kick off AI-driven clip segmentation for a video as a background task.

    Marks the video "processing" and returns immediately; the actual clip
    generation runs asynchronously via `run_clip_generation`. A no-op if the
    video is already `processing` (avoids a second concurrent job racing on
    the same deterministic clip file paths).

    Note: `Video.status == "completed"` is shared between "ingestion
    finished" and "clip generation finished" — this endpoint is legitimately
    called on a `completed` video (that's the normal post-upload flow), so
    that status can't also be used to guard against a *second* generation
    call creating duplicate `Clip` rows. That narrower case is accepted as a
    known limitation for this MVP.
    """
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("Video", video_id)

    if video.status == VideoStatus.processing:
        return video

    video.status = VideoStatus.processing
    db.commit()
    db.refresh(video)

    background_tasks.add_task(run_clip_generation, video_id, SessionLocal)
    return video


@router.get("/videos/{video_id}/clips", response_model=list[ClipResponse])
async def list_video_clips(video_id: int, db: Session = Depends(get_db)) -> list[Clip]:
    """List all clips generated for a given video, ordered by start time."""
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("Video", video_id)

    return db.query(Clip).filter(Clip.video_id == video_id).order_by(Clip.start_time).all()


@router.post("/clips/{clip_id}/regenerate", response_model=ClipResponse)
async def regenerate_clip(clip_id: int, db: Session = Depends(get_db)) -> Clip:
    """Regenerate a clip's rendered file (and thumbnail) from its current boundaries.

    Deletes the existing clip file and re-cuts it from the source video
    using the clip's existing `start_time`/`end_time`.
    """
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip", clip_id)

    video = db.get(Video, clip.video_id)
    if video is None:
        raise NotFoundError("Video", clip.video_id)

    clip.status = ClipStatus.processing
    db.commit()

    try:
        await asyncio.to_thread(segmentation_service.regenerate_clip_file, video, clip)
    except Exception:
        clip.status = ClipStatus.failed
        db.commit()
        raise

    clip.status = ClipStatus.completed
    db.commit()
    db.refresh(clip)
    return clip


@router.put("/clips/{clip_id}/boundaries", response_model=ClipResponse)
async def update_clip_boundaries(
    clip_id: int,
    payload: ClipBoundariesUpdate,
    db: Session = Depends(get_db),
) -> Clip:
    """Adjust a clip's start/end time.

    Validates the new boundaries against the source video's duration, then
    persists them and marks the clip "pending" to signal it needs its file
    regenerated (see `POST /clips/{id}/regenerate`).
    """
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip", clip_id)

    video = db.get(Video, clip.video_id)
    if video is None:
        raise NotFoundError("Video", clip.video_id)

    if payload.start_time >= payload.end_time:
        raise ValidationAppError("start_time must be less than end_time.")
    if payload.start_time < 0 or payload.end_time > video.duration:
        raise ValidationAppError("Clip boundaries must fall within the source video's duration.")

    clip.start_time = payload.start_time
    clip.end_time = payload.end_time
    clip.status = ClipStatus.pending
    db.commit()
    db.refresh(clip)
    return clip
