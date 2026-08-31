import { Film, Scissors } from "lucide-react";

import { AnimatedList } from "@/components/ui/AnimatedList";
import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";
import type { ActivityItem } from "@/types";

interface ActivityFeedProps {
  items: ActivityItem[];
}

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-600",
  processing: "bg-amber-500/10 text-amber-600",
  pending: "bg-slate-500/10 text-slate-600",
  failed: "bg-red-500/10 text-red-600",
};

/** Format an ISO timestamp as a short relative time string (e.g. "5m ago"). */
function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffSeconds = Math.round(diffMs / 1000);

  if (diffSeconds < 60) {
    return "just now";
  }

  const units: Array<[string, number]> = [
    ["y", 60 * 60 * 24 * 365],
    ["mo", 60 * 60 * 24 * 30],
    ["d", 60 * 60 * 24],
    ["h", 60 * 60],
    ["m", 60],
  ];

  for (const [label, secondsInUnit] of units) {
    const value = Math.floor(diffSeconds / secondsInUnit);
    if (value >= 1) {
      return `${value}${label} ago`;
    }
  }

  return "just now";
}

/** A staggered vertical feed of recent video/clip activity. */
export function ActivityFeed({ items }: ActivityFeedProps) {
  if (items.length === 0) {
    return (
      <GlassCard className="text-center text-sm text-muted-foreground">
        No activity yet.
      </GlassCard>
    );
  }

  return (
    <AnimatedList>
      {items.map((item) => {
        const Icon = item.type === "video" ? Film : Scissors;
        const statusClassName = STATUS_STYLES[item.status] ?? STATUS_STYLES.pending;

        return (
          <GlassCard key={item.id} className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-600/10">
              <Icon className="h-5 w-5 text-violet-600" aria-hidden="true" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{item.title}</p>
              <p className="text-xs capitalize text-muted-foreground">{item.type}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium capitalize", statusClassName)}>
                {item.status}
              </span>
              <span className="text-xs text-muted-foreground">{formatRelativeTime(item.createdAt)}</span>
            </div>
          </GlassCard>
        );
      })}
    </AnimatedList>
  );
}
