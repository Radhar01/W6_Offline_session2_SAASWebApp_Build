import type { AxiosProgressEvent } from "axios";

import api from "./api";
import type { Video, VideoSourceType, ProcessingStatus } from "@/types";

/**
 * API layer for video ingestion (file upload + URL import) and lookup.
 *
 * Mirrors the backend's `/videos` routes (see backend/app/routers/videos.py).
 * The backend responds with snake_case fields and integer ids (see
 * `VideoResponse` in backend/app/schemas/video.py), while `Video` in
 * `@/types` is camelCase. That conversion is done here so callers only ever
 * see the shared `Video` shape.
 */

/** Raw video representation as returned by the backend (snake_case). */
interface RawVideo {
  id: number;
  source_type: VideoSourceType;
  original_filename: string | null;
  source_url: string | null;
  file_path: string;
  duration: number;
  size_bytes: number;
  status: ProcessingStatus;
  created_at: string;
  updated_at: string;
}

function mapVideo(raw: RawVideo): Video {
  return {
    id: raw.id,
    sourceType: raw.source_type,
    originalFilename: raw.original_filename ?? undefined,
    sourceUrl: raw.source_url ?? undefined,
    filePath: raw.file_path,
    duration: raw.duration,
    sizeBytes: raw.size_bytes,
    status: raw.status,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

/**
 * Upload a video file as multipart/form-data, reporting progress as a
 * whole-number percent (0-100) via `onProgress`.
 */
export async function uploadVideo(file: File, onProgress: (percent: number) => void): Promise<Video> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<RawVideo>("/videos/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (!event.total) {
        return;
      }
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress(percent);
    },
  });

  return mapVideo(response.data);
}

/** Ingest a video from a remote URL (e.g. YouTube link) instead of a file upload. */
export async function submitVideoUrl(url: string): Promise<Video> {
  const response = await api.post<RawVideo>("/videos/from-url", { source_url: url });
  return mapVideo(response.data);
}

/** List all videos known to the backend. */
export async function listVideos(): Promise<Video[]> {
  // Trailing slash matches the backend route exactly (avoids a 307 redirect hop).
  const response = await api.get<RawVideo[]>("/videos/");
  return response.data.map(mapVideo);
}

/** Fetch a single video by id. */
export async function getVideo(id: number): Promise<Video> {
  const response = await api.get<RawVideo>(`/videos/${id}`);
  return mapVideo(response.data);
}

/** Delete a video by id. */
export async function deleteVideo(id: number): Promise<void> {
  await api.delete(`/videos/${id}`);
}
