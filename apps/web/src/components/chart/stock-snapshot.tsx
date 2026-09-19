"use client";

import { PriceCell } from "@/components/ui/price-cell";
import { formatPercent, formatVolume, formatPrice } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { LivePrice, Stock } from "@/lib/api-types";

interface StockSnapshotProps {
  stock?: Stock;
  livePrice?: LivePrice;
}

/**
 * Quote bar. Hierarchy: price (largest) → symbol → change → name/sector → day range.
 * Everything a trader checks before looking at the chart sits in one 88px band.
 */
export function StockSnapshot({ stock, livePrice }: StockSnapshotProps) {
  const hasPrice = livePrice != null && livePrice.ltp > 0;
  const changePct = livePrice?.change_pct ?? 0;
  const change = livePrice?.change ?? 0;
  const up = change >= 0;

  const stats = livePrice
    ? [
        { label: "Open", value: formatPrice(livePrice.open) },
        { label: "High", value: formatPrice(livePrice.high) },
        { label: "Low", value: formatPrice(livePrice.low) },
        { label: "Volume", value: formatVolume(livePrice.volume) },
      ]
    : [];

  return (
    <div className="rounded-panel border border-border bg-card shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <h1 className="font-mono text-title font-semibold text-text-primary">
              {stock?.symbol ?? "---"}
            </h1>
            {stock?.sector && (
              <span className="rounded bg-elevated px-1.5 py-0.5 text-micro font-semibold uppercase text-text-secondary">
                {stock.sector}
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate text-data text-text-secondary">{stock?.name ?? "Loading…"}</p>
        </div>

        <div className="flex items-baseline gap-3">
          {hasPrice ? (
            <>
              <PriceCell price={livePrice.ltp} className="!px-0 text-kpi font-semibold" />
              <span
                className={cn(
                  "font-mono text-panel font-semibold tabular-nums",
                  up ? "text-bullish" : "text-bearish"
                )}
              >
                {up ? "+" : ""}
                {formatPrice(change)}
                <span className="ml-2">({formatPercent(changePct)})</span>
              </span>
            </>
          ) : (
            <span className="text-data text-text-muted">No live price — market closed</span>
          )}
        </div>
      </div>

      {stats.length > 0 && (
        <dl className="grid grid-cols-2 border-t border-border sm:grid-cols-4">
          {stats.map((item, i) => (
            <div
              key={item.label}
              className={cn("px-4 py-2", i > 0 && "sm:border-l sm:border-border", i % 2 === 1 && "border-l border-border sm:border-l")}
            >
              <dt className="text-micro font-semibold uppercase text-text-muted">{item.label}</dt>
              <dd className="font-mono text-data font-medium tabular-nums text-text-primary">{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
