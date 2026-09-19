"use client";

import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";

interface PullToRefreshIndicatorProps {
  pullDistance: number;
  refreshing: boolean;
  threshold?: number;
}

export function PullToRefreshIndicator({
  pullDistance,
  refreshing,
  threshold = 80,
}: PullToRefreshIndicatorProps) {
  if (pullDistance === 0 && !refreshing) return null;

  const progress = Math.min(1, pullDistance / threshold);
  const ready = pullDistance >= threshold;

  return (
    <div
      className="flex items-center justify-center overflow-hidden transition-all duration-200"
      style={{ height: refreshing ? 48 : pullDistance }}
    >
      <div
        className={cn(
          "flex items-center gap-2 rounded-full px-4 py-1.5 text-label font-medium transition-all",
          ready || refreshing
            ? "bg-accent/15 text-accent"
            : "bg-border/30 text-text-muted"
        )}
      >
        <RefreshCw
          className={cn(
            "h-4 w-4 transition-transform duration-300",
            refreshing && "animate-spin"
          )}
          style={{
            transform: refreshing ? undefined : `rotate(${progress * 360}deg)`,
          }}
        />
        <span>
          {refreshing
            ? "Refreshing..."
            : ready
              ? "Release to refresh"
              : "Pull to refresh"}
        </span>
      </div>
    </div>
  );
}
