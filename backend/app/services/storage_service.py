"""File storage helpers for media (videos, clips) persisted on local disk.

All paths stored in the database are *relative* to `settings.MEDIA_STORAGE_PATH`.
Callers should use `get_absolute_path` to resolve a relative path before doing
disk I/O, and `generate_relative_path` to mint a fresh, collision-free path for
a newly ingested file.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.config import settings
from app.exceptions import ValidationAppError

logger = logging.getLogger(__name__)


def get_media_root() -> Path:
    """Return the configured media storage root as an absolute `Path`."""
    return Path(settings.MEDIA_STORAGE_PATH).resolve()


def get_absolute_path(relative_path: str) -> Path:
    """Resolve a relative storage path to an absolute path under the media root.

    Raises `ValidationAppError` if the resolved path would escape the media
    root (e.g. via `..` traversal or an absolute-path override) — every
    caller relies on this containment check, since some values (like a
    clip's `thumbnail_url`) ultimately originate from client-supplied input.
    """
    root = get_media_root()
    resolved = (root / relative_path).resolve()
    if not resolved.is_relative_to(root):
        raise ValidationAppError(f"Path '{relative_path}' resolves outside the storage root.")
    return resolved


def generate_relative_path(original_filename: str | None, subdir: str = "videos") -> str:
    """Build a unique, collision-free relative path for a new file.

    Preserves the original extension (if any) so downstream tools (e.g. ffmpeg)
    can still infer the container format from the filename.
    """
    suffix = Path(original_filename).suffix if original_filename else ""
    return f"{subdir}/{uuid4().hex}{suffix}"


def ensure_parent_dir(path: Path) -> None:
    """Create the parent directory of `path`, if it doesn't already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(file_obj: BinaryIO, dest_relative_path: str) -> str:
    """Write a file-like object's full contents to storage in one shot.

    Prefer streaming/chunked writes (see `upload_service`) for large, untrusted
    uploads; this helper is for smaller or already-buffered files.

    Returns the relative path the file was stored at.
    """
    abs_path = get_absolute_path(dest_relative_path)
    ensure_parent_dir(abs_path)
    with open(abs_path, "wb") as dest:
        shutil.copyfileobj(file_obj, dest)
    logger.info("Saved uploaded file to %s", abs_path)
    return dest_relative_path


def save_upload_chunk(dest_relative_path: str, chunk: bytes, append: bool = True) -> str:
    """Write a single chunk of bytes to the destination file under the media root.

    Used by callers that stream a large file (e.g. `UploadFile` or an HTTP
    response body) piece by piece instead of buffering it fully in memory.
    Pass `append=False` for the first chunk of a new file to truncate/create it.

    Returns the relative path the chunk was written to.
    """
    abs_path = get_absolute_path(dest_relative_path)
    ensure_parent_dir(abs_path)
    mode = "ab" if append else "wb"
    with open(abs_path, mode) as dest:
        dest.write(chunk)
    return dest_relative_path


def delete_file(path: str | None) -> None:
    """Safely remove a file if it exists. Never raises on a missing/bad/unsafe path.

    Always resolves `path` as *relative* to the media root via `get_absolute_path`
    (even if it looks absolute) so a path that would escape the storage root is
    rejected rather than silently deleting an arbitrary file on disk.
    """
    if not path:
        return
    try:
        abs_path = get_absolute_path(path)
    except ValidationAppError:
        logger.warning("Refusing to delete path outside storage root: %s", path)
        return
    try:
        if abs_path.exists():
            abs_path.unlink()
            logger.info("Deleted file %s", abs_path)
    except OSError:
        logger.warning("Failed to delete file %s", path, exc_info=True)
