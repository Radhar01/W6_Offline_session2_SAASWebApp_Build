import { useEffect, useRef, useState } from "react";

import type { ApiError } from "@/services/api";
import { getClipsForVideo, getVideo } from "@/services/clipGenerationService";
import type { Clip, Video } from "@/types";

const POLL_INTERVAL_MS = 2000;

interface UseClipGenerationStatusResult {
  video: Video | null;
  clips: Clip[];
  isProcessing: boolean;
  error: string | null;
}

/**
 * Polls a video's status and its clips while generation is in flight.
 *
 * Polling starts immediately and continues every ~2s as long as the video's
 * status is "pending" or "processing". It stops automatically once the
 * status settles to "completed" or "failed", and is always cleaned up on
 * unmount or when `videoId` changes.
 */
export function useClipGenerationStatus(videoId: number | undefined): UseClipGenerationStatusResult {
  const [video, setVideo] = useState<Video | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [isProcessing, setIsProcessing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tracks the latest videoId so an in-flight poll from a stale render
  // can't clobber state after the id changes or the component unmounts.
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    if (!videoId) {
      setIsProcessing(false);
      return;
    }

    const poll = async (): Promise<void> => {
      try {
        const [latestVideo, latestClips] = await Promise.all([
          getVideo(videoId),
          getClipsForVideo(videoId),
        ]);

        if (!isMountedRef.current) {
          return;
        }

        setVideo(latestVideo);
        setClips(latestClips);
        setError(null);

        const stillGoing = latestVideo.status === "pending" || latestVideo.status === "processing";
        setIsProcessing(stillGoing);

        if (!stillGoing && intervalId) {
          clearInterval(intervalId);
        }
      } catch (err) {
        if (!isMountedRef.current) {
          return;
        }
        const message =
          typeof (err as Partial<ApiError>)?.message === "string"
            ? (err as ApiError).message
            : "Failed to load processing status.";
        setError(message);
      }
    };

    void poll();
    const intervalId = setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);

    return () => {
      isMountedRef.current = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [videoId]);

  return { video, clips, isProcessing, error };
}
