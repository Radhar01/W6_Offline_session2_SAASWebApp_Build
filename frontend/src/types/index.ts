/**
 * Shared domain types for ClipCreator.
 *
 * These mirror the backend Pydantic schemas (see backend/app/schemas) and
 * SQLAlchemy models (see backend/app/models). Keep field names in
 * camelCase here; the API layer is responsible for converting to/from the
 * backend's snake_case representation.
 */

/** How a video was ingested into the system. */
export type VideoSourceType = "upload" | "url";

/** Lifecycle status shared by videos and clips as they move through processing. */
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";

/** Supported output aspect ratios for generated clips. */
export type AspectRatio = "9:16" | "1:1" | "16:9";

/** A long-form source video, either uploaded directly or ingested from a URL. */
export interface Video {
  id: number;
  sourceType: VideoSourceType;
  originalFilename?: string;
  sourceUrl?: string;
  filePath: string;
  duration: number;
  sizeBytes: number;
  status: ProcessingStatus;
  createdAt: string;
  updatedAt: string;
}

/** A short, logically-segmented clip generated from a source video. */
export interface Clip {
  id: number;
  videoId: number;
  startTime: number;
  endTime: number;
  title: string;
  thumbnailUrl?: string;
  filePath: string;
  aspectRatio: AspectRatio;
  status: ProcessingStatus;
  createdAt: string;
  updatedAt: string;
}

/** Aggregate counts and storage usage shown on the dashboard's stat widgets. */
export interface DashboardStats {
  totalVideos: number;
  totalClips: number;
  storageUsedBytes: number;
}

/** A single entry in the dashboard's recent activity feed. */
export interface ActivityItem {
  id: number;
  type: "video" | "clip";
  title: string;
  status: string;
  createdAt: string;
}
