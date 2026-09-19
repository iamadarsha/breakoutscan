"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { formatPrice, formatPercent } from "@/lib/format";
import { API_BASE_URL } from "@/lib/constants";

interface IndexTick {
  symbol: string;
  name: string;
  value: number;
  change_pct: number;
}

export function IndexTickerBar() {
  const [indices, setIndices] = useState<IndexTick[]>([]);

  useEffect(() => {
    async function fetchIndices() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/market/indices`);
        if (res.ok) {
          const data = await res.json();
          setIndices(
            (data ?? []).map((d: Record<string, unknown>) => ({
              symbol: d.symbol ?? "",
              name: d.name ?? d.symbol ?? "",
              value: Number(d.value ?? d.last ?? 0),
              change_pct: Number(d.change_pct ?? 0),
            }))
          );
        }
      } catch {
        // silently ignore — ticker is non-critical
      }
    }
    fetchIndices();
    const id = setInterval(fetchIndices, 30_000);
    return () => clearInterval(id);
  }, []);

  if (indices.length === 0) return null;

  // One quiet 32px strip of index levels — reference data, so it stays low in the hierarchy.
  return (
    <div
      className="scrollbar-hide flex h-8 w-full items-center overflow-x-auto border-b border-border bg-card px-3 sm:px-5"
      aria-label="Market indices"
    >
      <div className="flex items-center gap-5 whitespace-nowrap text-label">
        {indices.map((idx) => {
          const up = idx.change_pct >= 0;
          return (
            <span key={idx.symbol} className="flex items-baseline gap-1.5">
              <span className="font-medium uppercase text-text-muted">{idx.name}</span>
              <span className="font-mono font-semibold tabular-nums text-text-primary">
                {formatPrice(idx.value)}
              </span>
              <span
                className={cn(
                  "font-mono tabular-nums",
                  up ? "text-bullish" : "text-bearish"
                )}
              >
                <span className="mr-0.5 text-[8px]">{up ? "▲" : "▼"}</span>{formatPercent(Math.abs(idx.change_pct)).replace("+", "")}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
