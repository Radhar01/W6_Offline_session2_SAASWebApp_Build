import { AlertCircle, Film, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ClipGrid } from "@/components/library/ClipGrid";
import { FilterSortBar, type ClipFilterState } from "@/components/library/FilterSortBar";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageWrapper } from "@/components/layout/PageWrapper";
import type { ApiError } from "@/services/api";
import { deleteClip, listClips } from "@/services/clipService";
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

const DEFAULT_FILTER: ClipFilterState = {
  status: "all",
  sort: "created_at_desc",
};

/** Clip library: browse, filter/sort, preview, download, and delete clips. */
export function LibraryPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ClipFilterState>(DEFAULT_FILTER);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchClips = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await listClips({
        status: filter.status === "all" ? undefined : filter.status,
        sort: filter.sort,
      });
      setClips(result);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void fetchClips();
  }, [fetchClips]);

  const handleConfirmDelete = async () => {
    if (!pendingDeleteId) {
      return;
    }
    setIsDeleting(true);
    try {
      await deleteClip(pendingDeleteId);
      setPendingDeleteId(null);
      await fetchClips();
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setIsDeleting(false);
    }
  };

  const clipPendingDelete = clips.find((clip) => clip.id === pendingDeleteId);

  return (
    <PageWrapper>
      <h1 className="mb-6 text-2xl font-bold">Clip library</h1>

      <FilterSortBar value={filter} onChange={setFilter} />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <GlassCard className="flex items-center justify-center gap-3 py-12 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-violet-600" aria-hidden="true" />
          <span>Loading clips&hellip;</span>
        </GlassCard>
      ) : clips.length === 0 ? (
        <GlassCard className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
          <Film className="h-8 w-8" aria-hidden="true" />
          <p>No clips yet. Upload a video to get started.</p>
        </GlassCard>
      ) : (
        <ClipGrid clips={clips} onDelete={setPendingDeleteId} />
      )}

      <ConfirmDialog
        isOpen={pendingDeleteId !== null}
        title="Delete clip"
        message={
          clipPendingDelete
            ? `Are you sure you want to delete "${clipPendingDelete.title}"? This can't be undone.`
            : "Are you sure you want to delete this clip? This can't be undone."
        }
        confirmLabel="Delete"
        isConfirming={isDeleting}
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => setPendingDeleteId(null)}
      />
    </PageWrapper>
  );
}
