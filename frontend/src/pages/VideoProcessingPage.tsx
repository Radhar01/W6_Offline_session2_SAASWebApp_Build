import { AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { ClipPreviewList } from "@/components/processing/ClipPreviewList";
import { PipelineStages } from "@/components/processing/PipelineStages";
import { ProgressIndicator } from "@/components/processing/ProgressIndicator";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientButton } from "@/components/ui/GradientButton";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useClipGenerationStatus } from "@/hooks/useClipGenerationStatus";
import type { ApiError } from "@/services/api";
import { getVideo, triggerClipGeneration } from "@/services/clipGenerationService";

/**
 * Shows processing status for a video while it's being segmented into clips,
 * polling the backend and rendering progress + a lightweight clip preview
 * as clips are produced.
 */
export function VideoProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const videoId = id ? Number(id) : undefined;
  const { video, clips, error: pollError } = useClipGenerationStatus(videoId);

  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [isTriggering, setIsTriggering] = useState(false);
  const hasTriggeredRef = useRef(false);

  const startGeneration = useCallback(async () => {
    if (!videoId) {
      return;
    }
    setIsTriggering(true);
    setTriggerError(null);
    try {
      await triggerClipGeneration(videoId);
    } catch (err) {
      const message =
        typeof (err as Partial<ApiError>)?.message === "string"
          ? (err as ApiError).message
          : "Failed to start clip generation.";
      setTriggerError(message);
    } finally {
      setIsTriggering(false);
    }
  }, [videoId]);

  // Kick off generation exactly once, and only if the video hasn't already
  // started/finished processing (e.g. a page refresh mid-flight).
  useEffect(() => {
    if (!videoId || hasTriggeredRef.current) {
      return;
    }
    hasTriggeredRef.current = true;

    void (async () => {
      try {
        const currentVideo = await getVideo(videoId);
        if (currentVideo.status === "pending") {
          await startGeneration();
        }
      } catch (err) {
        const message =
          typeof (err as Partial<ApiError>)?.message === "string"
            ? (err as ApiError).message
            : "Failed to load video.";
        setTriggerError(message);
      }
    })();
  }, [videoId, startGeneration]);

  const handleRetry = () => {
    hasTriggeredRef.current = true;
    void startGeneration();
  };

  const hasFailed = video?.status === "failed" || Boolean(triggerError);
  const errorMessage = triggerError ?? pollError;

  return (
    <PageWrapper>
      <h1 className="mb-6 text-3xl font-extrabold tracking-tight">Processing video</h1>

      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <GlassCard>
          <PipelineStages
            currentStage={video?.status === "completed" ? "generated" : "processing"}
            failed={hasFailed}
          />
        </GlassCard>

        <GlassCard className="flex items-center justify-between gap-4">
          <ProgressIndicator status={hasFailed ? "failed" : (video?.status ?? "pending")} />
          <span className="shrink-0 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-muted-foreground">
            Video #{id ?? "?"}
          </span>
        </GlassCard>

        {hasFailed && (
          <GlassCard className="flex items-center justify-between gap-4 border-red-200 bg-red-50/60">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 shrink-0 text-red-500" aria-hidden="true" />
              <div>
                <p className="font-medium text-red-700">Clip generation failed</p>
                {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
              </div>
            </div>
            <GradientButton type="button" onClick={handleRetry} disabled={isTriggering}>
              {isTriggering ? "Retrying…" : "Retry"}
            </GradientButton>
          </GlassCard>
        )}

        <ClipPreviewList clips={clips} />
      </div>
    </PageWrapper>
  );
}
