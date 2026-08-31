import api from "./api";
import { mapClip, type RawClip } from "./clipService";
import { getVideo } from "./videoService";
import type { Clip, ProcessingStatus } from "@/types";

/**
 * API layer for clip generation and clip lifecycle management.
 *
 * Mirrors the backend's `/videos/{id}/generate-clips`, `/videos/{id}/clips`
 * and `/clips/*` routes (see backend/app/routers). The backend responds with
 * snake_case fields, so responses are mapped via `mapClip` from
 * `clipService` (the shared Clip <-> RawClip mapping) rather than assumed to
 * already match the `Clip` shape.
 */

/** Re-exported so callers of this service don't need to know it lives in videoService. */
export { getVideo };

/** Minimal status returned by the generate-clips endpoint (not a full Video). */
export interface VideoStatus {
  id: number;
  status: ProcessingStatus;
}

/** Kick off clip generation for a video that has finished uploading. */
export async function triggerClipGeneration(videoId: number): Promise<VideoStatus> {
  const response = await api.post<VideoStatus>(`/videos/${videoId}/generate-clips`);
  return response.data;
}

/** Fetch all clips generated (so far) for a given source video. */
export async function getClipsForVideo(videoId: number): Promise<Clip[]> {
  const response = await api.get<RawClip[]>(`/videos/${videoId}/clips`);
  return response.data.map(mapClip);
}

/** Ask the backend to regenerate a single clip (e.g. after a failure). */
export async function regenerateClip(clipId: number): Promise<Clip> {
  const response = await api.post<RawClip>(`/clips/${clipId}/regenerate`);
  return mapClip(response.data);
}

/** Adjust a clip's in/out points. */
export async function updateClipBoundaries(
  clipId: number,
  startTime: number,
  endTime: number,
): Promise<Clip> {
  const response = await api.put<RawClip>(`/clips/${clipId}/boundaries`, {
    start_time: startTime,
    end_time: endTime,
  });
  return mapClip(response.data);
}
