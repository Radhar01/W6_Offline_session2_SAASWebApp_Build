"""Chunked/resumable video upload handling.

Validates and streams an incoming `UploadFile` to disk without ever loading
the whole file into memory, then probes it with ffmpeg to extract metadata
needed to create a `Video` row.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.exceptions import ValidationAppError
from app.services import storage_service

logger = logging.getLogger(__name__)

# 1 MB read chunks — large enough to be efficient, small enough to bound
# peak memory usage regardless of the uploaded file's size.
CHUNK_SIZE_BYTES = 1024 * 1024

ALLOWED_CONTENT_TYPES: set[str] = {
    "video/mp4",
    "video/quicktime",  # .mov
    "video/webm",
    "video/x-matroska",  # .mkv
    "video/x-msvideo",  # .avi
    "video/avi",
}
ALLOWED_EXTENSIONS: set[str] = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


@dataclass(frozen=True)
class VideoIngestResult:
    """Metadata needed to persist a `Video` row after ingesting a file."""

    file_path: str
    size_bytes: int
    duration: float
    original_filename: str | None


def validate_video_file(filename: str | None, content_type: str | None) -> None:
    """Raise `ValidationAppError` unless the filename/content-type look like a video.

    Checked before streaming begins so obviously-invalid uploads are rejected
    without writing anything to disk.
    """
    extension = Path(filename).suffix.lower() if filename else ""
    content_type_ok = bool(content_type) and content_type.lower() in ALLOWED_CONTENT_TYPES
    extension_ok = extension in ALLOWED_EXTENSIONS

    if not content_type_ok and not extension_ok:
        raise ValidationAppError(
            f"Unsupported video format (content_type='{content_type}', filename='{filename}'). "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )


def probe_video_duration(path: Path) -> float:
    """Run `ffmpeg -i <path>` and parse the `Duration:` line from its stderr.

    ffmpeg exits with a non-zero status when invoked without an output target
    (as here) — that is expected and not itself treated as failure. Only a
    missing/unparseable `Duration` line, or an inability to run ffmpeg at all,
    is surfaced as an error.
    """
    try:
        result = subprocess.run(
            [settings.FFMPEG_PATH, "-i", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationAppError(f"Failed to run ffmpeg on video '{path.name}': {exc}") from exc

    match = _DURATION_RE.search(result.stderr)
    if not match:
        raise ValidationAppError(
            f"Could not determine duration for '{path.name}'; the file may be corrupt "
            "or not a valid video."
        )

    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


async def save_video_upload(file: UploadFile) -> VideoIngestResult:
    """Stream an uploaded video to disk, validating type and size, then probe it.

    Returns the info needed to create a `Video` row. Raises `ValidationAppError`
    if the content type/extension is unsupported, the file exceeds
    `settings.MAX_UPLOAD_SIZE_MB`, or ffmpeg cannot read the resulting file.
    Any partially-written file is cleaned up on failure.
    """
    validate_video_file(file.filename, file.content_type)

    relative_path = storage_service.generate_relative_path(file.filename, subdir="videos")
    abs_path = storage_service.get_absolute_path(relative_path)
    storage_service.ensure_parent_dir(abs_path)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size_bytes = 0

    try:
        dest = await asyncio.to_thread(open, abs_path, "wb")
        try:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise ValidationAppError(
                        f"Uploaded file exceeds the maximum allowed size of "
                        f"{settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                await asyncio.to_thread(dest.write, chunk)
        finally:
            await asyncio.to_thread(dest.close)
    except ValidationAppError:
        storage_service.delete_file(relative_path)
        raise
    except OSError as exc:
        storage_service.delete_file(relative_path)
        raise ValidationAppError(f"Failed to save uploaded file: {exc}") from exc
    finally:
        await file.close()

    duration = await asyncio.to_thread(probe_video_duration, abs_path)
    actual_size = abs_path.stat().st_size
    logger.info(
        "Saved upload '%s' -> %s (%d bytes, %.2fs)",
        file.filename,
        relative_path,
        actual_size,
        duration,
    )

    return VideoIngestResult(
        file_path=relative_path,
        size_bytes=actual_size,
        duration=duration,
        original_filename=file.filename,
    )
