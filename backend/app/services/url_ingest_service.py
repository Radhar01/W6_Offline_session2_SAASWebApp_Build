"""URL-based video ingestion: validate, then extract/download via yt-dlp.

Supports both site-specific extractors (YouTube, Vimeo, TikTok, Instagram,
etc.) and direct video file links (yt-dlp's generic extractor handles a bare
".mp4" URL just as well as a YouTube watch page).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import shutil
import socket
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import yt_dlp

from app.config import settings
from app.exceptions import ValidationAppError
from app.services import storage_service
from app.services.upload_service import VideoIngestResult, probe_video_duration

logger = logging.getLogger(__name__)

_BLOCKED_HOSTNAMES = {"localhost"}


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if `ip` is any flavor of loopback/private/internal address."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _validate_source_url(source_url: str) -> str:
    """Validate scheme, hostname, and that the host doesn't resolve internally.

    Rejects anything but http/https, rejects literal loopback/private/
    link-local/reserved/unspecified IP addresses, and resolves the hostname
    via DNS to reject any hostname whose *resolved* address is internal.

    This only validates the user-submitted URL itself. yt-dlp performs its
    own HTTP requests (including any redirects and the eventual CDN media
    URL it discovers) which are not individually re-validated here — that's
    an accepted trade-off of delegating extraction to a third-party library
    rather than a residual gap unique to this code path.
    """
    parsed = urlparse(source_url)

    if parsed.scheme not in ("http", "https"):
        raise ValidationAppError(
            f"Unsupported URL scheme '{parsed.scheme}'; only http/https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationAppError("URL is missing a hostname.")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValidationAppError("URLs pointing to local/internal hosts are not allowed.")

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None and _is_unsafe_ip(literal_ip):
        raise ValidationAppError(
            "URLs pointing to private/internal network addresses are not allowed."
        )

    if literal_ip is None:
        try:
            resolved = socket.getaddrinfo(hostname, None)
        except OSError as exc:
            raise ValidationAppError(f"Could not resolve host '{hostname}': {exc}") from exc
        for family_info in resolved:
            addr = family_info[4][0]
            try:
                resolved_ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if _is_unsafe_ip(resolved_ip):
                raise ValidationAppError(
                    f"Host '{hostname}' resolves to a private/internal address "
                    "and is not allowed."
                )

    return source_url


def _sanitize_title(title: str | None) -> str:
    """Turn a video's extracted title into a filesystem-safe base name."""
    if not title:
        return "video"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")
    return slug[:100] or "video"


def _run_ytdlp_download(source_url: str, dest_dir: Path, max_bytes: int) -> dict:
    """Blocking yt-dlp extraction/download — always run via `asyncio.to_thread`."""
    ffmpeg_dir = str(Path(settings.FFMPEG_PATH).parent)
    ydl_opts = {
        "outtmpl": str(dest_dir / "video.%(ext)s"),
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "merge_output_format": "mp4",
        "max_filesize": max_bytes,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 2,
        "ffmpeg_location": ffmpeg_dir,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(source_url, download=True)
    return info or {}


async def download_video_from_url(source_url: str) -> VideoIngestResult:
    """Extract and download a video from `source_url`, then probe its metadata.

    Enforces `settings.MAX_UPLOAD_SIZE_MB` (via yt-dlp's format-level
    `max_filesize` filter, double-checked against the actual downloaded file
    afterward). Raises `ValidationAppError` for invalid/unsafe URLs,
    extraction/download failures, oversized downloads, or files ffmpeg can't
    read. Any partially-downloaded directory is cleaned up on failure.
    """
    _validate_source_url(source_url)

    relative_dir = f"videos/{uuid4().hex}"
    abs_dir = storage_service.get_absolute_path(relative_dir)
    abs_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        info = await asyncio.to_thread(_run_ytdlp_download, source_url, abs_dir, max_bytes)
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(abs_dir, ignore_errors=True)
        raise ValidationAppError(f"Failed to download video from URL: {exc}") from exc
    except OSError as exc:
        shutil.rmtree(abs_dir, ignore_errors=True)
        raise ValidationAppError(f"Failed to save downloaded file: {exc}") from exc

    downloaded_files = [p for p in abs_dir.iterdir() if p.is_file()]
    if not downloaded_files:
        shutil.rmtree(abs_dir, ignore_errors=True)
        raise ValidationAppError("Download completed but no video file was produced.")
    abs_path = downloaded_files[0]

    actual_size = abs_path.stat().st_size
    if actual_size > max_bytes:
        shutil.rmtree(abs_dir, ignore_errors=True)
        raise ValidationAppError(
            f"Downloaded file exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    try:
        duration = await asyncio.to_thread(probe_video_duration, abs_path)
    except ValidationAppError:
        shutil.rmtree(abs_dir, ignore_errors=True)
        raise

    relative_path = f"{relative_dir}/{abs_path.name}"
    title = _sanitize_title(info.get("title"))
    original_filename = f"{title}{abs_path.suffix}"

    logger.info(
        "Downloaded '%s' -> %s (%d bytes, %.2fs)", source_url, relative_path, actual_size, duration
    )

    return VideoIngestResult(
        file_path=relative_path,
        size_bytes=actual_size,
        duration=duration,
        original_filename=original_filename,
    )
