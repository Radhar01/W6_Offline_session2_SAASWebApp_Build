import { Film } from "lucide-react";
import { Link } from "react-router-dom";

import { AnimatedList } from "@/components/ui/AnimatedList";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientButton } from "@/components/ui/GradientButton";
import { cn } from "@/lib/utils";
import type { Clip } from "@/types";

interface ClipPreviewListProps {
  clips: Clip[];
  className?: string;
}

/**
 * Lightweight "here's what got generated" preview shown while/after a
 * video's clips are produced. The full browse/edit experience lives in the
 * library module (`/library`); this component intentionally stays minimal.
 */
export function ClipPreviewList({ clips, className }: ClipPreviewListProps) {
  if (clips.length === 0) {
    return null;
  }

  return (
    <div className={cn("flex flex-col gap-4 border-t border-border/60 pt-6", className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold tracking-tight">
          Generated <span className="text-gradient">clips</span>{" "}
          <span className="text-muted-foreground">({clips.length})</span>
        </h2>
        <Link to="/library">
          <GradientButton type="button" className="px-4 py-2 text-sm">
            View in library
          </GradientButton>
        </Link>
      </div>

      <AnimatedList className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {clips.map((clip) => (
          <GlassCard key={clip.id} className="flex flex-col gap-3 p-4">
            <div className="flex aspect-[9/16] items-center justify-center overflow-hidden rounded-xl bg-secondary">
              {clip.thumbnailUrl ? (
                <img
                  src={clip.thumbnailUrl}
                  alt={clip.title}
                  className="h-full w-full object-cover"
                />
              ) : (
                <Film className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
              )}
            </div>
            <div>
              <p className="truncate font-medium">{clip.title}</p>
              <p className="text-sm text-muted-foreground">
                {clip.aspectRatio} &middot; {clip.status}
              </p>
            </div>
          </GlassCard>
        ))}
      </AnimatedList>
    </div>
  );
}
