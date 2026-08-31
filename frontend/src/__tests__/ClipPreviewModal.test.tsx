import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ClipPreviewModal } from "@/components/library/ClipPreviewModal";
import type { Clip } from "@/types";

vi.mock("@/services/clipService", () => ({
  getPreviewUrl: (id: number) => `https://api.test/clips/${id}/preview`,
}));

function makeClip(overrides: Partial<Clip> = {}): Clip {
  return {
    id: 1,
    videoId: 10,
    startTime: 0,
    endTime: 60,
    title: "My Awesome Clip",
    thumbnailUrl: undefined,
    filePath: "clips/1.mp4",
    aspectRatio: "9:16",
    status: "completed",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderModal(clip: Clip | null, onClose = vi.fn()) {
  render(
    <MemoryRouter>
      <ClipPreviewModal clip={clip} onClose={onClose} />
    </MemoryRouter>,
  );
  return { onClose };
}

describe("ClipPreviewModal", () => {
  it("renders nothing when clip is null", () => {
    renderModal(null);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the video player and title when a clip is given", () => {
    renderModal(makeClip());

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByText("My Awesome Clip")).toBeInTheDocument();

    const video = dialog.querySelector("video");
    expect(video).toHaveAttribute("src", "https://api.test/clips/1/preview");
  });

  it("calls onClose when the close (X) button is clicked", () => {
    const { onClose } = renderModal(makeClip());

    fireEvent.click(screen.getByLabelText("Close preview"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", () => {
    const { onClose } = renderModal(makeClip());

    fireEvent.click(screen.getByRole("presentation"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when the dialog content itself is clicked", () => {
    const { onClose } = renderModal(makeClip());

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when the Escape key is pressed", () => {
    const { onClose } = renderModal(makeClip());

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
