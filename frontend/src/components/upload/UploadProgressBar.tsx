import { motion } from "framer-motion";

interface UploadProgressBarProps {
  /** Upload completion percentage, 0-100. */
  percent: number;
}

/** Animated horizontal progress bar for upload/ingest status. */
export function UploadProgressBar({ percent }: UploadProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percent));

  return (
    <div className="w-full">
      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full overflow-hidden rounded-full bg-secondary"
      >
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-500"
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
      </div>
      <p className="mt-1 text-right text-xs text-muted-foreground">{clamped}%</p>
    </div>
  );
}
