import { AlertCircle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { GlassCard } from "@/components/ui/GlassCard";
import { GradientButton } from "@/components/ui/GradientButton";
import { AnimatedInput } from "@/components/ui/AnimatedInput";
import { PageWrapper } from "@/components/layout/PageWrapper";
import type { ApiError } from "@/services/api";
import { getClip, getDownloadUrl, getPreviewUrl, updateClip } from "@/services/clipService";
import type { Clip } from "@/types";

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
 * Single-clip detail view: preview player, inline-editable metadata, and
 * download. Wired up to GET/PUT `/api/v1/clips/:id`.
 */
export function ClipDetailPage() {
  const { clipId: clipIdParam } = useParams<{ clipId: string }>();
  const clipId = clipIdParam ? Number(clipIdParam) : undefined;

  const [clip, setClip] = useState<Clip | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [thumbnailUrl, setThumbnailUrl] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchClip = useCallback(async () => {
    if (!clipId) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await getClip(clipId);
      setClip(result);
      setTitle(result.title);
      setThumbnailUrl(result.thumbnailUrl ?? "");
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [clipId]);

  useEffect(() => {
    void fetchClip();
  }, [fetchClip]);

  const hasChanges = clip !== null && (title !== clip.title || thumbnailUrl !== (clip.thumbnailUrl ?? ""));

  const handleSave = async () => {
    if (!clipId || !hasChanges) {
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateClip(clipId, {
        title,
        thumbnailUrl: thumbnailUrl || undefined,
      });
      setClip(updated);
      setTitle(updated.title);
      setThumbnailUrl(updated.thumbnailUrl ?? "");
    } catch (err) {
      setSaveError(toErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <PageWrapper>
        <h1 className="mb-6 text-2xl font-bold">Clip details</h1>
        <GlassCard className="flex max-w-xl items-center gap-4">
          <Loader2 className="h-6 w-6 animate-spin text-violet-600" aria-hidden="true" />
          <span className="text-muted-foreground">Loading clip&hellip;</span>
        </GlassCard>
      </PageWrapper>
    );
  }

  if (error || !clip) {
    return (
      <PageWrapper>
        <h1 className="mb-6 text-2xl font-bold">Clip details</h1>
        <GlassCard className="max-w-xl">
          <div className="flex items-start gap-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error ?? "Clip not found."}</span>
          </div>
        </GlassCard>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <h1 className="mb-6 text-2xl font-bold">Clip details</h1>

      <GlassCard className="max-w-xl">
        <div className="mx-auto w-full max-w-[360px] overflow-hidden rounded-xl bg-black">
          <video
            key={clip.id}
            controls
            className="aspect-[9/16] w-full"
            src={getPreviewUrl(clip.id)}
            poster={clip.thumbnailUrl}
          />
        </div>

        <div className="mt-6 flex flex-col gap-4">
          <AnimatedInput
            label="Title"
            name="title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            onBlur={() => void handleSave()}
          />
          <AnimatedInput
            label="Thumbnail URL"
            name="thumbnailUrl"
            value={thumbnailUrl}
            onChange={(event) => setThumbnailUrl(event.target.value)}
            onBlur={() => void handleSave()}
            placeholder="https://…"
          />

          {saveError && (
            <div className="flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{saveError}</span>
            </div>
          )}

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <dt>Status</dt>
            <dd className="capitalize text-foreground">{clip.status}</dd>
            <dt>Duration</dt>
            <dd className="text-foreground">{Math.round(clip.endTime - clip.startTime)}s</dd>
            <dt>Aspect ratio</dt>
            <dd className="text-foreground">{clip.aspectRatio}</dd>
          </dl>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <a
            href={getDownloadUrl(clip.id)}
            download
            className="inline-flex items-center justify-center rounded-full border border-input px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
          >
            Download clip
          </a>
          <GradientButton type="button" disabled={!hasChanges || isSaving} onClick={() => void handleSave()}>
            {isSaving ? "Saving…" : "Save changes"}
          </GradientButton>
        </div>
      </GlassCard>
    </PageWrapper>
  );
}
