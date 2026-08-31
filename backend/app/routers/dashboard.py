"""Dashboard module — aggregate library stats and recent-activity feed.

Designed to be mounted under `/api/v1/dashboard` by the central router
wiring in app.main (owned by the orchestrator).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.clip import Clip
from app.models.video import Video
from app.schemas.dashboard import ActivityItem, ActivityResponse, DashboardStats

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStats:
    """Return aggregate counts and storage usage across the whole library.

    `storage_used_bytes` is approximated as the sum of `Video.size_bytes`
    across all videos. Clips are derived (trimmed/re-encoded) from videos
    that are already counted toward storage, so summing video sizes alone
    is treated as an acceptable MVP approximation rather than also summing
    per-clip file sizes on disk (which would require a filesystem stat call
    per clip, since Clip has no size_bytes column today).
    """
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    total_clips = db.query(func.count(Clip.id)).scalar() or 0
    storage_used_bytes = db.query(func.sum(Video.size_bytes)).scalar() or 0

    logger.info(
        "Computed dashboard stats: videos=%s clips=%s storage_bytes=%s",
        total_videos,
        total_clips,
        storage_used_bytes,
    )

    return DashboardStats(
        total_videos=total_videos,
        total_clips=total_clips,
        storage_used_bytes=int(storage_used_bytes),
    )


@router.get("/activity", response_model=ActivityResponse)
async def get_recent_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ActivityResponse:
    """Return the most recent videos and clips combined, newest first.

    Fetches up to `limit` of each resource type ordered by `created_at`
    descending, merges them, re-sorts the merged set by `created_at`
    descending, and truncates to `limit`. Fetching `limit` from each side
    (rather than just `limit` total from a single query) guarantees correct
    results even if one resource type dominates recent activity.
    """
    recent_videos = (
        db.query(Video).order_by(Video.created_at.desc()).limit(limit).all()
    )
    recent_clips = db.query(Clip).order_by(Clip.created_at.desc()).limit(limit).all()

    items: list[ActivityItem] = []

    for video in recent_videos:
        items.append(
            ActivityItem(
                id=video.id,
                type="video",
                title=video.original_filename or video.source_url or "Untitled video",
                status=video.status.value,
                created_at=video.created_at,
            )
        )

    for clip in recent_clips:
        items.append(
            ActivityItem(
                id=clip.id,
                type="clip",
                title=clip.title,
                status=clip.status.value,
                created_at=clip.created_at,
            )
        )

    items.sort(key=lambda item: item.created_at, reverse=True)
    items = items[:limit]

    logger.info("Returning %s recent activity items (limit=%s)", len(items), limit)

    return ActivityResponse(items=items)
