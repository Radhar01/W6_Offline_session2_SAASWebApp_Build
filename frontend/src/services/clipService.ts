import api, { getMediaUrl } from "./api";
import type { AspectRatio, Clip, ProcessingStatus } from "@/types";

/**
 * API layer for the Clip Library (list/retrieve/update/delete/download of
 * clips that already exist — clip *generation* lives in a separate module).
 *
 * Mirrors the backend's `/clips` routes (see backend/app/routers/clips.py).
 * The backend responds with snake_case fields (see `ClipResponse` in
 * backend/app/schemas/clip.py), while `Clip` in `@/types` is camelCase.
 * That conversion is done here so callers only ever see the shared `Clip`
 * shape.
 */

/** Raw clip representation as returned by the backend (snake_case, numeric ids). */
export interface RawClip {
  id: number;
  video_id: number;
  start_time: number;
  end_time: number;
  title: string;
  thumbnail_url: string | null;
  file_path: string;
  aspect_ratio: AspectRatio;
  status: ProcessingStatus;
  created_at: string;
  updated_at: string;
}

/**
 * A stored `thumbnail_url` is either a path relative to the backend's
 * storage root (the common case — set during clip generation) or a full
 * external URL (if a caller edited it via `PUT /clips/{id}`). Only the
 * former needs the `/media` mount prefix.
 */
function resolveThumbnailUrl(rawThumbnailUrl: string | null): string | undefined {
  if (!rawThumbnailUrl) {
    return undefined;
  }
  if (/^https?:\/\//i.test(rawThumbnailUrl)) {
    return rawThumbnailUrl;
  }
  return getMediaUrl(rawThumbnailUrl);
}

export function mapClip(raw: RawClip): Clip {
  return {
    id: raw.id,
    videoId: raw.video_id,
    startTime: raw.start_time,
    endTime: raw.end_time,
    title: raw.title,
    thumbnailUrl: resolveThumbnailUrl(raw.thumbnail_url),
    filePath: raw.file_path,
    aspectRatio: raw.aspect_ratio,
    status: raw.status,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

/** Sort orders supported by the backend's `GET /clips` endpoint. */
export type ClipSortOption = "created_at_desc" | "created_at_asc" | "start_time_asc" | "start_time_desc";

export interface ListClipsParams {
  videoId?: number;
  status?: ProcessingStatus;
  sort?: ClipSortOption;
}

const CLIPS_PATH = "/clips";

/** List clips, optionally filtered by source video and/or status, and sorted. */
export async function listClips(params?: ListClipsParams): Promise<Clip[]> {
  const response = await api.get<RawClip[]>(CLIPS_PATH, {
    params: {
      video_id: params?.videoId,
      status: params?.status,
      sort: params?.sort,
    },
  });
  return response.data.map(mapClip);
}

/** Fetch a single clip by id. */
export async function getClip(id: number): Promise<Clip> {
  const response = await api.get<RawClip>(`${CLIPS_PATH}/${id}`);
  return mapClip(response.data);
}

export interface UpdateClipData {
  title?: string;
  thumbnailUrl?: string;
}

/** Update a clip's editable metadata (title and/or thumbnail URL). */
export async function updateClip(id: number, data: UpdateClipData): Promise<Clip> {
  const response = await api.put<RawClip>(`${CLIPS_PATH}/${id}`, {
    title: data.title,
    thumbnail_url: data.thumbnailUrl,
  });
  return mapClip(response.data);
}

/**
 * Full URL for downloading a clip's video file as an attachment.
 * Intended for a plain `<a href download>` link/navigation, not a JS fetch.
 */
export function getDownloadUrl(id: number): string {
  return `${api.defaults.baseURL}${CLIPS_PATH}/${id}/download`;
}

/**
 * Full URL for previewing a clip's video file inline (e.g. `<video src>`).
 * Uses the same endpoint as `getDownloadUrl` with `?inline=true` so the
 * backend serves it without a `Content-Disposition: attachment` header.
 */
export function getPreviewUrl(id: number): string {
  return `${getDownloadUrl(id)}?inline=true`;
}

/** Delete a clip (removes both its database record and its file on disk). */
export async function deleteClip(id: number): Promise<void> {
  await api.delete(`${CLIPS_PATH}/${id}`);
}
