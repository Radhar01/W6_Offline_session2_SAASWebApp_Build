"""AI-driven clip segmentation service.

Segments a source video into short, logically-bounded clips and renders
each one (plus a thumbnail) to storage via ffmpeg.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import ValidationAppError
from app.models.clip import AspectRatio, Clip, ClipStatus
from app.models.video import Video
from app.services import broll_service
from app.services.broll_service import BrollAsset
from app.services.storage_service import delete_file, get_absolute_path

logger = logging.getLogger(__name__)

# --- Segmentation heuristic constants -------------------------------------
# Placeholder for a future topic/scene ML model: uses ffmpeg scene-change
# detection grouped into target-length clips, falling back to fixed intervals.
SCENE_CHANGE_THRESHOLD = 0.4
MIN_CLIP_DURATION_SECONDS = 45.0
MAX_CLIP_DURATION_SECONDS = 60.0
FALLBACK_INTERVAL_SECONDS = 55.0

# --- Output format constants -----------------------------------------------
# Every clip is rendered as a vertical short/reel: 1080x1920 (9:16), 30fps,
# H.264/AAC in an MP4 container.
CLIP_OUTPUT_WIDTH = 1080
CLIP_OUTPUT_HEIGHT = 1920
CLIP_OUTPUT_FPS = 30

_PTS_TIME_RE = re.compile(r"pts_time:(?P<time>[0-9]+(?:\.[0-9]+)?)")


def generate_clips(video: Video, db: Session) -> list[Clip]:
    """Segment `video` into one or more `Clip` rows and persist them.

    Detects candidate scene-cut timestamps via ffmpeg, groups them into
    `MIN_CLIP_DURATION_SECONDS`-`MAX_CLIP_DURATION_SECONDS` segments, cuts
    each segment (and a thumbnail) to its own file, and creates a
    corresponding `Clip` row. Always produces at least one clip.
    """
    if not video.duration or video.duration <= 0:
        raise ValidationAppError("Video duration is unknown; cannot generate clips.")

    source_path = get_absolute_path(video.file_path)
    cut_points = _detect_scene_cuts(source_path, video.duration)
    segments = _build_segments(cut_points, video.duration)
    broll = broll_service.get_or_fetch_broll(video)

    clips_dir = Path(settings.MEDIA_STORAGE_PATH) / "clips" / str(video.id)
    thumbs_dir = Path(settings.MEDIA_STORAGE_PATH) / "thumbnails" / str(video.id)
    clips_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    clips: list[Clip] = []
    for index, (start, end) in enumerate(segments, start=1):
        clip_rel_path = f"clips/{video.id}/clip_{index}.mp4"
        thumb_rel_path = f"thumbnails/{video.id}/clip_{index}.jpg"
        clip_abs_path = get_absolute_path(clip_rel_path)
        thumb_abs_path = get_absolute_path(thumb_rel_path)

        _cut_segment(source_path, start, end, clip_abs_path, broll)
        _extract_thumbnail(source_path, (start + end) / 2, thumb_abs_path, broll)

        clip = Clip(
            video_id=video.id,
            start_time=start,
            end_time=end,
            title=f"Clip {index}",
            thumbnail_url=thumb_rel_path,
            file_path=clip_rel_path,
            aspect_ratio=AspectRatio.vertical,
            status=ClipStatus.completed,
        )
        db.add(clip)
        clips.append(clip)

    db.commit()
    for clip in clips:
        db.refresh(clip)
    return clips


def regenerate_clip_file(video: Video, clip: Clip) -> None:
    """Re-cut `clip`'s file (and thumbnail) from its current start/end against the source video.

    Deletes the existing clip/thumbnail files first, then re-renders them
    in place at the same relative paths. Mutates `clip` in place; does not
    commit — the caller (router) owns the transaction/status transitions.
    """
    source_path = get_absolute_path(video.file_path)
    clip_abs_path = get_absolute_path(clip.file_path)
    broll = broll_service.get_or_fetch_broll(video)

    _safe_delete(clip_abs_path)
    Path(clip_abs_path).parent.mkdir(parents=True, exist_ok=True)
    _cut_segment(source_path, clip.start_time, clip.end_time, clip_abs_path, broll)

    if clip.thumbnail_url:
        thumb_abs_path = get_absolute_path(clip.thumbnail_url)
        _safe_delete(thumb_abs_path)
        Path(thumb_abs_path).parent.mkdir(parents=True, exist_ok=True)
        thumb_timestamp = (clip.start_time + clip.end_time) / 2
        _extract_thumbnail(source_path, thumb_timestamp, thumb_abs_path, broll)


def _safe_delete(path: str) -> None:
    """Delete a file via `storage_service.delete_file`, tolerating a missing/already-gone file."""
    try:
        delete_file(path)
    except Exception:  # noqa: BLE001 - best-effort cleanup, never blocks regeneration
        logger.warning("Could not delete existing file at %s; continuing anyway", path)


def _detect_scene_cuts(source_path: str, duration: float) -> list[float]:
    """Run ffmpeg scene-change detection and return sorted candidate cut timestamps."""
    cmd = [
        settings.FFMPEG_PATH,
        "-i",
        source_path,
        "-vf",
        f"select='gt(scene,{SCENE_CHANGE_THRESHOLD})',showinfo",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning(
            "Scene detection failed for %s, falling back to fixed intervals: %s", source_path, exc
        )
        return []

    timestamps = {float(m.group("time")) for m in _PTS_TIME_RE.finditer(result.stderr)}
    return sorted(t for t in timestamps if 0 < t < duration)


def _build_segments(cut_points: list[float], duration: float) -> list[tuple[float, float]]:
    """Group candidate scene-cut points into MIN/MAX-length clip segments.

    Falls back to fixed-interval splitting when there are no usable cut
    points, guaranteeing at least one segment for any positive duration.
    """
    if not cut_points:
        return _fixed_interval_segments(duration)

    segments: list[tuple[float, float]] = []
    remaining_cuts = list(cut_points)
    start = 0.0

    while start < duration - 0.5:
        candidates = [
            c
            for c in remaining_cuts
            if MIN_CLIP_DURATION_SECONDS <= (c - start) <= MAX_CLIP_DURATION_SECONDS
        ]
        end = candidates[0] if candidates else min(start + MAX_CLIP_DURATION_SECONDS, duration)
        end = min(end, duration)

        if end - start < MIN_CLIP_DURATION_SECONDS and segments:
            prev_start, _ = segments.pop()
            end = max(end, duration) if duration - start < MIN_CLIP_DURATION_SECONDS else end
            segments.append((prev_start, end))
        else:
            segments.append((start, end))

        remaining_cuts = [c for c in remaining_cuts if c > end]
        start = end

    return segments if segments else _fixed_interval_segments(duration)


def _fixed_interval_segments(
    duration: float, interval: float = FALLBACK_INTERVAL_SECONDS
) -> list[tuple[float, float]]:
    """Split `duration` seconds into fixed-length segments (always at least one)."""
    if duration <= MAX_CLIP_DURATION_SECONDS:
        return [(0.0, duration)]

    segments: list[tuple[float, float]] = []
    start = 0.0
    while start < duration:
        end = min(start + interval, duration)
        remaining = duration - end
        # Merge a short trailing remainder into the final segment, but only
        # if doing so doesn't push that segment past the max clip duration.
        if 0 < remaining <= MAX_CLIP_DURATION_SECONDS - interval:
            end = duration
        segments.append((start, end))
        start = end
    return segments


def _background_filter_and_inputs(
    broll: BrollAsset | None, fps: int | None = None
) -> tuple[list[str], str]:
    """Build the extra ffmpeg input args + filter graph for the vertical background.

    Either way, the *entire* source frame is fitted (scaled down, never
    cropped) into the 1080x1920 canvas and centered on top of a background
    that fills the rest of the frame:

    - With a B-roll asset (`broll_service`), that background is the fetched
      image/video, looped to cover the clip's full duration.
    - Without one, it falls back to a blurred, cropped copy of the source's
      own frame -- the standard letterboxed "reels/shorts" treatment.
    """
    fps_suffix = f",fps={fps}" if fps else ""

    if broll is None:
        filter_complex = (
            f"[0:v]scale={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT},gblur=sigma=20[bg];"
            f"[0:v]scale={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2{fps_suffix}[outv]"
        )
        return [], filter_complex

    extra_inputs = (
        ["-stream_loop", "-1", "-i", broll.absolute_path]
        if broll.is_video
        else ["-loop", "1", "-i", broll.absolute_path]
    )
    filter_complex = (
        f"[1:v]scale={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT}[bg];"
        f"[0:v]scale={CLIP_OUTPUT_WIDTH}:{CLIP_OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2{fps_suffix}[outv]"
    )
    return extra_inputs, filter_complex


def _cut_segment(
    source_path: str, start: float, end: float, dest_path: str, broll: BrollAsset | None
) -> None:
    """Cut [start, end) from `source_path` into `dest_path`, re-encoded as a
    vertical 9:16 short (1080x1920 @30fps, H.264/AAC MP4) with the full
    source frame fitted (never cropped) over a B-roll or blurred-self
    background -- see `_background_filter_and_inputs`.
    """
    extra_inputs, filter_complex = _background_filter_and_inputs(broll, fps=CLIP_OUTPUT_FPS)
    duration = end - start
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss",
        str(start),
        "-to",
        str(end),
        "-i",
        source_path,
        *extra_inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        dest_path,
    ]
    _run_ffmpeg(cmd, f"Failed to cut clip [{start}, {end}] from {source_path}")


def _extract_thumbnail(
    source_path: str, timestamp: float, dest_path: str, broll: BrollAsset | None
) -> None:
    """Extract a single-frame vertical (fitted, not cropped) thumbnail from
    `source_path` at `timestamp` seconds, matching the clip's own framing
    and background.
    """
    extra_inputs, filter_complex = _background_filter_and_inputs(broll)
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        source_path,
        *extra_inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-frames:v",
        "1",
        dest_path,
    ]
    _run_ffmpeg(cmd, f"Failed to generate thumbnail at {timestamp}s from {source_path}")


def _run_ffmpeg(cmd: list[str], error_message: str) -> None:
    """Run an ffmpeg subprocess, raising `ValidationAppError` (with logging) on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.exception(error_message)
        raise ValidationAppError(f"{error_message}: {exc}") from exc

    if result.returncode != 0:
        logger.error("%s (ffmpeg stderr: %s)", error_message, result.stderr[-2000:])
        raise ValidationAppError(error_message)
