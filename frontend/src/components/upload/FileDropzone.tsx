import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { DragEvent, KeyboardEvent } from "react";

import { GlassCard } from "@/components/ui/GlassCard";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  onFileSelected: (file: File) => void;
  /** Optional override for the accepted MIME pattern. Defaults to any video type. */
  accept?: string;
  className?: string;
}

/** Drag-and-drop (or click-to-browse) area restricted to video files. */
export function FileDropzone({ onFileSelected, accept = "video/*", className }: FileDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file && file.type.startsWith("video/")) {
      onFileSelected(file);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(false);
    handleFiles(event.dataTransfer.files);
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <GlassCard
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed border-input bg-card/40 py-12 text-center transition-colors hover:border-violet-500 hover:bg-card/60",
        isDragActive && "border-violet-500 bg-violet-500/10",
        className,
      )}
    >
      <UploadCloud
        className={cn("h-10 w-10 text-muted-foreground transition-colors", isDragActive && "text-violet-600")}
        aria-hidden="true"
      />
      <div>
        <p className="font-medium text-foreground">Drag &amp; drop a video here</p>
        <p className="text-sm text-muted-foreground">or click to browse your files</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />
    </GlassCard>
  );
}
