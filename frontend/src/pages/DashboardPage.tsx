import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Film } from "lucide-react";

import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { StatsWidgetRow } from "@/components/dashboard/StatsWidgetRow";
import { GlassCard } from "@/components/ui/GlassCard";
import { GradientButton } from "@/components/ui/GradientButton";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { getDashboardStats, getRecentActivity } from "@/services/dashboardService";
import type { ActivityItem, DashboardStats } from "@/types";

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      try {
        const [statsResult, activityResult] = await Promise.all([getDashboardStats(), getRecentActivity()]);
        if (!isMounted) {
          return;
        }
        setStats(statsResult);
        setActivity(activityResult);
      } catch {
        if (isMounted) {
          setError("Couldn't load your dashboard. Please try again shortly.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <PageWrapper>
        <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Loading your dashboard...</p>
      </PageWrapper>
    );
  }

  if (error || !stats) {
    return (
      <PageWrapper>
        <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
        <GlassCard className="text-center text-sm text-destructive">
          {error ?? "Something went wrong."}
        </GlassCard>
      </PageWrapper>
    );
  }

  if (stats.totalVideos === 0) {
    return (
      <PageWrapper>
        <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
        <GlassCard className="flex flex-col items-center gap-4 py-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-violet-600/10">
            <Film className="h-8 w-8 text-violet-600" aria-hidden="true" />
          </div>
          <div>
            <p className="text-lg font-semibold">No videos yet</p>
            <p className="text-sm text-muted-foreground">
              Upload your first video to start generating clips.
            </p>
          </div>
          <Link to="/upload">
            <GradientButton>Upload a video</GradientButton>
          </Link>
        </GlassCard>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
      <div className="flex flex-col gap-6">
        <StatsWidgetRow stats={stats} />
        <div>
          <h2 className="mb-3 text-lg font-semibold">Recent activity</h2>
          <ActivityFeed items={activity} />
        </div>
      </div>
    </PageWrapper>
  );
}
