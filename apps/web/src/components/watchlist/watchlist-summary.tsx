"use client";

import { cn } from "@/lib/cn";
import type { LivePrice } from "@/lib/api-types";

interface WatchlistSummaryProps {
  prices: Record<string, LivePrice>;
  count: number;
}

function compactVolume(v: number): string {
  if (v >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
  return v.toString();
}

/** Same segmented strip as the dashboard KPIs: neutral numbers, colour only where there is a direction. */
export function WatchlistSummary({ prices, count }: WatchlistSummaryProps) {
  const priceList = Object.values(prices);
  const gainers = priceList.filter((p) => (p.change_pct ?? 0) > 0).length;
  const losers = priceList.filter((p) => (p.change_pct ?? 0) < 0).length;
  const totalVolume = priceList.reduce((sum, p) => sum + (p.volume ?? 0), 0);

  const cells = [
    { label: "Watching", value: count.toString(), tone: "text-text-primary" },
    { label: "Gainers", value: gainers.toString(), tone: gainers > 0 ? "text-bullish" : "text-text-primary" },
    { label: "Losers", value: losers.toString(), tone: losers > 0 ? "text-bearish" : "text-text-primary" },
    { label: "Total volume", value: compactVolume(totalVolume), tone: "text-text-primary" },
  ];

  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-panel border border-border bg-card shadow-card lg:grid-cols-4">
      {cells.map((cell, i) => (
        <div
          key={cell.label}
          className={cn(
            "px-4 py-3",
            i > 0 && "lg:border-l lg:border-border",
            i % 2 === 1 && "border-l border-border lg:border-l",
            i >= 2 && "border-t border-border lg:border-t-0"
          )}
        >
          <div className="text-label font-semibold uppercase text-text-muted">{cell.label}</div>
          <div className={cn("font-mono text-kpi font-semibold tabular-nums", cell.tone)}>{cell.value}</div>
        </div>
      ))}
    </div>
  );
}
