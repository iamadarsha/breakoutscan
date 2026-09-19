"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { PanelHeader } from "@/components/ui/panel-header";
import type { MarketBreadth } from "@/lib/api-types";

interface BreadthDonutProps {
  breadth?: MarketBreadth;
}

export function BreadthDonut({ breadth }: BreadthDonutProps) {
  const advances = breadth?.advances ?? 0;
  const declines = breadth?.declines ?? 0;
  const unchanged = breadth?.unchanged ?? 0;
  const total = breadth?.total ?? 0;
  const ratio = breadth?.advance_decline_ratio ?? 0;

  const slices = [
    { name: "Advances", value: advances, fill: "var(--bullish)" },
    { name: "Declines", value: declines, fill: "var(--bearish)" },
    { name: "Unchanged", value: unchanged, fill: "var(--border)" },
  ];

  const rows = [
    { label: "Advances", value: advances, dot: "bg-bullish", tone: "text-bullish" },
    { label: "Declines", value: declines, dot: "bg-bearish", tone: "text-bearish" },
    { label: "Unchanged", value: unchanged, dot: "bg-text-muted/40", tone: "text-text-primary" },
  ];

  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader title="Market breadth" meta="NIFTY 50 · last session" />
      <div className="flex items-center gap-5 px-4 py-4">
        <div className="relative h-[104px] w-[104px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                cx="50%"
                cy="50%"
                innerRadius={34}
                outerRadius={50}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
                isAnimationActive={false}
              >
                {slices.map((s) => (
                  <Cell key={s.name} fill={s.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-panel font-semibold tabular-nums text-text-primary">
              {ratio.toFixed(2)}
            </span>
            <span className="text-micro uppercase text-text-muted">A / D</span>
          </div>
        </div>

        <dl className="min-w-0 flex-1 space-y-2 text-data">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${r.dot}`} />
              <dt className="text-text-secondary">{r.label}</dt>
              <dd className={`ml-auto font-mono font-semibold tabular-nums ${r.tone}`}>{r.value}</dd>
            </div>
          ))}
          <div className="flex items-center justify-between border-t border-border pt-2 text-label text-text-muted">
            <span>Total tracked</span>
            <span className="font-mono tabular-nums text-text-secondary">{total}</span>
          </div>
        </dl>
      </div>
    </div>
  );
}
