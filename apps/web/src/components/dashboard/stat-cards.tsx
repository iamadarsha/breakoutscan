"use client";

import { AnimatedNumber } from "@/components/ui/animated-number";
import { cn } from "@/lib/cn";
import type { MarketBreadth } from "@/lib/api-types";

interface StatCardsProps {
  breakoutCount?: number;
  alertCount?: number;
  volumeSurgeCount?: number;
  breadth?: MarketBreadth;
}

/**
 * Headline numbers as ONE segmented strip (level 1 of the dashboard hierarchy).
 * Numbers are neutral ink; colour is reserved for breadth, the only KPI with a
 * direction. Hairline dividers replace four separate boxes.
 */
export function StatCards({
  breakoutCount = 0,
  alertCount = 0,
  volumeSurgeCount = 0,
  breadth,
}: StatCardsProps) {
  const total = Math.max(breadth?.total ?? 0, 1);
  const breadthPct = breadth ? Math.round((breadth.advances / total) * 100) : 0;
  const declinePct = breadth ? Math.round((breadth.declines / total) * 100) : 0;

  const cells = [
    { label: "Active breakouts", value: breakoutCount, hint: "signals from the latest session" },
    { label: "Triggered alerts", value: alertCount, hint: "your alerts that fired" },
    { label: "Volume surges", value: volumeSurgeCount, hint: "≥ 2× average volume" },
  ];

  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-panel border border-border bg-card shadow-card lg:grid-cols-4">
      {cells.map((cell, i) => (
        <div
          key={cell.label}
          className={cn(
            "px-4 py-3.5 sm:px-5",
            i > 0 && "lg:border-l lg:border-border",
            i % 2 === 1 && "border-l border-border lg:border-l",
            i >= 2 && "border-t border-border lg:border-t-0"
          )}
        >
          <div className="text-label font-semibold uppercase text-text-muted">{cell.label}</div>
          <AnimatedNumber
            value={cell.value}
            format={(v) => Math.round(v).toString()}
            className="mt-1 block font-mono text-kpi font-semibold tabular-nums text-text-primary"
          />
          <div className="mt-0.5 text-micro normal-case tracking-normal text-text-muted">{cell.hint}</div>
        </div>
      ))}

      <div className="border-t border-border px-4 py-3.5 sm:px-5 lg:border-l lg:border-t-0">
        <div className="text-label font-semibold uppercase text-text-muted">Market breadth</div>
        <div className="mt-1 flex items-baseline gap-1">
          <AnimatedNumber
            value={breadthPct}
            format={(v) => Math.round(v).toString()}
            className={cn(
              "font-mono text-kpi font-semibold tabular-nums",
              breadthPct >= 50 ? "text-bullish" : "text-bearish"
            )}
          />
          <span className="font-mono text-panel font-semibold text-text-muted">%</span>
          <span className="ml-1 text-micro normal-case tracking-normal text-text-muted">advancing</span>
        </div>
        <div className="mt-1.5 flex h-1 overflow-hidden rounded-full bg-border" aria-hidden>
          <div className="bg-bullish" style={{ width: `${breadthPct}%` }} />
          <div className="bg-bearish" style={{ width: `${declinePct}%` }} />
        </div>
      </div>
    </div>
  );
}
