import { Check, Loader2, X } from "lucide-react";

import { cn } from "@/lib/utils";

export type PipelineStage = "upload" | "downloading" | "processing" | "generated";

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "downloading", label: "Downloading" },
  { key: "processing", label: "Processing" },
  { key: "generated", label: "Generated" },
];

interface PipelineStagesProps {
  /** The stage currently in progress (or, once done, the final "generated" stage). */
  currentStage: PipelineStage;
  /** Marks the current stage as failed instead of active/complete. */
  failed?: boolean;
  className?: string;
}

/**
 * Horizontal step tracker for the ingest→clip pipeline: Upload → Downloading
 * → Processing → Generated. Steps before `currentStage` render as complete,
 * `currentStage` itself renders as active (or failed), and later steps
 * render as pending.
 */
export function PipelineStages({ currentStage, failed = false, className }: PipelineStagesProps) {
  const currentIndex = STAGES.findIndex((stage) => stage.key === currentStage);
  const isFinalStage = currentStage === "generated" && !failed;

  return (
    <div className={cn("flex items-center", className)}>
      {STAGES.map((stage, index) => {
        const isComplete = index < currentIndex || (index === currentIndex && isFinalStage);
        const isActive = index === currentIndex && !isComplete;
        const isFailed = isActive && failed;

        return (
          <div key={stage.key} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center gap-2">
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors",
                  isComplete && "border-emerald-500 bg-emerald-500 text-white",
                  isActive && !isFailed && "border-violet-600 bg-violet-50 text-violet-600",
                  isFailed && "border-red-500 bg-red-50 text-red-500",
                  !isComplete && !isActive && "border-muted bg-muted text-muted-foreground",
                )}
              >
                {isComplete ? (
                  <Check className="h-4 w-4" aria-hidden="true" />
                ) : isFailed ? (
                  <X className="h-4 w-4" aria-hidden="true" />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  "text-xs font-medium",
                  isComplete && "text-emerald-600",
                  isActive && !isFailed && "text-violet-600",
                  isFailed && "text-red-500",
                  !isComplete && !isActive && "text-muted-foreground",
                )}
              >
                {stage.label}
              </span>
            </div>
            {index < STAGES.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-0.5 flex-1 rounded-full transition-colors",
                  index < currentIndex ? "bg-emerald-500" : "bg-muted",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
