import { Film, HardDrive, ListVideo } from "lucide-react";

import { GlassCard } from "@/components/ui/GlassCard";
import type { DashboardStats } from "@/types";

interface StatsWidgetRowProps {
  stats: DashboardStats;
}

/** Format a byte count into a human-readable KB/MB/GB string. */
function formatBytes(bytes: number): string {
  if (bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;

  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

/** A row of glass-card tiles summarizing the account's video/clip/storage totals. */
export function StatsWidgetRow({ stats }: StatsWidgetRowProps) {
  const tiles = [
    { label: "Total videos", value: stats.totalVideos.toLocaleString(), icon: Film },
    { label: "Total clips", value: stats.totalClips.toLocaleString(), icon: ListVideo },
    { label: "Storage used", value: formatBytes(stats.storageUsedBytes), icon: HardDrive },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {tiles.map(({ label, value, icon: Icon }) => (
        <GlassCard key={label} className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 shadow-glow">
            <Icon className="h-6 w-6 text-white" aria-hidden="true" />
          </div>
          <div>
            <p className="text-2xl font-bold tracking-tight">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
