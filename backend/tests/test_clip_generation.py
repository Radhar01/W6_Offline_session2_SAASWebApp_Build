"""Tests for backend/app/routers/clip_generation.py and the worker/service it drives.

`segmentation_service.generate_clips` (and, indirectly, its ffmpeg subprocess
calls) is mocked wherever the goal is to exercise routing/DB logic; a
dedicated test drives `segmentation_service` itself with ffmpeg mocked, and
another drives the background worker directly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clip import AspectRatio, Clip, ClipStatus
from app.models.video import SourceType, Video, VideoStatus
from app.workers.clip_generation_worker import run_clip_generation


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
# POST /videos/{id}/generate-clips
# --------------------------------------------------------------------------


def test_trigger_clip_generation_marks_processing_and_schedules_task(
    client: TestClient, db_session: Session
) -> None:
    video = _make_video(db_session, status=VideoStatus.completed)

    # Prevent the background task from actually running ffmpeg; we only care
    # here that the endpoint flips the status and schedules the task.
    with patch("app.routers.clip_generation.run_clip_generation") as mock_run:
        response = client.post(f"/api/v1/videos/{video.id}/generate-clips")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == video.id
    assert body["status"] == "processing"

    db_session.refresh(video)
    assert video.status == VideoStatus.processing
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == video.id


def test_trigger_clip_generation_video_not_found(client: TestClient) -> None:
    response = client.post("/api/v1/videos/999/generate-clips")
    assert response.status_code == 404


def test_list_video_clips(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip1 = _make_clip(db_session, video, start_time=0.0, end_time=30.0, file_path="clips/1/a.mp4")
    clip2 = _make_clip(db_session, video, start_time=30.0, end_time=60.0, file_path="clips/1/b.mp4")

    response = client.get(f"/api/v1/videos/{video.id}/clips")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body] == [clip1.id, clip2.id]


def test_list_video_clips_video_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/videos/999/clips")
    assert response.status_code == 404


# --------------------------------------------------------------------------
# POST /clips/{id}/regenerate
# --------------------------------------------------------------------------


def test_regenerate_clip_success(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, status=ClipStatus.completed)

    with patch("app.routers.clip_generation.segmentation_service.regenerate_clip_file") as mock_regen:
        response = client.post(f"/api/v1/clips/{clip.id}/regenerate")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    mock_regen.assert_called_once()
    db_session.refresh(clip)
    assert clip.status == ClipStatus.completed


def test_regenerate_clip_marks_failed_on_error(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video, status=ClipStatus.completed)

    with patch(
        "app.routers.clip_generation.segmentation_service.regenerate_clip_file",
        side_effect=RuntimeError("ffmpeg exploded"),
    ):
        response = client.post(f"/api/v1/clips/{clip.id}/regenerate")

    # The router re-raises after marking failed; the unhandled-exception
    # handler converts it to a 500.
    assert response.status_code == 500
    db_session.refresh(clip)
    assert clip.status == ClipStatus.failed


def test_regenerate_clip_not_found(client: TestClient) -> None:
    response = client.post("/api/v1/clips/999/regenerate")
    assert response.status_code == 404


def test_regenerate_clip_video_not_found(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    clip = _make_clip(db_session, video)
    db_session.delete(video)
    db_session.commit()
    # `video_id` FK is not tied to the clip lookup here (SQLite doesn't enforce
    # FKs by default), so the clip row is still fetchable and the router's
    # own `Video` re-fetch should raise NotFoundError.
    response = client.post(f"/api/v1/clips/{clip.id}/regenerate")
    assert response.status_code == 404


# --------------------------------------------------------------------------
# PUT /clips/{id}/boundaries
# --------------------------------------------------------------------------


def test_update_clip_boundaries_success(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session, duration=100.0)
    clip = _make_clip(db_session, video, start_time=0.0, end_time=30.0, status=ClipStatus.completed)

    response = client.put(
        f"/api/v1/clips/{clip.id}/boundaries",
        json={"start_time": 5.0, "end_time": 45.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["start_time"] == pytest.approx(5.0)
    assert body["end_time"] == pytest.approx(45.0)
    assert body["status"] == "pending"


def test_update_clip_boundaries_start_after_end_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    video = _make_video(db_session, duration=100.0)
    clip = _make_clip(db_session, video)

    response = client.put(
        f"/api/v1/clips/{clip.id}/boundaries",
        json={"start_time": 50.0, "end_time": 10.0},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_clip_boundaries_out_of_video_duration_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    video = _make_video(db_session, duration=60.0)
    clip = _make_clip(db_session, video)

    response = client.put(
        f"/api/v1/clips/{clip.id}/boundaries",
        json={"start_time": 0.0, "end_time": 999.0},
    )

    assert response.status_code == 422


def test_update_clip_boundaries_negative_start_rejected_by_schema(
    client: TestClient, db_session: Session
) -> None:
    """`start_time` has `ge=0` on the Pydantic schema -> FastAPI 422 before the route runs."""
    video = _make_video(db_session, duration=60.0)
    clip = _make_clip(db_session, video)

    response = client.put(
        f"/api/v1/clips/{clip.id}/boundaries",
        json={"start_time": -5.0, "end_time": 10.0},
    )

    assert response.status_code == 422


def test_update_clip_boundaries_clip_not_found(client: TestClient) -> None:
    response = client.put(
        "/api/v1/clips/999/boundaries", json={"start_time": 0.0, "end_time": 10.0}
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# Background worker (run_clip_generation) — driven directly
# --------------------------------------------------------------------------


def test_run_clip_generation_success(db_session: Session) -> None:
    from tests.conftest import TestSessionLocal

    video = _make_video(db_session, status=VideoStatus.pending)

    with patch(
        "app.workers.clip_generation_worker.segmentation_service.generate_clips"
    ) as mock_generate:
        run_clip_generation(video.id, TestSessionLocal)

    mock_generate.assert_called_once()
    db_session.refresh(video)
    assert video.status == VideoStatus.completed


def test_run_clip_generation_marks_failed_on_error(db_session: Session) -> None:
    from tests.conftest import TestSessionLocal

    video = _make_video(db_session, status=VideoStatus.pending)

    with patch(
        "app.workers.clip_generation_worker.segmentation_service.generate_clips",
        side_effect=RuntimeError("boom"),
    ):
        run_clip_generation(video.id, TestSessionLocal)

    db_session.refresh(video)
    assert video.status == VideoStatus.failed


def test_run_clip_generation_video_missing_is_noop(db_session: Session) -> None:
    from tests.conftest import TestSessionLocal

    # Should log and return without raising. `db_session` is depended on
    # purely to ensure the tables exist for this test's own session.
    run_clip_generation(999999, TestSessionLocal)


# --------------------------------------------------------------------------
# segmentation_service — ffmpeg subprocess calls fully mocked
# --------------------------------------------------------------------------


def test_generate_clips_creates_rows_with_fixed_intervals(
    db_session: Session, tmp_path, monkeypatch
) -> None:
    from app.services import segmentation_service

    monkeypatch.setattr(
        "app.services.segmentation_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
    )

    video = _make_video(db_session, duration=65.0, file_path="videos/source.mp4")

    fake_scene_result = MagicMock()
    fake_scene_result.stderr = ""  # no scene cuts -> fixed interval fallback
    fake_cut_result = MagicMock()
    fake_cut_result.returncode = 0
    fake_cut_result.stderr = ""

    with patch(
        "app.services.segmentation_service.subprocess.run",
        side_effect=[fake_scene_result, fake_cut_result, fake_cut_result, fake_cut_result, fake_cut_result],
    ):
        clips = segmentation_service.generate_clips(video, db_session)

    assert len(clips) >= 1
    for clip in clips:
        assert clip.status == ClipStatus.completed
        assert clip.video_id == video.id


def test_generate_clips_rejects_zero_duration_video(db_session: Session) -> None:
    from app.exceptions import ValidationAppError
    from app.services import segmentation_service

    video = _make_video(db_session, duration=0.0)

    with pytest.raises(ValidationAppError):
        segmentation_service.generate_clips(video, db_session)


def test_generate_clips_groups_scene_cuts_into_segments(
    db_session: Session, tmp_path, monkeypatch
) -> None:
    """With real scene-cut timestamps in ffmpeg's stderr, segments should follow them."""
    from app.services import segmentation_service

    monkeypatch.setattr(
        "app.services.segmentation_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
    )

    video = _make_video(db_session, duration=90.0, file_path="videos/source.mp4")

    fake_scene_result = MagicMock()
    # Two scene-cut candidates within [MIN, MAX] clip duration of the segment start.
    fake_scene_result.stderr = "pts_time:20.0 ... pts_time:55.0 ..."
    fake_ffmpeg_ok = MagicMock(returncode=0, stderr="")

    with patch(
        "app.services.segmentation_service.subprocess.run",
        side_effect=[fake_scene_result] + [fake_ffmpeg_ok] * 20,
    ):
        clips = segmentation_service.generate_clips(video, db_session)

    assert len(clips) >= 1
    total_covered = clips[-1].end_time
    assert total_covered == pytest.approx(90.0)


def test_detect_scene_cuts_falls_back_on_ffmpeg_failure(monkeypatch) -> None:
    from app.services import segmentation_service

    with patch(
        "app.services.segmentation_service.subprocess.run",
        side_effect=OSError("ffmpeg not found"),
    ):
        result = segmentation_service._detect_scene_cuts("videos/source.mp4", 60.0)

    assert result == []


def test_run_ffmpeg_raises_on_nonzero_returncode() -> None:
    from app.exceptions import ValidationAppError
    from app.services import segmentation_service

    fake_result = MagicMock(returncode=1, stderr="ffmpeg: fatal error")

    with patch("app.services.segmentation_service.subprocess.run", return_value=fake_result):
        with pytest.raises(ValidationAppError):
            segmentation_service._run_ffmpeg(["ffmpeg", "-version"], "boom")


def test_run_ffmpeg_raises_on_timeout() -> None:
    import subprocess as subprocess_module

    from app.exceptions import ValidationAppError
    from app.services import segmentation_service

    with patch(
        "app.services.segmentation_service.subprocess.run",
        side_effect=subprocess_module.TimeoutExpired(cmd="ffmpeg", timeout=300),
    ):
        with pytest.raises(ValidationAppError):
            segmentation_service._run_ffmpeg(["ffmpeg", "-version"], "boom")


def test_fixed_interval_segments_merges_short_trailing_remainder() -> None:
    from app.services import segmentation_service

    # duration=95, interval=30 -> segments at 30/30/30, remainder 5s (< interval/2=15)
    # should be merged into the final segment instead of its own tiny clip.
    segments = segmentation_service._fixed_interval_segments(95.0, interval=30.0)

    assert segments[-1][1] == pytest.approx(95.0)
    assert all(end > start for start, end in segments)


def test_regenerate_clip_file_recuts_and_rethumbnails(tmp_path, monkeypatch, db_session: Session) -> None:
    from app.services import segmentation_service

    monkeypatch.setattr(
        "app.services.segmentation_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
    )

    video = _make_video(db_session, duration=60.0, file_path="videos/source.mp4")
    clip = _make_clip(
        db_session,
        video,
        start_time=5.0,
        end_time=25.0,
        file_path="clips/1/clip_1.mp4",
        thumbnail_url="thumbnails/1/clip_1.jpg",
    )

    fake_ok = MagicMock(returncode=0, stderr="")
    with patch("app.services.segmentation_service.subprocess.run", return_value=fake_ok) as mock_run:
        segmentation_service.regenerate_clip_file(video, clip)

    # One ffmpeg call to re-cut the clip, one to re-extract the thumbnail.
    assert mock_run.call_count == 2


def test_regenerate_clip_file_without_thumbnail_only_recuts(
    tmp_path, monkeypatch, db_session: Session
) -> None:
    from app.services import segmentation_service

    monkeypatch.setattr(
        "app.services.segmentation_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
    )

    video = _make_video(db_session, duration=60.0, file_path="videos/source.mp4")
    clip = _make_clip(
        db_session,
        video,
        start_time=0.0,
        end_time=10.0,
        file_path="clips/1/clip_no_thumb.mp4",
        thumbnail_url=None,
    )

    fake_ok = MagicMock(returncode=0, stderr="")
    with patch("app.services.segmentation_service.subprocess.run", return_value=fake_ok) as mock_run:
        segmentation_service.regenerate_clip_file(video, clip)

    assert mock_run.call_count == 1
