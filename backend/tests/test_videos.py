"""Tests for backend/app/routers/videos.py and the ingestion services it calls.

ffmpeg subprocess calls and real network (httpx) calls are mocked throughout
so the suite never needs a real ffmpeg binary or network access.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clip import AspectRatio, Clip, ClipStatus
from app.models.video import SourceType, Video, VideoStatus
from app.services import upload_service, url_ingest_service
from app.services.upload_service import VideoIngestResult

# --------------------------------------------------------------------------
# Router tests
# --------------------------------------------------------------------------


def _make_video(
    db_session: Session,
    *,
    source_type: SourceType = SourceType.upload,
    file_path: str = "videos/abc.mp4",
    duration: float = 120.0,
    size_bytes: int = 1024,
    status: VideoStatus = VideoStatus.completed,
    original_filename: str | None = "abc.mp4",
    source_url: str | None = None,
) -> Video:
    video = Video(
        source_type=source_type,
        original_filename=original_filename,
        source_url=source_url,
        file_path=file_path,
        duration=duration,
        size_bytes=size_bytes,
        status=status,
    )
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


def test_upload_video_success(client: TestClient) -> None:
    """A successful upload should create a Video row from the service result."""
    fake_result = VideoIngestResult(
        file_path="videos/deadbeef.mp4",
        size_bytes=12345,
        duration=42.5,
        original_filename="my_video.mp4",
    )

    with patch(
        "app.routers.videos.upload_service.save_video_upload",
        new=AsyncMock(return_value=fake_result),
    ):
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("my_video.mp4", io.BytesIO(b"fake bytes"), "video/mp4")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "my_video.mp4"
    assert body["file_path"] == "videos/deadbeef.mp4"
    assert body["duration"] == pytest.approx(42.5)
    assert body["size_bytes"] == 12345
    assert body["status"] == "pending"
    assert body["source_type"] == "upload"


def test_upload_video_rejects_invalid_file_type(client: TestClient) -> None:
    """An unsupported extension/content-type should be rejected before any I/O."""
    response = client.post(
        "/api/v1/videos/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported video format" in body["error"]["message"]


def test_ingest_video_from_url_success(client: TestClient) -> None:
    fake_result = VideoIngestResult(
        file_path="videos/from-url.mp4",
        size_bytes=999,
        duration=10.0,
        original_filename="from-url.mp4",
    )

    with patch(
        "app.routers.videos.url_ingest_service.download_video_from_url",
        new=AsyncMock(return_value=fake_result),
    ):
        response = client.post(
            "/api/v1/videos/from-url",
            json={"source_url": "https://example.com/videos/from-url.mp4"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "url"
    assert body["source_url"] == "https://example.com/videos/from-url.mp4"
    assert body["file_path"] == "videos/from-url.mp4"


def test_ingest_video_from_url_rejects_malformed_url(client: TestClient) -> None:
    """A non-http(s) URL is rejected by the pydantic schema validator (422)."""
    response = client.post("/api/v1/videos/from-url", json={"source_url": "not-a-url"})
    assert response.status_code == 422


def test_ingest_video_from_url_rejects_private_address(client: TestClient) -> None:
    """A URL pointing at a private/internal address is rejected by the service layer.

    This exercises the real `url_ingest_service._validate_source_url` logic
    (no network call is made since validation happens first).
    """
    response = client.post(
        "/api/v1/videos/from-url",
        json={"source_url": "http://127.0.0.1/video.mp4"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "private/internal" in body["error"]["message"]


def test_list_videos(client: TestClient, db_session: Session) -> None:
    _make_video(db_session, file_path="videos/one.mp4")
    _make_video(db_session, file_path="videos/two.mp4")

    response = client.get("/api/v1/videos/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # newest first (ordered by id desc)
    assert body[0]["file_path"] == "videos/two.mp4"
    assert body[1]["file_path"] == "videos/one.mp4"


def test_get_video_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/videos/999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "999" in body["error"]["message"]


def test_get_video_success(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session)
    response = client.get(f"/api/v1/videos/{video.id}")
    assert response.status_code == 200
    assert response.json()["id"] == video.id


def test_delete_video_cascades_clips_and_files(client: TestClient, db_session: Session) -> None:
    video = _make_video(db_session, file_path="videos/parent.mp4")
    clip1 = _make_clip(db_session, video, file_path="clips/1/clip_1.mp4")
    clip2 = _make_clip(db_session, video, file_path="clips/1/clip_2.mp4")

    with patch("app.routers.videos.storage_service.delete_file") as mock_delete:
        response = client.delete(f"/api/v1/videos/{video.id}")

    assert response.status_code == 204

    # storage_service.delete_file called once per clip file, plus once for the video file.
    deleted_paths = [call.args[0] for call in mock_delete.call_args_list]
    assert clip1.file_path in deleted_paths
    assert clip2.file_path in deleted_paths
    assert "videos/parent.mp4" in deleted_paths
    assert mock_delete.call_count == 3

    assert db_session.get(Video, video.id) is None
    assert db_session.get(Clip, clip1.id) is None
    assert db_session.get(Clip, clip2.id) is None


def test_delete_video_not_found(client: TestClient) -> None:
    response = client.delete("/api/v1/videos/999")
    assert response.status_code == 404


# --------------------------------------------------------------------------
# Service-level unit tests (ffmpeg/network mocked out entirely)
# --------------------------------------------------------------------------


def test_validate_video_file_accepts_known_extension() -> None:
    # Should not raise.
    upload_service.validate_video_file("clip.mp4", "video/mp4")


def test_validate_video_file_rejects_unknown_type() -> None:
    from app.exceptions import ValidationAppError

    with pytest.raises(ValidationAppError):
        upload_service.validate_video_file("doc.pdf", "application/pdf")


def test_probe_video_duration_parses_ffmpeg_stderr(tmp_path) -> None:
    fake_completed = MagicMock()
    fake_completed.stderr = "Duration: 00:01:05.50, start: 0.000000, bitrate: 128 kb/s"

    fake_path = tmp_path / "video.mp4"
    fake_path.write_bytes(b"fake")

    with patch("app.services.upload_service.subprocess.run", return_value=fake_completed):
        duration = upload_service.probe_video_duration(fake_path)

    assert duration == pytest.approx(65.5)


def test_probe_video_duration_raises_when_unparseable(tmp_path) -> None:
    from app.exceptions import ValidationAppError

    fake_completed = MagicMock()
    fake_completed.stderr = "not a duration line"
    fake_path = tmp_path / "video.mp4"
    fake_path.write_bytes(b"fake")

    with patch("app.services.upload_service.subprocess.run", return_value=fake_completed):
        with pytest.raises(ValidationAppError):
            upload_service.probe_video_duration(fake_path)


@pytest.mark.parametrize(
    "url,expected_message_fragment",
    [
        ("ftp://example.com/video.mp4", "Unsupported URL scheme"),
        ("http://localhost/video.mp4", "local/internal"),
        ("http://10.0.0.5/video.mp4", "private/internal"),
        ("http://169.254.169.254/video.mp4", "private/internal"),
    ],
)
def test_validate_source_url_rejects_unsafe_urls(url: str, expected_message_fragment: str) -> None:
    from app.exceptions import ValidationAppError

    with pytest.raises(ValidationAppError) as exc_info:
        url_ingest_service._validate_source_url(url)
    assert expected_message_fragment in str(exc_info.value)


def test_validate_source_url_accepts_public_https_url(monkeypatch) -> None:
    # DNS resolution is mocked so this doesn't require real network access;
    # simulates a hostname that resolves to an ordinary public address.
    monkeypatch.setattr(
        url_ingest_service.socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    # Should not raise.
    url_ingest_service._validate_source_url("https://cdn.example.com/video.mp4")


def test_validate_source_url_rejects_hostname_resolving_to_private_ip(monkeypatch) -> None:
    from app.exceptions import ValidationAppError

    # A hostname that *resolves* to an internal address must be rejected even
    # though the literal hostname string isn't itself an IP.
    monkeypatch.setattr(
        url_ingest_service.socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", ("169.254.169.254", 0))],
    )
    with pytest.raises(ValidationAppError):
        url_ingest_service._validate_source_url("https://sneaky.example.com/video.mp4")


class _FakeUploadFile:
    """Minimal async stand-in for `fastapi.UploadFile` used by `save_video_upload`."""

    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._data = data
        self._sent = False

    async def read(self, size: int) -> bytes:
        if self._sent:
            return b""
        self._sent = True
        return self._data

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_save_video_upload_full_pipeline(tmp_path, monkeypatch) -> None:
    """Exercises `save_video_upload` end-to-end with ffmpeg/storage mocked out."""
    monkeypatch.setattr(upload_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))

    fake_upload = _FakeUploadFile("clip.mp4", "video/mp4", b"fake video bytes")
    fake_probe_result = MagicMock()
    fake_probe_result.stderr = "Duration: 00:00:10.00, start: 0.000000, bitrate: 1 kb/s"

    with patch("app.services.upload_service.subprocess.run", return_value=fake_probe_result):
        result = await upload_service.save_video_upload(fake_upload)

    assert result.original_filename == "clip.mp4"
    assert result.duration == pytest.approx(10.0)
    assert result.size_bytes == len(b"fake video bytes")
    assert (tmp_path / result.file_path).read_bytes() == b"fake video bytes"


@pytest.mark.asyncio
async def test_save_video_upload_cleans_up_on_oversized_file(tmp_path, monkeypatch) -> None:
    from app.exceptions import ValidationAppError

    monkeypatch.setattr(upload_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(upload_service.settings, "MAX_UPLOAD_SIZE_MB", 0)  # 0 MB cap

    fake_upload = _FakeUploadFile("clip.mp4", "video/mp4", b"this is definitely too big")

    with pytest.raises(ValidationAppError):
        await upload_service.save_video_upload(fake_upload)

    # The partially-written file should have been cleaned up.
    assert list((tmp_path / "videos").glob("*.mp4")) == []


def _fake_ytdlp_download_factory(content: bytes, title: str = "My Cool Video"):
    """Build a fake `_run_ytdlp_download` replacement that writes `content`
    to `dest_dir/video.mp4` and returns a minimal yt-dlp `info` dict."""

    def _fake_run_ytdlp_download(source_url: str, dest_dir, max_bytes: int) -> dict:
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "video.mp4").write_bytes(content)
        return {"title": title}

    return _fake_run_ytdlp_download


@pytest.mark.asyncio
async def test_download_video_from_url_full_pipeline(tmp_path, monkeypatch) -> None:
    """Exercises `download_video_from_url` end-to-end with yt-dlp/ffmpeg mocked out."""
    monkeypatch.setattr(url_ingest_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))

    fake_probe_result = MagicMock()
    fake_probe_result.stderr = "Duration: 00:00:05.00, start: 0.000000, bitrate: 1 kb/s"

    with (
        patch(
            "app.services.url_ingest_service._run_ytdlp_download",
            side_effect=_fake_ytdlp_download_factory(b"chunk-1-chunk-2"),
        ),
        patch(
            "app.services.upload_service.subprocess.run", return_value=fake_probe_result
        ),
        patch.object(
            url_ingest_service.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ),
    ):
        result = await url_ingest_service.download_video_from_url(
            "https://example.com/videos/clip.mp4"
        )

    assert result.original_filename == "My_Cool_Video.mp4"
    assert result.duration == pytest.approx(5.0)
    assert result.size_bytes == len(b"chunk-1-chunk-2")
    assert (tmp_path / result.file_path).read_bytes() == b"chunk-1-chunk-2"


@pytest.mark.asyncio
async def test_download_video_from_url_cleans_up_on_oversized_download(
    tmp_path, monkeypatch
) -> None:
    from app.exceptions import ValidationAppError

    monkeypatch.setattr(url_ingest_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(url_ingest_service.settings, "MAX_UPLOAD_SIZE_MB", 0)

    with (
        patch(
            "app.services.url_ingest_service._run_ytdlp_download",
            side_effect=_fake_ytdlp_download_factory(b"way too much data for the cap"),
        ),
        patch.object(
            url_ingest_service.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ),
    ):
        with pytest.raises(ValidationAppError):
            await url_ingest_service.download_video_from_url(
                "https://example.com/videos/clip.mp4"
            )

    assert list((tmp_path / "videos").glob("*")) == []


@pytest.mark.asyncio
async def test_download_video_from_url_raises_on_ytdlp_download_error(
    tmp_path, monkeypatch
) -> None:
    """A yt-dlp extraction/download failure (unsupported site, private video,
    network error, etc.) surfaces as a `ValidationAppError`, not a raw
    `yt_dlp.utils.DownloadError` leaking out of the service."""
    from app.exceptions import ValidationAppError
    from yt_dlp.utils import DownloadError

    monkeypatch.setattr(url_ingest_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))

    with (
        patch(
            "app.services.url_ingest_service._run_ytdlp_download",
            side_effect=DownloadError("Unsupported URL"),
        ),
        patch.object(
            url_ingest_service.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 0))],
        ),
    ):
        with pytest.raises(ValidationAppError):
            await url_ingest_service.download_video_from_url(
                "https://video-site.example.com/watch?v=abc123"
            )

    assert list((tmp_path / "videos").glob("*")) == []
