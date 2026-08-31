"""B-roll background sourcing: pick a background image/video relevant to a
Video's content and cache it for reuse across that video's clips.

"Relevant" here means a simple keyword match: the video's title/filename is
reduced to a short search query and used against the free Pexels stock-media
API. This is a heuristic, not real content understanding -- there's no
transcription or topic modeling involved.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

from app.config import settings
from app.exceptions import ValidationAppError
from app.models.video import Video
from app.services.storage_service import get_absolute_path
from app.services.upload_service import probe_video_duration

logger = logging.getLogger(__name__)

_PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"
_PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"
_SEARCH_TIMEOUT_SECONDS = 10
_DOWNLOAD_TIMEOUT_SECONDS = 30

# Stock clips often open on a couple of static/establishing seconds before
# the subject enters frame. Since the clip is looped continuously behind a
# generated clip's full duration, that dead time would otherwise repeat on
# every cycle -- so it's trimmed off once, right after download.
_INTRO_TRIM_SECONDS = 2.0
_MIN_DURATION_TO_TRIM = _INTRO_TRIM_SECONDS + 3.0

_CACHED_VIDEO_FILENAME = "broll.mp4"
_CACHED_IMAGE_FILENAME = "broll.jpg"

# Generic/technical tokens that make poor search keywords (filenames,
# camera/export boilerplate, etc.).
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "video", "clip", "clips", "final", "copy", "new", "raw", "source",
    "file", "recording", "record", "screen", "capture", "untitled",
    "export", "output", "movie", "mov", "mp4", "download",
}


@dataclass(frozen=True)
class BrollAsset:
    """A locally-cached background asset to composite behind a clip's main video."""

    absolute_path: str
    is_video: bool


def extract_keywords(text: str, max_words: int = 4) -> str:
    """Derive a short stock-media search query from a filename or title.

    Strips the extension, splits on non-alphanumeric characters, drops
    stopwords/pure numbers, and joins the first `max_words` remaining
    tokens. Falls back to a generic query if nothing usable remains.
    """
    stem = Path(text).stem
    words = re.split(r"[^A-Za-z0-9]+", stem)
    keywords = [w.lower() for w in words if w and not w.isdigit() and w.lower() not in _STOPWORDS]
    return " ".join(keywords[:max_words]) or "abstract background"


def get_or_fetch_broll(video: Video) -> BrollAsset | None:
    """Return a cached (or newly-fetched) B-roll asset for `video`, or `None`.

    Caches the downloaded asset under `broll/{video_id}/` so repeated clip
    generation/regeneration for the same video reuses a single fetch. Never
    raises: a missing API key, no search results, or a network failure all
    just mean "no B-roll for this video" -- callers fall back to the
    existing blurred-self background instead of failing clip generation.
    """
    relative_dir = f"broll/{video.id}"
    abs_dir = get_absolute_path(relative_dir)

    cached = _find_cached_asset(abs_dir)
    if cached is not None:
        return cached

    if not settings.PEXELS_API_KEY:
        return None

    query = extract_keywords(video.original_filename or "")
    abs_dir.mkdir(parents=True, exist_ok=True)

    asset = _fetch_video_broll(query, abs_dir) or _fetch_photo_broll(query, abs_dir)
    if asset is None:
        logger.info("No B-roll found for video %s (query=%r)", video.id, query)
    return asset


def _find_cached_asset(abs_dir: Path) -> BrollAsset | None:
    video_path = abs_dir / _CACHED_VIDEO_FILENAME
    if video_path.is_file():
        return BrollAsset(absolute_path=str(video_path), is_video=True)
    image_path = abs_dir / _CACHED_IMAGE_FILENAME
    if image_path.is_file():
        return BrollAsset(absolute_path=str(image_path), is_video=False)
    return None


def _fetch_video_broll(query: str, abs_dir: Path) -> BrollAsset | None:
    try:
        response = requests.get(
            _PEXELS_VIDEO_SEARCH_URL,
            params={"query": query, "orientation": "portrait", "per_page": 5},
            headers={"Authorization": settings.PEXELS_API_KEY},
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Pexels video search failed for %r: %s", query, exc)
        return None

    for video_result in videos:
        file_url = _pick_video_file(video_result.get("video_files", []))
        if not file_url:
            continue
        dest = abs_dir / _CACHED_VIDEO_FILENAME
        if _download(file_url, dest):
            _trim_intro(dest)
            return BrollAsset(absolute_path=str(dest), is_video=True)
    return None


def _pick_video_file(video_files: list[dict]) -> str | None:
    """Prefer a portrait-oriented file, smallest first (keeps downloads fast)."""
    portrait = [f for f in video_files if f.get("height", 0) > f.get("width", 0)]
    candidates = portrait or video_files
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda f: f.get("width") or 10**9)
    return candidates[0].get("link")


def _fetch_photo_broll(query: str, abs_dir: Path) -> BrollAsset | None:
    try:
        response = requests.get(
            _PEXELS_PHOTO_SEARCH_URL,
            params={"query": query, "orientation": "portrait", "per_page": 1},
            headers={"Authorization": settings.PEXELS_API_KEY},
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Pexels photo search failed for %r: %s", query, exc)
        return None

    if not photos:
        return None

    src = photos[0].get("src", {})
    image_url = src.get("portrait") or src.get("large")
    if not image_url:
        return None

    dest = abs_dir / _CACHED_IMAGE_FILENAME
    if _download(image_url, dest):
        return BrollAsset(absolute_path=str(dest), is_video=False)
    return None


def _trim_intro(path: Path) -> None:
    """Cut `_INTRO_TRIM_SECONDS` off the start of a downloaded B-roll video, in place.

    Best-effort and silent: skips clips too short to spare the trim, and
    tolerates ffmpeg/probe failures by leaving the untrimmed file in place.
    A duller loop beats losing the B-roll entirely, and this must never
    block clip generation.
    """
    try:
        duration = probe_video_duration(path)
    except ValidationAppError:
        return
    if duration < _MIN_DURATION_TO_TRIM:
        return

    trimmed_path = path.with_name(path.stem + ".trimmed" + path.suffix)
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss",
        str(_INTRO_TRIM_SECONDS),
        "-i",
        str(path),
        "-c",
        "copy",
        str(trimmed_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to trim B-roll intro for %s: %s", path, exc)
        return

    if result.returncode != 0 or not trimmed_path.is_file():
        trimmed_path.unlink(missing_ok=True)
        logger.warning("ffmpeg failed trimming B-roll intro for %s", path)
        return

    trimmed_path.replace(path)


def _download(url: str, dest: Path) -> bool:
    try:
        response = requests.get(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS, stream=True)
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=256 * 1024):
                f.write(chunk)
        return True
    except (requests.RequestException, OSError) as exc:
        logger.warning("Failed to download B-roll asset from %s: %s", url, exc)
        return False
