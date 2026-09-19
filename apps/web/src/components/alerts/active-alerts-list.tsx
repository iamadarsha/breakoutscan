"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PanelHeader } from "@/components/ui/panel-header";
import type { Alert } from "@/lib/api-types";

interface ActiveAlertsListProps {
  alerts: Alert[];
  onDelete: (id: string) => void;
  deletingId?: string | null;
}

const FREQUENCY_LABEL: Record<string, string> = {
  once: "Once",
  every_time: "Every time",
  daily_digest: "Daily digest",
};

export function ActiveAlertsList({ alerts, onDelete, deletingId }: ActiveAlertsListProps) {
  const active = alerts.filter((a) => a.is_active);

  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader
        title="Your alerts"
        meta="fires on a confirmed breakout"
        action={<Badge variant="neutral">{active.length} active</Badge>}
      />

      <div className="max-h-[420px] overflow-y-auto">
        {active.length === 0 && (
          <div className="px-4 py-10 text-center text-data text-text-muted">
            No alerts yet. Pick a stock on the left to get notified when it breaks out.
          </div>
        )}

        {active.map((alert) => (
          <div
            key={alert.id}
            className="flex items-center gap-3 border-b border-border-subtle px-4 py-2.5 last:border-0"
          >
            <div className="min-w-0 flex-1">
              <Link
                href={`/chart/${alert.symbol}`}
                className="inline-block py-1.5 font-mono text-data font-semibold text-text-primary hover:text-accent"
              >
                {alert.symbol}
              </Link>
              <div className="text-label text-text-muted">
                Notify {(FREQUENCY_LABEL[alert.frequency] ?? alert.frequency ?? "once").toLowerCase()}
              </div>
            </div>
            <Badge variant="bullish">Watching</Badge>
            <button
              onClick={() => onDelete(alert.id)}
              disabled={deletingId === alert.id}
              aria-label={`Remove alert for ${alert.symbol}`}
              title="Remove alert"
              className="rounded-lg p-2.5 text-text-muted lg:p-2 transition-colors hover:bg-bearish/10 hover:text-bearish disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
