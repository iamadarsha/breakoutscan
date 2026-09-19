"use client";

import Link from "next/link";
import { PanelHeader } from "@/components/ui/panel-header";
import { formatDate, formatTime, formatPrice } from "@/lib/format";
import type { AlertHistoryItem } from "@/lib/api-types";

interface HistoryTimelineProps {
  history: AlertHistoryItem[];
}

export function HistoryTimeline({ history }: HistoryTimelineProps) {
  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader title="Trigger history" meta="most recent first" />

      {history.length === 0 ? (
        <div className="px-4 py-10 text-center text-data text-text-muted">
          Nothing has triggered yet. Alerts fire when a watched stock confirms a breakout.
        </div>
      ) : (
        <div className="max-h-[420px] overflow-y-auto">
          {history.map((h) => (
            <div
              key={h.id}
              className="flex items-center justify-between gap-3 border-b border-border-subtle px-4 py-2.5 last:border-0"
            >
              <div className="min-w-0">
                <Link
                  href={`/chart/${h.symbol}`}
                  className="inline-block py-1.5 font-mono text-data font-semibold text-text-primary hover:text-accent"
                >
                  {h.symbol}
                </Link>
                <div className="text-label text-text-muted">
                  {formatDate(h.triggered_at)} · {formatTime(h.triggered_at)}
                </div>
              </div>
              <span className="font-mono text-data font-medium tabular-nums text-text-primary">
                {formatPrice(Number(h.trigger_price) || 0)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
