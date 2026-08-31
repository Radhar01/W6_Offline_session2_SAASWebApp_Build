import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { FileDropzone } from "@/components/upload/FileDropzone";
import { UploadProgressBar } from "@/components/upload/UploadProgressBar";
import { UrlIngestForm } from "@/components/upload/UrlIngestForm";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PipelineStages } from "@/components/processing/PipelineStages";
import { useVideoUpload } from "@/hooks/useVideoUpload";
import { cn } from "@/lib/utils";

type IngestTab = "file" | "url";

const TABS: { key: IngestTab; label: string }[] = [
  { key: "file", label: "Upload a file" },
  { key: "url", label: "Or paste a URL" },
];

/**
 * Video ingestion page: upload a file or import from a URL, then route to
 * the processing page once the backend has accepted the video.
 */
export function UploadPage() {
  const navigate = useNavigate();
  const { uploadFile, submitUrl, progress, isUploading, error } = useVideoUpload();
  const [activeTab, setActiveTab] = useState<IngestTab>("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelected = async (file: File) => {
    setSelectedFile(file);
    try {
      const video = await uploadFile(file);
      navigate(`/videos/${video.id}/processing`);
    } catch {
      // Error state is already captured by useVideoUpload; nothing further to do here.
    }
  };

  const handleUrlSubmit = async (url: string) => {
    try {
      const video = await submitUrl(url);
      navigate(`/videos/${video.id}/processing`);
    } catch {
      // Error state is already captured by useVideoUpload; nothing further to do here.
    }
  };

  return (
    <PageWrapper>
      <h1 className="mb-6 text-2xl font-bold">Upload a video</h1>

      {(isUploading || error) && (
        <GlassCard className="mb-6 max-w-xl">
          <PipelineStages
            currentStage={activeTab === "url" ? "downloading" : "upload"}
            failed={Boolean(error)}
          />
        </GlassCard>
      )}

      <GlassCard className="max-w-xl">
        <div className="mb-6 flex gap-1 rounded-full bg-secondary p-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              disabled={isUploading}
              className={cn(
                "flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                activeTab === tab.key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "file" ? (
          <div className="flex flex-col gap-4">
            <FileDropzone onFileSelected={handleFileSelected} />
            {selectedFile && (
              <p className="text-sm text-muted-foreground">Selected: {selectedFile.name}</p>
            )}
            {isUploading && <UploadProgressBar percent={progress} />}
          </div>
        ) : (
          <UrlIngestForm onSubmit={handleUrlSubmit} isSubmitting={isUploading} />
        )}

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
      </GlassCard>
    </PageWrapper>
  );
}
