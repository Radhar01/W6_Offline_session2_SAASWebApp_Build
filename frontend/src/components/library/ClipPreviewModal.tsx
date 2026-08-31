import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";
import { Link } from "react-router-dom";

import { getPreviewUrl } from "@/services/clipService";
import type { Clip } from "@/types";

interface ClipPreviewModalProps {
  /** The clip to preview, or `null` to keep the modal closed. */
  clip: Clip | null;
  onClose: () => void;
}

/**
 * Popup video player for previewing a clip without leaving the library grid.
 * Closes on backdrop click, the X button, or Escape.
 */
export function ClipPreviewModal({ clip, onClose }: ClipPreviewModalProps) {
  useEffect(() => {
    if (!clip) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [clip, onClose]);

  return (
    <AnimatePresence>
      {clip && (
        <motion.div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={`Preview: ${clip.title}`}
            className="relative w-full max-w-sm"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.15 }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="relative overflow-hidden rounded-2xl bg-black shadow-glow-lg">
              <button
                type="button"
                onClick={onClose}
                aria-label="Close preview"
                className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur-sm transition-colors hover:bg-black/80"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>

              <video
                key={clip.id}
                controls
                autoPlay
                className="aspect-[9/16] max-h-[80vh] w-full"
                src={getPreviewUrl(clip.id)}
                poster={clip.thumbnailUrl}
              />
            </div>

            <div className="mt-3 flex items-center justify-between gap-3 text-white">
              <p className="truncate font-medium">{clip.title}</p>
              <Link
                to={`/library/${clip.id}`}
                onClick={onClose}
                className="shrink-0 text-sm font-medium text-violet-300 underline-offset-4 hover:underline"
              >
                Edit details
              </Link>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
