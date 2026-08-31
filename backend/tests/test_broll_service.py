"""Tests for backend/app/services/broll_service.py.

All Pexels HTTP calls are mocked; nothing here makes a real network request.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models.video import SourceType, Video, VideoStatus
from app.services import broll_service


def _make_video(**overrides) -> Video:
    defaults = dict(
        id=1,
        source_type=SourceType.upload,
        original_filename="Morning_Coffee_Routine_2024.mp4",
        file_path="videos/source.mp4",
        duration=90.0,
        size_bytes=1024,
        status=VideoStatus.pending,
    )
    defaults.update(overrides)
    return Video(**defaults)


def test_extract_keywords_strips_extension_stopwords_and_numbers() -> None:
    query = broll_service.extract_keywords("Morning_Coffee_Routine_2024_final_copy.mp4")
    assert query == "morning coffee routine"


def test_extract_keywords_falls_back_when_nothing_usable() -> None:
    query = broll_service.extract_keywords("video_final_copy.mp4")
    assert query == "abstract background"


def test_get_or_fetch_broll_returns_none_without_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(broll_service.settings, "PEXELS_API_KEY", None)
    monkeypatch.setattr(
        "app.services.broll_service.get_absolute_path", lambda rel: tmp_path / rel
    )

    result = broll_service.get_or_fetch_broll(_make_video())

    assert result is None


def test_get_or_fetch_broll_reuses_cached_video_asset(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(broll_service.settings, "PEXELS_API_KEY", "fake-key")
    monkeypatch.setattr(
        "app.services.broll_service.get_absolute_path", lambda rel: tmp_path / rel
    )

    cache_dir = tmp_path / "broll" / "1"
    cache_dir.mkdir(parents=True)
    (cache_dir / "broll.mp4").write_bytes(b"fake-video-bytes")

    with patch("app.services.broll_service.requests.get") as mock_get:
        result = broll_service.get_or_fetch_broll(_make_video())

    mock_get.assert_not_called()
    assert result is not None
    assert result.is_video is True
    assert result.absolute_path.endswith("broll.mp4")


def test_get_or_fetch_broll_downloads_video_result(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(broll_service.settings, "PEXELS_API_KEY", "fake-key")
    monkeypatch.setattr(
        "app.services.broll_service.get_absolute_path", lambda rel: tmp_path / rel
    )

    search_response = MagicMock()
    search_response.raise_for_status = MagicMock()
    search_response.json.return_value = {
        "videos": [
            {
                "video_files": [
                    {"link": "https://example.com/big.mp4", "width": 1920, "height": 1080},
                    {"link": "https://example.com/small.mp4", "width": 720, "height": 1280},
                ]
            }
        ]
    }

    download_response = MagicMock()
    download_response.raise_for_status = MagicMock()
    download_response.iter_content.return_value = [b"chunk1", b"chunk2"]

    with patch(
        "app.services.broll_service.requests.get",
        side_effect=[search_response, download_response],
    ):
        result = broll_service.get_or_fetch_broll(_make_video())

    assert result is not None
    assert result.is_video is True
    assert (tmp_path / "broll" / "1" / "broll.mp4").read_bytes() == b"chunk1chunk2"


def test_get_or_fetch_broll_falls_back_to_photo_when_no_video_results(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(broll_service.settings, "PEXELS_API_KEY", "fake-key")
    monkeypatch.setattr(
        "app.services.broll_service.get_absolute_path", lambda rel: tmp_path / rel
    )

    empty_video_search = MagicMock()
    empty_video_search.raise_for_status = MagicMock()
    empty_video_search.json.return_value = {"videos": []}

    photo_search = MagicMock()
    photo_search.raise_for_status = MagicMock()
    photo_search.json.return_value = {
        "photos": [{"src": {"portrait": "https://example.com/photo.jpg"}}]
    }

    download_response = MagicMock()
    download_response.raise_for_status = MagicMock()
    download_response.iter_content.return_value = [b"jpegbytes"]

    with patch(
        "app.services.broll_service.requests.get",
        side_effect=[empty_video_search, photo_search, download_response],
    ):
        result = broll_service.get_or_fetch_broll(_make_video())

    assert result is not None
    assert result.is_video is False
    assert (tmp_path / "broll" / "1" / "broll.jpg").read_bytes() == b"jpegbytes"


def test_get_or_fetch_broll_returns_none_on_request_failure(monkeypatch, tmp_path) -> None:
    import requests

    monkeypatch.setattr(broll_service.settings, "PEXELS_API_KEY", "fake-key")
    monkeypatch.setattr(
        "app.services.broll_service.get_absolute_path", lambda rel: tmp_path / rel
    )

    with patch(
        "app.services.broll_service.requests.get",
        side_effect=requests.RequestException("network down"),
    ):
        result = broll_service.get_or_fetch_broll(_make_video())

    assert result is None


def test_trim_intro_replaces_file_when_long_enough(tmp_path) -> None:
    video_path = tmp_path / "broll.mp4"
    video_path.write_bytes(b"original-bytes")

    fake_run = MagicMock(returncode=0)

    def fake_side_effect(cmd, **kwargs):
        # The real ffmpeg invocation would write the trimmed output file;
        # simulate that so `_trim_intro` finds it and swaps it in.
        Path(cmd[-1]).write_bytes(b"trimmed-bytes")
        return fake_run

    with (
        patch("app.services.broll_service.probe_video_duration", return_value=10.0),
        patch("app.services.broll_service.subprocess.run", side_effect=fake_side_effect),
    ):
        broll_service._trim_intro(video_path)

    assert video_path.read_bytes() == b"trimmed-bytes"


def test_trim_intro_skips_clip_too_short_to_trim(tmp_path) -> None:
    video_path = tmp_path / "broll.mp4"
    video_path.write_bytes(b"original-bytes")

    with (
        patch("app.services.broll_service.probe_video_duration", return_value=3.0),
        patch("app.services.broll_service.subprocess.run") as mock_run,
    ):
        broll_service._trim_intro(video_path)

    mock_run.assert_not_called()
    assert video_path.read_bytes() == b"original-bytes"


def test_trim_intro_leaves_original_when_ffmpeg_fails(tmp_path) -> None:
    video_path = tmp_path / "broll.mp4"
    video_path.write_bytes(b"original-bytes")

    with (
        patch("app.services.broll_service.probe_video_duration", return_value=10.0),
        patch("app.services.broll_service.subprocess.run", return_value=MagicMock(returncode=1)),
    ):
        broll_service._trim_intro(video_path)

    assert video_path.read_bytes() == b"original-bytes"


def test_trim_intro_leaves_original_when_duration_probe_fails(tmp_path) -> None:
    from app.exceptions import ValidationAppError

    video_path = tmp_path / "broll.mp4"
    video_path.write_bytes(b"original-bytes")

    with (
        patch(
            "app.services.broll_service.probe_video_duration",
            side_effect=ValidationAppError("bad file"),
        ),
        patch("app.services.broll_service.subprocess.run") as mock_run,
    ):
        broll_service._trim_intro(video_path)

    mock_run.assert_not_called()
    assert video_path.read_bytes() == b"original-bytes"
