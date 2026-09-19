"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { PanelHeader } from "@/components/ui/panel-header";
import { formatPrice, formatPercent, formatVolume } from "@/lib/format";
import type { ScanResultItem } from "@/lib/api-types";

interface VolumeSurgesProps {
  items: ScanResultItem[];
}

export function VolumeSurges({ items }: VolumeSurgesProps) {
  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader
        title="Volume surges"
        meta="≥ 2× 20-day average"
        action={<Badge variant="neutral">{items.length}</Badge>}
      />

      <div className="max-h-[360px] overflow-y-auto">
        <table className="w-full text-data">
          <thead className="sticky top-0 bg-elevated">
            <tr className="border-b border-border text-label uppercase text-text-muted">
              <th className="px-4 py-2 text-left font-semibold">Symbol</th>
              <th className="px-4 py-2 text-right font-semibold">LTP</th>
              <th className="px-4 py-2 text-right font-semibold">Chg %</th>
              <th className="px-4 py-2 text-right font-semibold">Volume</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const up = (item.change_pct ?? 0) >= 0;
              return (
                <tr
                  key={item.symbol}
                  className="border-b border-border-subtle transition-colors last:border-0 hover:bg-accent/[0.04]"
                >
                  <td className="px-4 py-2">
                    <Link
                      href={`/chart/${item.symbol}`}
                      className="font-mono font-semibold text-text-primary hover:text-accent"
                    >
                      {item.symbol}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums text-text-primary">
                    {formatPrice(item.ltp ?? 0)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-mono tabular-nums ${up ? "text-bullish" : "text-bearish"}`}
                  >
                    {formatPercent(item.change_pct ?? 0)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums text-text-secondary">
                    {formatVolume(item.volume ?? 0)}
                  </td>
                </tr>
              );
            })}
            {items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-12 text-center text-text-muted">
                  No volume surges detected
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
