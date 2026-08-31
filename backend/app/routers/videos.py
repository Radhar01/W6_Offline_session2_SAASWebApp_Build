"""Video upload/import API routes.

Handles ingesting source videos (via direct upload or a remote URL) and basic
CRUD over the resulting `Video` records. Clip generation is a separate module.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.exceptions import NotFoundError
from app.models.video import SourceType, Video, VideoStatus
from app.schemas.video import VideoResponse, VideoUrlIngestRequest
from app.services import storage_service, upload_service, url_ingest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> Video:
    """Stream an uploaded video file to storage and record it as a `Video`."""
    result = await upload_service.save_video_upload(file)

    video = Video(
        source_type=SourceType.upload,
        original_filename=result.original_filename,
        file_path=result.file_path,
        duration=result.duration,
        size_bytes=result.size_bytes,
        # "pending" = ingestion done, awaiting clip generation. The frontend's
        # processing page auto-triggers generation only when it sees this
        # status — see `Video.status`'s docstring for the full lifecycle.
        status=VideoStatus.pending,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info("Video %s created from upload (%.2fs)", video.id, video.duration)
    return video


@router.post("/from-url", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def ingest_video_from_url(
    payload: VideoUrlIngestRequest, db: Session = Depends(get_db)
) -> Video:
    """Download a video from a remote URL to storage and record it as a `Video`."""
    result = await url_ingest_service.download_video_from_url(payload.source_url)

    video = Video(
        source_type=SourceType.url,
        original_filename=result.original_filename,
        source_url=payload.source_url,
        file_path=result.file_path,
        duration=result.duration,
        size_bytes=result.size_bytes,
        # See the comment in `upload_video` above: "pending" awaits generation.
        status=VideoStatus.pending,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info("Video %s created from URL (%.2fs)", video.id, video.duration)
    return video


@router.get("/", response_model=list[VideoResponse])
async def list_videos(
    skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> list[Video]:
    """List videos, newest first, with simple skip/limit pagination."""
    return (
        db.query(Video)
        .order_by(Video.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    """Get a single video by id, or raise `NotFoundError` if it doesn't exist."""
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("Video", video_id)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_video(video_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a video: its clips' files, its own file, then the DB rows.

    The DB-level `ondelete=CASCADE` on `Clip.video_id` removes clip rows
    automatically, but the clip *files* on disk must be removed explicitly
    before that happens, since we still need `video.clips` populated.
    """
    video = db.get(Video, video_id)
    if video is None:
        raise NotFoundError("Video", video_id)

    for clip in video.clips:
        storage_service.delete_file(clip.file_path)

    storage_service.delete_file(video.file_path)
    storage_service.delete_directory(f"broll/{video.id}")

    db.delete(video)
    db.commit()
