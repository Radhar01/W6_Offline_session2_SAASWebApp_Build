"""Tests for backend/app/services/storage_service.py.

Pure filesystem logic (no ffmpeg/network involved) — tested directly against
a temp directory used as the media root.
"""

from __future__ import annotations

import io

import pytest

from app.exceptions import ValidationAppError
from app.services import storage_service


def test_get_media_root_resolves_configured_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    assert storage_service.get_media_root() == tmp_path.resolve()


def test_get_absolute_path_joins_media_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    result = storage_service.get_absolute_path("videos/abc.mp4")
    assert result == (tmp_path / "videos" / "abc.mp4").resolve()


def test_generate_relative_path_preserves_extension() -> None:
    path = storage_service.generate_relative_path("my video.MOV", subdir="videos")
    assert path.startswith("videos/")
    assert path.endswith(".MOV")


def test_generate_relative_path_handles_missing_filename() -> None:
    path = storage_service.generate_relative_path(None, subdir="clips")
    assert path.startswith("clips/")
    assert "." not in path.split("/")[-1]


def test_ensure_parent_dir_creates_directory(tmp_path) -> None:
    target = tmp_path / "nested" / "dir" / "file.mp4"
    assert not target.parent.exists()
    storage_service.ensure_parent_dir(target)
    assert target.parent.exists()


def test_save_uploaded_file_writes_contents(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    relative_path = "videos/test.mp4"

    result = storage_service.save_uploaded_file(io.BytesIO(b"hello world"), relative_path)

    assert result == relative_path
    assert (tmp_path / "videos" / "test.mp4").read_bytes() == b"hello world"


def test_save_upload_chunk_creates_then_appends(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    relative_path = "videos/chunked.mp4"

    storage_service.save_upload_chunk(relative_path, b"chunk1", append=False)
    storage_service.save_upload_chunk(relative_path, b"chunk2", append=True)

    assert (tmp_path / "videos" / "chunked.mp4").read_bytes() == b"chunk1chunk2"


def test_delete_file_removes_existing_relative_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    target = tmp_path / "videos" / "to-delete.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"data")

    storage_service.delete_file("videos/to-delete.mp4")

    assert not target.exists()


def test_delete_file_removes_existing_file_within_media_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    target = tmp_path / "videos" / "to-delete.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"data")

    storage_service.delete_file("videos/to-delete.mp4")

    assert not target.exists()


def test_delete_file_refuses_absolute_path_outside_media_root(tmp_path, monkeypatch) -> None:
    """An absolute path outside the media root must be refused, not deleted.

    Regression test: `Path(root) / "/etc/passwd"` discards `root` entirely
    (pathlib's `/` operator on an absolute right-hand side), so without an
    explicit containment check `delete_file` would happily delete an
    arbitrary file anywhere on disk if handed an absolute path.
    """
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(media_root))

    outside_target = tmp_path / "outside-media-root.txt"
    outside_target.write_bytes(b"do not delete me")

    storage_service.delete_file(str(outside_target))

    assert outside_target.exists()


def test_get_absolute_path_rejects_traversal_outside_media_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))

    with pytest.raises(ValidationAppError):
        storage_service.get_absolute_path("../outside.txt")


def test_delete_file_tolerates_missing_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    # Should not raise even though the file doesn't exist.
    storage_service.delete_file("videos/does-not-exist.mp4")


def test_delete_file_noop_for_none_or_empty() -> None:
    # Should not raise.
    storage_service.delete_file(None)
    storage_service.delete_file("")


def test_delete_file_swallows_os_error(monkeypatch, tmp_path) -> None:
    """If unlink() raises OSError (e.g. permissions), delete_file logs and returns."""
    monkeypatch.setattr(storage_service.settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    target = tmp_path / "videos" / "locked.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"data")

    def _raise_os_error(self):
        raise OSError("permission denied")

    monkeypatch.setattr("pathlib.Path.unlink", _raise_os_error)

    # Should not raise.
    storage_service.delete_file("videos/locked.mp4")
