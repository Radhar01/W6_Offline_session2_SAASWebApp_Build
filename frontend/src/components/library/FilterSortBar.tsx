import type { ChangeEvent } from "react";

import type { ClipSortOption } from "@/services/clipService";
import type { ProcessingStatus } from "@/types";

export type StatusFilter = ProcessingStatus | "all";

export interface ClipFilterState {
  status: StatusFilter;
  sort: ClipSortOption;
}

interface FilterSortBarProps {
  value: ClipFilterState;
  onChange: (next: ClipFilterState) => void;
}

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

const SORT_OPTIONS: { value: ClipSortOption; label: string }[] = [
  { value: "created_at_desc", label: "Newest first" },
  { value: "created_at_asc", label: "Oldest first" },
  { value: "start_time_asc", label: "Start time (earliest)" },
  { value: "start_time_desc", label: "Start time (latest)" },
];

const selectClassName =
  "rounded-xl border-2 border-input bg-background px-4 py-2 text-sm text-foreground outline-none transition-colors focus:border-ring";

/** Status filter + sort order controls for the clip library. */
export function FilterSortBar({ value, onChange }: FilterSortBarProps) {
  const handleStatusChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...value, status: event.target.value as StatusFilter });
  };

  const handleSortChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...value, sort: event.target.value as ClipSortOption });
  };

  return (
    <div className="mb-6 flex flex-wrap items-center gap-3">
      <div>
        <label htmlFor="clip-status-filter" className="sr-only">
          Filter by status
        </label>
        <select
          id="clip-status-filter"
          value={value.status}
          onChange={handleStatusChange}
          className={selectClassName}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="clip-sort-order" className="sr-only">
          Sort order
        </label>
        <select
          id="clip-sort-order"
          value={value.sort}
          onChange={handleSortChange}
          className={selectClassName}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
