import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ClipCard } from "@/components/library/ClipCard";
import type { Clip } from "@/types";

vi.mock("@/services/clipService", () => ({
  getDownloadUrl: (id: number) => `https://api.test/clips/${id}/download`,
}));

function makeClip(overrides: Partial<Clip> = {}): Clip {
  return {
    id: 1,
    videoId: 10,
    startTime: 0,
    endTime: 95, // -> 1:35
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

function renderClipCard(clip: Clip, onDelete = vi.fn()) {
  render(
    <MemoryRouter>
      <ClipCard clip={clip} onDelete={onDelete} />
    </MemoryRouter>,
  );
  return { onDelete };
}

describe("ClipCard", () => {
  it("renders the clip title, formatted duration, and status", () => {
    renderClipCard(makeClip());

    expect(screen.getByText("My Awesome Clip")).toBeInTheDocument();
    expect(screen.getByText("1:35")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("formats a sub-minute duration correctly", () => {
    renderClipCard(makeClip({ startTime: 0, endTime: 9 }));
    expect(screen.getByText("0:09")).toBeInTheDocument();
  });

  it("calls onDelete with the clip id when the delete button is clicked", () => {
    const clip = makeClip({ id: 42 });
    const { onDelete } = renderClipCard(clip);

    fireEvent.click(screen.getByLabelText(`Delete ${clip.title}`));

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledWith(42);
  });

  it("does not call onDelete on render", () => {
    const { onDelete } = renderClipCard(makeClip());
    expect(onDelete).not.toHaveBeenCalled();
  });
});
