import { Download, Film, Play, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { GlassCard } from "@/components/ui/GlassCard";
import { getDownloadUrl } from "@/services/clipService";
import { cn } from "@/lib/utils";
import type { Clip, ProcessingStatus } from "@/types";

interface ClipCardProps {
  clip: Clip;
  onDelete: (id: number) => void;
}

const STATUS_STYLES: Record<ProcessingStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  processing: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  completed: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  failed: "bg-destructive/15 text-destructive",
};

/** Format a duration in seconds as `m:ss`. */
function formatDuration(seconds: number): string {
  const wholeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(wholeSeconds / 60);
  const remainder = wholeSeconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

/** A single clip's card in the library grid: thumbnail, metadata, and actions. */
export function ClipCard({ clip, onDelete }: ClipCardProps) {
  const duration = formatDuration(clip.endTime - clip.startTime);
  const detailPath = `/library/${clip.id}`;

  return (
    <GlassCard className="flex flex-col gap-4 p-4">
      <Link to={detailPath} className="block">
        <div className="relative aspect-[9/16] w-full overflow-hidden rounded-xl bg-secondary">
          {clip.thumbnailUrl ? (
            <img
              src={clip.thumbnailUrl}
              alt={clip.title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Film className="h-8 w-8" aria-hidden="true" />
            </div>
          )}
          <span className="absolute bottom-2 right-2 rounded-full bg-black/70 px-2 py-0.5 text-xs font-medium text-white">
            {duration}
          </span>
        </div>

        <div className="mt-3 flex items-start justify-between gap-2">
          <h3 className="truncate font-medium" title={clip.title}>
            {clip.title}
          </h3>
          <span
            className={cn(
              "shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
              STATUS_STYLES[clip.status],
            )}
          >
            {clip.status}
          </span>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        <Link
          to={detailPath}
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full border border-input px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
        >
          <Play className="h-4 w-4" aria-hidden="true" />
          Preview
        </Link>
        <a
          href={getDownloadUrl(clip.id)}
          download
          className="inline-flex items-center justify-center rounded-full border border-input p-2 text-foreground transition-colors hover:bg-secondary"
          aria-label={`Download ${clip.title}`}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
        </a>
        <button
          type="button"
          onClick={() => onDelete(clip.id)}
          className="inline-flex items-center justify-center rounded-full border border-input p-2 text-destructive transition-colors hover:bg-destructive/10"
          aria-label={`Delete ${clip.title}`}
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </GlassCard>
  );
}
