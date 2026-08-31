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
        "flex cursor-pointer flex-col items-center justify-center gap-4 border-2 border-dashed border-violet-500/25 bg-card/40 py-14 text-center transition-all duration-300 hover:border-violet-500/60 hover:bg-violet-500/5 hover:shadow-glow",
        isDragActive && "border-violet-500 bg-violet-500/10 shadow-glow",
        className,
      )}
    >
      <span
        className={cn(
          "flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600/15 to-fuchsia-500/15 transition-transform duration-300",
          isDragActive && "scale-110",
        )}
      >
        <UploadCloud
          className={cn("h-8 w-8 text-violet-600 transition-transform", isDragActive && "-translate-y-0.5")}
          aria-hidden="true"
        />
      </span>
      <div>
        <p className="font-semibold text-foreground">Drag &amp; drop a video here</p>
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
