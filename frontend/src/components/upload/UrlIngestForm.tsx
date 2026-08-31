import type { FormEvent } from "react";
import { useState } from "react";

import { AnimatedInput } from "@/components/ui/AnimatedInput";
import { GradientButton } from "@/components/ui/GradientButton";

interface UrlIngestFormProps {
  onSubmit: (url: string) => void;
  isSubmitting?: boolean;
}

/** Validate that a string is a well-formed absolute http(s) URL. */
function isValidVideoUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

/** Form for ingesting a video by pasting a source URL (e.g. a YouTube link). */
export function UrlIngestForm({ onSubmit, isSubmitting = false }: UrlIngestFormProps) {
  const [url, setUrl] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = url.trim();
    if (!trimmed) {
      setValidationError("Enter a video URL.");
      return;
    }
    if (!isValidVideoUrl(trimmed)) {
      setValidationError("Enter a valid http(s) URL.");
      return;
    }

    setValidationError(null);
    onSubmit(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <AnimatedInput
        label="Video URL"
        name="sourceUrl"
        type="url"
        placeholder="https://youtube.com/watch?v=..."
        value={url}
        onChange={(event) => {
          setUrl(event.target.value);
          if (validationError) {
            setValidationError(null);
          }
        }}
        error={validationError ?? undefined}
        disabled={isSubmitting}
      />
      <GradientButton type="submit" disabled={isSubmitting || !url.trim()}>
        {isSubmitting ? "Submitting..." : "Import from URL"}
      </GradientButton>
    </form>
  );
}
