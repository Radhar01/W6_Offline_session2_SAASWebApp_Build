import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatsWidgetRow } from "@/components/dashboard/StatsWidgetRow";
import type { DashboardStats } from "@/types";

describe("StatsWidgetRow", () => {
  it("renders total videos and total clips as plain counts", () => {
    const stats: DashboardStats = {
      totalVideos: 12,
      totalClips: 340,
      storageUsedBytes: 0,
    };
    render(<StatsWidgetRow stats={stats} />);

    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("340")).toBeInTheDocument();
    expect(screen.getByText("Total videos")).toBeInTheDocument();
    expect(screen.getByText("Total clips")).toBeInTheDocument();
  });

  it("formats zero bytes as '0 B'", () => {
    const stats: DashboardStats = { totalVideos: 0, totalClips: 0, storageUsedBytes: 0 };
    render(<StatsWidgetRow stats={stats} />);
    expect(screen.getByText("0 B")).toBeInTheDocument();
  });

  it("formats bytes under 1 KB as whole bytes", () => {
    const stats: DashboardStats = { totalVideos: 0, totalClips: 0, storageUsedBytes: 512 };
    render(<StatsWidgetRow stats={stats} />);
    expect(screen.getByText("512 B")).toBeInTheDocument();
  });

  it("formats kilobyte-scale values with one decimal place", () => {
    const stats: DashboardStats = { totalVideos: 0, totalClips: 0, storageUsedBytes: 2048 };
    render(<StatsWidgetRow stats={stats} />);
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });

  it("formats megabyte-scale values", () => {
    const stats: DashboardStats = {
      totalVideos: 0,
      totalClips: 0,
      storageUsedBytes: 5 * 1024 * 1024,
    };
    render(<StatsWidgetRow stats={stats} />);
    expect(screen.getByText("5.0 MB")).toBeInTheDocument();
  });

  it("formats gigabyte-scale values", () => {
    const stats: DashboardStats = {
      totalVideos: 0,
      totalClips: 0,
      storageUsedBytes: 1.5 * 1024 * 1024 * 1024,
    };
    render(<StatsWidgetRow stats={stats} />);
    expect(screen.getByText("1.5 GB")).toBeInTheDocument();
  });
});
