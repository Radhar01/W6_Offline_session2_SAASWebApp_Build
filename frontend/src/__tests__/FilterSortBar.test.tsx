import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FilterSortBar, type ClipFilterState } from "@/components/library/FilterSortBar";

const DEFAULT_VALUE: ClipFilterState = {
  status: "all",
  sort: "created_at_desc",
};

describe("FilterSortBar", () => {
  it("renders the current status and sort selections", () => {
    render(<FilterSortBar value={DEFAULT_VALUE} onChange={vi.fn()} />);

    expect(screen.getByLabelText(/filter by status/i)).toHaveValue("all");
    expect(screen.getByLabelText(/sort order/i)).toHaveValue("created_at_desc");
  });

  it("calls onChange with the updated status, preserving the current sort", () => {
    const onChange = vi.fn();
    render(<FilterSortBar value={DEFAULT_VALUE} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText(/filter by status/i), {
      target: { value: "completed" },
    });

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ status: "completed", sort: "created_at_desc" });
  });

  it("calls onChange with the updated sort, preserving the current status", () => {
    const onChange = vi.fn();
    const value: ClipFilterState = { status: "failed", sort: "created_at_desc" };
    render(<FilterSortBar value={value} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText(/sort order/i), {
      target: { value: "start_time_asc" },
    });

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ status: "failed", sort: "start_time_asc" });
  });
});
