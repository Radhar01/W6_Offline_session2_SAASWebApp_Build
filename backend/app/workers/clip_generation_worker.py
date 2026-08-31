"""Background worker that runs the clip-generation pipeline for a video."""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.video import Video, VideoStatus
from app.services import segmentation_service

logger = logging.getLogger(__name__)


def run_clip_generation(video_id: int, db_session_factory: Callable[[], Session]) -> None:
    """Run AI-driven clip segmentation for `video_id` as a `BackgroundTasks` job.

    Opens its own DB session (background tasks run after the request's
    session has been closed), marks the video "processing", generates
    clips, then marks it "completed" or "failed". Never raises, so it is
    safe to schedule via `BackgroundTasks.add_task`.
    """
    db = db_session_factory()
    try:
        video = db.get(Video, video_id)
        if video is None:
            logger.error("run_clip_generation: video %s not found", video_id)
            return

        video.status = VideoStatus.processing
        db.commit()

        try:
            segmentation_service.generate_clips(video, db)
        except Exception:
            logger.exception("Clip generation failed for video %s", video_id)
            video.status = VideoStatus.failed
            db.commit()
            return

        video.status = VideoStatus.completed
        db.commit()
    finally:
        db.close()
