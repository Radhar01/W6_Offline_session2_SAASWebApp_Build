import { useCallback, useState } from "react";

import type { ApiError } from "@/services/api";
import { submitVideoUrl, uploadVideo } from "@/services/videoService";
import type { Video } from "@/types";

interface UseVideoUploadResult {
  uploadFile: (file: File) => Promise<Video>;
  submitUrl: (url: string) => Promise<Video>;
  progress: number;
  isUploading: boolean;
  error: string | null;
}

/** Type guard for the normalized `ApiError` shape produced by the axios interceptor. */
function isApiError(value: unknown): value is ApiError {
  return typeof value === "object" && value !== null && "message" in value;
}

function toErrorMessage(err: unknown): string {
  if (isApiError(err)) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "An unexpected error occurred.";
}

/**
 * Drives video ingestion (file upload or URL import), exposing upload
 * progress and error state so pages don't have to manage it themselves.
 */
export function useVideoUpload(): UseVideoUploadResult {
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = useCallback(async (file: File): Promise<Video> => {
    setIsUploading(true);
    setProgress(0);
    setError(null);
    try {
      const video = await uploadVideo(file, setProgress);
      return video;
    } catch (err) {
      const message = toErrorMessage(err);
      setError(message);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const submitUrl = useCallback(async (url: string): Promise<Video> => {
    setIsUploading(true);
    setProgress(0);
    setError(null);
    try {
      const video = await submitVideoUrl(url);
      setProgress(100);
      return video;
    } catch (err) {
      const message = toErrorMessage(err);
      setError(message);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return { uploadFile, submitUrl, progress, isUploading, error };
}
