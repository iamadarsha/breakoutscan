"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonCard } from "@/components/ui/skeleton";
import { StockCard } from "@/components/ai-picks/stock-card";
import {
  useAiSuggestions,
  useRefreshAiSuggestions,
} from "@/hooks/use-ai-suggestions";
import { RefreshCw, Sparkles, Clock } from "lucide-react";
import { ThinkingOrb } from "thinking-orbs";
import { cn } from "@/lib/cn";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import { useLivePrices } from "@/hooks/use-live-prices";
import { fetchLivePrices } from "@/lib/api";
import type { AiSuggestion } from "@/lib/api-types";

type TabKey = "intraday" | "weekly" | "monthly";

const TABS: { key: TabKey; label: string }[] = [
  { key: "intraday", label: "Intraday" },
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
];

export default function AiPicksPage() {
  const { data, isLoading } = useAiSuggestions();
  const refresh = useRefreshAiSuggestions();
  const [activeTab, setActiveTab] = useState<TabKey>("intraday");

  // Support both old format (flat suggestions[]) and new format (intraday/weekly/monthly)
  const hasGroupedFormat = !!(data?.intraday || data?.weekly || data?.monthly);

  const groupedPicks: Record<TabKey, AiSuggestion[]> = hasGroupedFormat
    ? {
        intraday: data?.intraday ?? [],
        weekly: data?.weekly ?? [],
        monthly: data?.monthly ?? [],
      }
    : {
        intraday: (data?.suggestions ?? []).filter(
          (s) => s.target_horizon === "intraday"
        ),
        weekly: (data?.suggestions ?? []).filter(
          (s) => s.target_horizon === "swing"
        ),
        monthly: (data?.suggestions ?? []).filter(
          (s) => s.target_horizon === "positional"
        ),
      };

  const activePicks = groupedPicks[activeTab];

  // Collect all symbols across all tabs for live price subscription
  const allSymbols = [...new Set([
    ...groupedPicks.intraday,
    ...groupedPicks.weekly,
    ...groupedPicks.monthly,
  ].map((s) => s.symbol))];
  const wsLivePrices = useLivePrices(allSymbols);

  // REST fallback for when WebSocket doesn't deliver (e.g. market closed)
  const { data: restPrices } = useQuery({
    queryKey: ["livePrices", allSymbols.join(",")],
    queryFn: () => fetchLivePrices(allSymbols),
    enabled: allSymbols.length > 0,
    retry: 0,
    staleTime: 30_000,
  });

  // Merge: WS takes priority, REST as fallback
  const livePrices: Record<string, { change_pct: number }> = {};
  for (const sym of allSymbols) {
    if (wsLivePrices[sym]) {
      livePrices[sym] = wsLivePrices[sym];
    } else {
      const rest = restPrices?.find((p) => p.symbol === sym);
      if (rest) livePrices[sym] = rest;
    }
  }

  const generatedAt = data?.generated_at
    ? new Date(data.generated_at).toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        dateStyle: "medium",
        timeStyle: "short",
      })
    : null;

  // Reflects which layer actually produced these picks — never claim AI
  // authorship for a result the technical-scoring fallback generated.
  const sourceLabel: Record<string, string> = {
    gemini: "Gemini 3.5 Flash Lite",
    groq: "Groq Llama 3.3",
    "technical-analysis": "Technical scoring (AI unavailable)",
    pending: "Generating…",
  };
  const poweredBy = data?.source ? sourceLabel[data.source] ?? data.source : null;

  return (
    <AppShell>
      <PageTransition>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <SectionHeading
              title="AI Picks"
              subtitle="AI-powered stock suggestions based on latest market news"
            />
            <button
              onClick={() =>
                refresh.mutate(undefined, {
                  onSuccess: () => toast.success("AI Picks refreshed"),
                  onError: () => toast.error("Refresh failed - try again"),
                })
              }
              disabled={refresh.isPending}
              className={cn(
                "flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-text-secondary transition hover:border-accent/30 hover:text-text-primary",
                refresh.isPending && "cursor-not-allowed opacity-50"
              )}
            >
              {refresh.isPending ? (
                <ThinkingOrb state="searching" size={20} theme="auto" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {refresh.isPending ? "Generating..." : "Refresh"}
            </button>
          </div>

          {/* Meta info */}
          {generatedAt && (
            <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
              {poweredBy && (
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3" /> Powered by {poweredBy}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" /> Generated {generatedAt}
              </span>
              {data?.headline_count ? (
                <span>Based on {data.headline_count} news headlines</span>
              ) : null}
            </div>
          )}

          {/* Tab switcher */}
          <div className="flex items-center gap-1 border-b border-border">
            {TABS.map((tab) => {
              const count = groupedPicks[tab.key].length;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors",
                    activeTab === tab.key
                      ? "text-text-primary"
                      : "text-text-muted hover:text-text-secondary"
                  )}
                >
                  {tab.label}
                  {count > 0 && (
                    <span
                      className={cn(
                        "rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
                        activeTab === tab.key
                          ? "bg-accent/20 text-accent"
                          : "bg-elevated text-text-muted"
                      )}
                    >
                      {count}
                    </span>
                  )}
                  {activeTab === tab.key && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-accent" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Cards grid */}
          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : activePicks.length === 0 ? (
            <div className="rounded-panel border border-border bg-card p-10 text-center">
              <Sparkles className="mx-auto h-8 w-8 text-text-muted" />
              <p className="mt-3 text-sm text-text-secondary">
                No AI suggestions available for this timeframe. Click Refresh to
                generate picks based on the latest market news.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {activePicks.map((s, i) => (
                <motion.div
                  key={s.symbol}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                >
                  <StockCard suggestion={s} index={i} changePct={livePrices[s.symbol]?.change_pct} />
                </motion.div>
              ))}
            </div>
          )}

          {/* Disclaimer */}
          <div className="rounded-panel border border-border bg-card/60 px-5 py-4">
            <p className="text-[11px] leading-relaxed text-text-muted">
              Disclaimer: AI-generated suggestions are for informational
              purposes only and do not constitute financial advice. Always do
              your own research before making investment decisions. Past
              performance does not guarantee future results.
            </p>
          </div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
