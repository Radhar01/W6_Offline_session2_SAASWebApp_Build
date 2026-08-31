"""Tests for backend/app/routers/dashboard.py."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clip import AspectRatio, Clip, ClipStatus
from app.models.video import SourceType, Video, VideoStatus


def _make_video(db_session: Session, **overrides) -> Video:
    defaults = dict(
        source_type=SourceType.upload,
        original_filename="source.mp4",
        file_path="videos/source.mp4",
        duration=120.0,
        size_bytes=1000,
        status=VideoStatus.completed,
    )
    defaults.update(overrides)
    video = Video(**defaults)
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


def _make_clip(db_session: Session, video: Video, **overrides) -> Clip:
    defaults = dict(
        video_id=video.id,
        start_time=0.0,
        end_time=30.0,
        title="Clip 1",
        thumbnail_url="thumbnails/1/clip_1.jpg",
        file_path="clips/1/clip_1.mp4",
        aspect_ratio=AspectRatio.vertical,
        status=ClipStatus.completed,
    )
    defaults.update(overrides)
    clip = Clip(**defaults)
    db_session.add(clip)
    db_session.commit()
    db_session.refresh(clip)
    return clip


# --------------------------------------------------------------------------
# GET /api/v1/dashboard/stats
# --------------------------------------------------------------------------


def test_dashboard_stats_with_zero_data(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    assert body == {"total_videos": 0, "total_clips": 0, "storage_used_bytes": 0}


def test_dashboard_stats_with_seeded_data(client: TestClient, db_session: Session) -> None:
    video1 = _make_video(db_session, file_path="videos/v1.mp4", size_bytes=1000)
    video2 = _make_video(db_session, file_path="videos/v2.mp4", size_bytes=2500)
    _make_clip(db_session, video1, file_path="clips/1/a.mp4")
    _make_clip(db_session, video1, file_path="clips/1/b.mp4")
    _make_clip(db_session, video2, file_path="clips/2/c.mp4")

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_videos"] == 2
    assert body["total_clips"] == 3
    assert body["storage_used_bytes"] == 3500


# --------------------------------------------------------------------------
# GET /api/v1/dashboard/activity
# --------------------------------------------------------------------------


def test_recent_activity_empty(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/activity")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_recent_activity_ordering_most_recent_first(
    client: TestClient, db_session: Session
) -> None:
    import datetime

    video = _make_video(db_session, file_path="videos/v1.mp4")

    older_clip = _make_clip(db_session, video, title="Older clip", file_path="clips/1/older.mp4")
    older_clip.created_at = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    db_session.add(older_clip)
    db_session.commit()

    newer_clip = _make_clip(db_session, video, title="Newer clip", file_path="clips/1/newer.mp4")
    newer_clip.created_at = datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)
    db_session.add(newer_clip)
    db_session.commit()

    video.created_at = datetime.datetime(2024, 3, 1, tzinfo=datetime.timezone.utc)
    db_session.add(video)
    db_session.commit()

    response = client.get("/api/v1/dashboard/activity")

    assert response.status_code == 200
    items = response.json()["items"]
    titles_in_order = [item["title"] for item in items]
    assert titles_in_order == ["Newer clip", "source.mp4", "Older clip"]


def test_recent_activity_respects_limit_param(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    for i in range(5):
        _make_clip(db_session, video, title=f"Clip {i}", file_path=f"clips/1/clip_{i}.mp4")

    response = client.get("/api/v1/dashboard/activity", params={"limit": 2})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2


def test_recent_activity_limit_out_of_range_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/activity", params={"limit": 0})
    assert response.status_code == 422

    response = client.get("/api/v1/dashboard/activity", params={"limit": 101})
    assert response.status_code == 422
