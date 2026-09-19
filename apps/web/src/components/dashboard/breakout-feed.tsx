"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { PanelHeader } from "@/components/ui/panel-header";
import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { ActiveBreakout } from "@/lib/api-types";

const TRIGGER_LABELS: Record<string, string> = {
  pdh_pdl: "PDH/PDL",
  orb: "ORB",
  "52w": "52W",
  donchian: "Donchian",
  nr4: "NR4",
  nr7: "NR7",
  inside_bar: "Inside Bar",
  volume_breakout: "Volume",
  vwap: "VWAP",
  ema_cross: "EMA Cross",
  macd_cross: "MACD Cross",
  bollinger_squeeze: "BB Squeeze",
};

function timeAgo(dateStr?: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function FlashPrice({ price }: { price: number }) {
  const prevRef = useRef(price);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    if (price > prevRef.current) setFlash("flash-bullish");
    else if (price < prevRef.current) setFlash("flash-bearish");
    prevRef.current = price;
    const t = setTimeout(() => setFlash(null), 600);
    return () => clearTimeout(t);
  }, [price]);

  return (
    <span
      className={cn(
        "inline-block rounded px-1 font-mono text-panel font-semibold tabular-nums text-text-primary",
        flash
      )}
    >
      {formatPrice(price)}
    </span>
  );
}

interface BreakoutFeedProps {
  items: ActiveBreakout[];
}

interface BreakoutGroup {
  symbol: string;
  company_name?: string | null;
  last_price?: number | null;
  is_live: boolean;
  triggered_at?: string | null;
  signals: ActiveBreakout[];
}

/** One row per stock, with every trigger that fired shown as a chip. */
function groupBySymbol(items: ActiveBreakout[]): BreakoutGroup[] {
  const groups = new Map<string, BreakoutGroup>();
  for (const item of items) {
    const g = groups.get(item.symbol);
    if (g) {
      g.signals.push(item);
      g.is_live = g.is_live || item.is_live !== false;
    } else {
      groups.set(item.symbol, {
        symbol: item.symbol,
        company_name: item.company_name,
        last_price: item.last_price,
        is_live: item.is_live !== false,
        triggered_at: item.triggered_at,
        signals: [item],
      });
    }
  }
  return [...groups.values()];
}

export function BreakoutFeed({ items }: BreakoutFeedProps) {
  const [visibleGroups, setVisibleGroups] = useState<BreakoutGroup[]>([]);
  const anyStale = items.some((i) => i.is_live === false);
  const totalStocks = new Set(items.map((i) => i.symbol)).size;

  useEffect(() => {
    setVisibleGroups(groupBySymbol(items).slice(0, 20));
  }, [items]);

  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader
        title="Breakout feed"
        meta={anyStale ? "last session" : "live"}
        action={
          <Badge variant="neutral">
            {totalStocks} stocks · {items.length} signals
          </Badge>
        }
      />

      {anyStale && (
        <div className="border-b border-border bg-warning/10 px-4 py-1.5 text-label text-warning">
          Market closed — showing the last confirmed breakouts from the most recent session
        </div>
      )}

      <div className="max-h-[420px] overflow-y-auto">
        <AnimatePresence initial={false}>
          {visibleGroups.map((group, idx) => {
            const bullish = group.signals.filter((s) => s.direction === "bullish").length;
            const direction = bullish >= group.signals.length / 2 ? "bullish" : "bearish";
            return (
              <motion.div
                key={group.symbol}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 16 }}
                transition={{ delay: Math.min(idx, 10) * 0.04, duration: 0.25, ease: "easeOut" }}
              >
                <Link
                  href={`/chart/${group.symbol}`}
                  className={cn(
                    "flex items-center gap-3 border-b border-border-subtle px-4 py-2.5 transition-colors last:border-0 hover:bg-accent/[0.04] sm:gap-4"
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="font-mono text-data font-semibold text-text-primary">
                        {group.symbol}
                      </span>
                      {group.company_name && (
                        <span className="truncate text-label text-text-secondary">
                          {group.company_name}
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      {group.signals.map((sig) => (
                        <span
                          key={sig.trigger_type}
                          className="rounded bg-elevated px-1.5 py-px text-micro font-semibold uppercase tracking-wide text-text-secondary"
                        >
                          {TRIGGER_LABELS[sig.trigger_type] ?? sig.trigger_type}
                        </span>
                      ))}
                      <span className="text-label text-text-muted">
                        {group.is_live ? timeAgo(group.triggered_at ?? undefined) : "last session"}
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    {group.last_price != null && <FlashPrice price={group.last_price} />}
                    <div
                      className={cn(
                        "text-label font-semibold",
                        direction === "bullish" ? "text-bullish" : "text-bearish"
                      )}
                    >
                      <span className="mr-1 text-[8px]">{direction === "bullish" ? "▲" : "▼"}</span>
                      {direction === "bullish" ? "Bullish" : "Bearish"}
                    </div>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {visibleGroups.length === 0 && (
          <div className="px-5 py-12 text-center text-data text-text-muted">
            No breakout signals yet
          </div>
        )}
      </div>
    </div>
  );
}
