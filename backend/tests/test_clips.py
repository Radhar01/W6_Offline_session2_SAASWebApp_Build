"""Tests for backend/app/routers/clips.py (the Clip Library CRUD/download endpoints)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
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
        size_bytes=2048,
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
# GET /clips  (list + filters + sort)
# --------------------------------------------------------------------------


def test_list_clips_no_filters_returns_all(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    _make_clip(db_session, video, title="A")
    _make_clip(db_session, video, title="B")

    response = client.get("/api/v1/clips")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_clips_filter_by_video_id(client: TestClient, db_session: Session) -> None:
    video1 = _make_video(db_session, file_path="videos/v1.mp4")
    video2 = _make_video(db_session, file_path="videos/v2.mp4")
    clip1 = _make_clip(db_session, video1, file_path="clips/1/a.mp4")
    _make_clip(db_session, video2, file_path="clips/2/b.mp4")

    response = client.get("/api/v1/clips", params={"video_id": video1.id})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == clip1.id


def test_list_clips_filter_by_status(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    completed = _make_clip(db_session, video, status=ClipStatus.completed, file_path="clips/1/a.mp4")
    _make_clip(db_session, video, status=ClipStatus.failed, file_path="clips/1/b.mp4")

    response = client.get("/api/v1/clips", params={"status": "completed"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == completed.id


def test_list_clips_invalid_status_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/clips", params={"status": "not-a-real-status"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_clips_invalid_sort_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/clips", params={"sort": "not-a-real-sort"})
    assert response.status_code == 422


def test_list_clips_sort_by_start_time(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    later = _make_clip(db_session, video, start_time=50.0, end_time=60.0, file_path="clips/1/late.mp4")
    earlier = _make_clip(db_session, video, start_time=0.0, end_time=10.0, file_path="clips/1/early.mp4")

    response = client.get("/api/v1/clips", params={"sort": "start_time_asc"})

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body] == [earlier.id, later.id]

    response_desc = client.get("/api/v1/clips", params={"sort": "start_time_desc"})
    body_desc = response_desc.json()
    assert [c["id"] for c in body_desc] == [later.id, earlier.id]


# --------------------------------------------------------------------------
# GET /clips/{id}
# --------------------------------------------------------------------------


def test_get_clip_success(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video)

    response = client.get(f"/api/v1/clips/{clip.id}")

    assert response.status_code == 200
    assert response.json()["id"] == clip.id


def test_get_clip_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/clips/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------
# PUT /clips/{id}  (partial update)
# --------------------------------------------------------------------------


def test_update_clip_title_only(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, title="Old title", thumbnail_url="thumbs/old.jpg")

    response = client.put(f"/api/v1/clips/{clip.id}", json={"title": "New title"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New title"
    assert body["thumbnail_url"] == "thumbs/old.jpg"  # untouched


def test_update_clip_thumbnail_only(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, title="Keep me", thumbnail_url="thumbs/old.jpg")

    response = client.put(
        f"/api/v1/clips/{clip.id}", json={"thumbnail_url": "thumbs/new.jpg"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Keep me"
    assert body["thumbnail_url"] == "thumbs/new.jpg"


def test_update_clip_both_fields(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, title="Old", thumbnail_url="thumbs/old.jpg")

    response = client.put(
        f"/api/v1/clips/{clip.id}",
        json={"title": "Brand new", "thumbnail_url": "thumbs/brand-new.jpg"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Brand new"
    assert body["thumbnail_url"] == "thumbs/brand-new.jpg"


def test_update_clip_empty_body_changes_nothing(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, title="Unchanged", thumbnail_url="thumbs/unchanged.jpg")

    response = client.put(f"/api/v1/clips/{clip.id}", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Unchanged"
    assert body["thumbnail_url"] == "thumbs/unchanged.jpg"


def test_update_clip_not_found(client: TestClient) -> None:
    response = client.put("/api/v1/clips/999", json={"title": "Nope"})
    assert response.status_code == 404


# --------------------------------------------------------------------------
# GET /clips/{id}/download
# --------------------------------------------------------------------------


def test_download_clip_success(client: TestClient, db_session: Session, tmp_path) -> None:
    video = _make_video(db_session)
    clip_file = tmp_path / "clip.mp4"
    clip_file.write_bytes(b"fake mp4 bytes")
    clip = _make_clip(db_session, video, title="My Great Clip!", file_path="clips/1/clip.mp4")

    with patch(
        "app.routers.clips.storage_service.get_absolute_path", return_value=clip_file
    ):
        response = client.get(f"/api/v1/clips/{clip.id}/download")

    assert response.status_code == 200
    assert response.content == b"fake mp4 bytes"
    content_disposition = response.headers["content-disposition"]
    assert "attachment" in content_disposition
    assert "My_Great_Clip.mp4" in content_disposition


def test_download_clip_missing_file_on_disk(
    client: TestClient, db_session: Session, tmp_path
) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, file_path="clips/1/missing.mp4")
    missing_path = tmp_path / "does-not-exist.mp4"

    with patch(
        "app.routers.clips.storage_service.get_absolute_path", return_value=missing_path
    ):
        response = client.get(f"/api/v1/clips/{clip.id}/download")

    assert response.status_code == 404


def test_download_clip_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/clips/999/download")
    assert response.status_code == 404


# --------------------------------------------------------------------------
# DELETE /clips/{id}
# --------------------------------------------------------------------------


def test_delete_clip_success(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, file_path="clips/1/to-delete.mp4")

    with patch("app.routers.clips.storage_service.delete_file") as mock_delete:
        response = client.delete(f"/api/v1/clips/{clip.id}")

    assert response.status_code == 204
    mock_delete.assert_called_once_with("clips/1/to-delete.mp4")
    assert db_session.get(Clip, clip.id) is None


def test_delete_clip_not_found(client: TestClient) -> None:
    response = client.delete("/api/v1/clips/999")
    assert response.status_code == 404
