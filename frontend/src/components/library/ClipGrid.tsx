import { AnimatedList } from "@/components/ui/AnimatedList";
import { ClipCard } from "@/components/library/ClipCard";
import type { Clip } from "@/types";

interface ClipGridProps {
  clips: Clip[];
  onDelete: (id: number) => void;
  onPreview: (clip: Clip) => void;
}

/** Responsive grid of clip cards with a staggered enter animation. */
export function ClipGrid({ clips, onDelete, onPreview }: ClipGridProps) {
  return (
    <AnimatedList className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {clips.map((clip) => (
        <ClipCard key={clip.id} clip={clip} onDelete={onDelete} onPreview={onPreview} />
      ))}
    </AnimatedList>
  );
}
