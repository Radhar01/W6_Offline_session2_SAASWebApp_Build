import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LibraryPage } from "@/pages/LibraryPage";

const { listClipsMock, deleteClipMock } = vi.hoisted(() => ({
  listClipsMock: vi.fn(),
  deleteClipMock: vi.fn(),
}));

vi.mock("@/services/clipService", () => ({
  listClips: listClipsMock,
  deleteClip: deleteClipMock,
}));

function renderLibraryPage() {
  return render(
    <MemoryRouter>
      <LibraryPage />
    </MemoryRouter>,
  );
}

describe("LibraryPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state before clips resolve", () => {
    listClipsMock.mockReturnValue(new Promise(() => {})); // never resolves

    renderLibraryPage();

    expect(screen.getByText(/loading clips/i)).toBeInTheDocument();
  });

  it("shows the empty state once loading finishes with no clips", async () => {
    listClipsMock.mockResolvedValue([]);

    renderLibraryPage();

    await waitFor(() => {
      expect(screen.getByText(/no clips yet/i)).toBeInTheDocument();
    });
    expect(listClipsMock).toHaveBeenCalledWith({ status: undefined, sort: "created_at_desc" });
  });

  it("shows an error message when fetching clips fails", async () => {
    listClipsMock.mockRejectedValue({ message: "Network error", status: 500 });

    renderLibraryPage();

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});
