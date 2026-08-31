import api from "./api";
import type { ActivityItem, DashboardStats } from "@/types";

/**
 * API layer for the dashboard overview: aggregate stats and recent activity.
 *
 * Mirrors the backend's `/dashboard` routes (see backend/app/routers/dashboard.py).
 * The backend responds with snake_case fields (see `DashboardStats`/`ActivityItem`
 * in backend/app/schemas/dashboard.py), while the types in `@/types` are
 * camelCase. That conversion is done here so callers only ever see the
 * shared shapes.
 */

interface RawDashboardStats {
  total_videos: number;
  total_clips: number;
  storage_used_bytes: number;
}

interface RawActivityItem {
  id: number;
  type: "video" | "clip";
  title: string;
  status: string;
  created_at: string;
}

function mapDashboardStats(raw: RawDashboardStats): DashboardStats {
  return {
    totalVideos: raw.total_videos,
    totalClips: raw.total_clips,
    storageUsedBytes: raw.storage_used_bytes,
  };
}

function mapActivityItem(raw: RawActivityItem): ActivityItem {
  return {
    id: raw.id,
    type: raw.type,
    title: raw.title,
    status: raw.status,
    createdAt: raw.created_at,
  };
}

/** Fetch aggregate counts and storage usage for the dashboard stat widgets. */
export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await api.get<RawDashboardStats>("/dashboard/stats");
  return mapDashboardStats(response.data);
}

/** Fetch the most recent activity items (videos and clips), newest first. */
export async function getRecentActivity(limit = 20): Promise<ActivityItem[]> {
  const response = await api.get<{ items: RawActivityItem[] }>("/dashboard/activity", {
    params: { limit },
  });
  return response.data.items.map(mapActivityItem);
}
