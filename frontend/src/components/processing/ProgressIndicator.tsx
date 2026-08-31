import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ProcessingStatus } from "@/types";

interface ProgressIndicatorProps {
  status: ProcessingStatus;
  className?: string;
}

const STATUS_COPY: Record<ProcessingStatus, { title: string; description: string }> = {
  pending: {
    title: "Queued",
    description: "Waiting for a worker to pick up this video…",
  },
  processing: {
    title: "Generating clips",
    description: "Segmenting your video and generating clips…",
  },
  completed: {
    title: "Done",
    description: "Clip generation finished successfully.",
  },
  failed: {
    title: "Generation failed",
    description: "Something went wrong while generating clips.",
  },
};

/** Animated status indicator reflecting a video's processing lifecycle. */
export function ProgressIndicator({ status, className }: ProgressIndicatorProps) {
  const copy = STATUS_COPY[status];

  return (
    <div className={cn("flex items-center gap-4", className)}>
      <div className="relative flex h-12 w-12 shrink-0 items-center justify-center">
        <AnimatePresence mode="wait">
          {status === "completed" ? (
            <motion.div
              key="completed"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.6 }}
            >
              <CheckCircle2 className="h-8 w-8 text-emerald-500" aria-hidden="true" />
            </motion.div>
          ) : status === "failed" ? (
            <motion.div
              key="failed"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.6 }}
            >
              <XCircle className="h-8 w-8 text-red-500" aria-hidden="true" />
            </motion.div>
          ) : (
            <motion.div
              key="spinning"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, rotate: 360 }}
              exit={{ opacity: 0 }}
              transition={{ rotate: { duration: 1, repeat: Infinity, ease: "linear" } }}
            >
              <Loader2 className="h-8 w-8 text-violet-600" aria-hidden="true" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div>
        <p className="font-medium">{copy.title}</p>
        <p className="text-sm text-muted-foreground">{copy.description}</p>
      </div>
    </div>
  );
}
