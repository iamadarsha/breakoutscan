"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  ShieldAlert,
  ChevronDown,
  Newspaper,
  Zap,
  Sparkles,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { fetchStockAnalysis } from "@/lib/api";
import { cn } from "@/lib/cn";

interface StockAnalysisCardProps {
  symbol: string;
}

const sourceLabel: Record<string, string> = {
  groq: "Groq Llama 3.3",
  "technical-analysis": "Technical scoring (AI unavailable)",
};

export function StockAnalysisCard({ symbol }: StockAnalysisCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["stockAnalysis", symbol],
    queryFn: () => fetchStockAnalysis(symbol),
    retry: 0,
    staleTime: 10 * 60_000,
  });

  if (isLoading) {
    return (
      <div className="glass-card rounded-panel p-5">
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-accent" />
          <div>
            <p className="text-sm font-medium text-text-primary">Recommendation loading...</p>
            <p className="text-xs text-text-muted">Groq is reading the latest news on {symbol}</p>
          </div>
        </div>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-elevated">
          <div
            className="h-full w-1/3 rounded-full bg-gradient-to-r from-accent to-bullish"
            style={{ animation: "indeterminate-progress 1.4s ease-in-out infinite" }}
          />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="glass-card rounded-panel p-5 text-center">
        <p className="text-sm text-text-muted">AI analysis unavailable for {symbol} right now.</p>
      </div>
    );
  }

  const isBuy = data.action === "BUY";
  const isSell = data.action === "SELL";
  const actionVariant = isBuy ? "bullish" : isSell ? "bearish" : "neutral";
  const ActionIcon = isBuy ? TrendingUp : isSell ? TrendingDown : Minus;

  const confidence = Math.max(1, Math.min(10, data.confidence ?? 5));
  const confidenceLabel = confidence >= 8 ? "High" : confidence >= 5 ? "Medium" : "Low";

  // A single 0-100 "AI Score" for the gradient-track marker below — centered
  // at 50 for HOLD (no directional lean by definition), pushed toward either
  // edge by confidence for BUY/SELL. This is our own AI's score, not a
  // stand-in for real analyst consensus — labeled as such in the UI.
  const direction = isBuy ? 1 : isSell ? -1 : 0;
  const aiScore = Math.max(0, Math.min(100, 50 + direction * confidence * 5));

  const sources = data.news_sources ?? [];
  const tags = data.tags ?? [];
  const poweredBy = data.source ? sourceLabel[data.source] ?? data.source : null;

  return (
    <div className="glass-card rounded-panel p-4 sm:p-5">
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Badge variant={actionVariant} className="gap-1 text-sm">
            <ActionIcon className="h-3.5 w-3.5" />
            {data.action}
          </Badge>
          {poweredBy && (
            <span className="flex items-center gap-1 text-[10px] text-text-muted">
              <Sparkles className="h-3 w-3" /> {poweredBy}
            </span>
          )}
        </div>
      </div>

      {/* AI Score — gradient track with a positioned marker, same visual
          language as a broker's Sell↔Hold↔Buy gauge, but this is our own
          Groq-derived score, not a stand-in for real analyst consensus. */}
      <div className="mb-3">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-[10px] font-medium text-text-muted">AI Score</span>
          <span className="text-[10px] font-semibold text-text-secondary">
            {confidenceLabel} confidence · {confidence}/10
          </span>
        </div>
        <div className="relative h-2 w-full rounded-full bg-gradient-to-r from-bearish via-text-muted to-bullish">
          <div
            className="absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-page bg-text-primary shadow-md transition-all"
            style={{ left: `${aiScore}%` }}
          />
        </div>
        <div className="mt-1 flex items-center justify-between text-[9px] text-text-muted">
          <span>Sell</span>
          <span>Hold</span>
          <span>Buy</span>
        </div>
      </div>

      {/* Catalyst */}
      {data.catalyst && (
        <div className="mb-3 flex gap-1.5 rounded-md bg-elevated/60 px-2.5 py-2">
          <Zap className="h-3 w-3 flex-shrink-0 mt-0.5 text-accent" />
          <p className="text-[11px] leading-snug text-text-secondary">{data.catalyst}</p>
        </div>
      )}

      {/* Targets */}
      {(data.target_pct ?? 0) > 0 && (
        <div className="mb-3 flex items-center gap-3 text-[10px] text-text-muted">
          <span className="flex items-center gap-1">
            {isSell ? <TrendingDown className="h-3 w-3" /> : <Target className="h-3 w-3" />}
            Target: {data.target_pct}%
          </span>
          {(data.stop_loss_pct ?? 0) > 0 && (
            <span className="flex items-center gap-1">
              <ShieldAlert className="h-3 w-3" />
              SL: {data.stop_loss_pct}%
            </span>
          )}
        </div>
      )}

      {/* Why this call */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between rounded-full border border-border/60 px-2.5 py-1.5 text-[11px] font-medium text-text-secondary transition hover:border-accent/30 hover:text-text-primary"
      >
        <span>Why this call</span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-2.5 border-t border-border/60 pt-2.5">
          <p className="text-[11px] leading-relaxed text-text-secondary">{data.rationale}</p>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-elevated px-2 py-0.5 text-[9px] font-medium text-text-muted"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {sources.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-text-muted">
                <Newspaper className="h-2.5 w-2.5" />
                Sources
              </div>
              <ul className="space-y-1">
                {sources.slice(0, 3).map((src, i) => (
                  <li key={i} className="text-[10px] leading-snug">
                    {src.url ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-text-secondary hover:text-accent hover:underline"
                      >
                        {src.title}
                      </a>
                    ) : (
                      <span className="text-text-secondary">{src.title}</span>
                    )}
                    {src.source && <span className="text-text-muted"> — {src.source}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <p className="mt-3 text-[10px] leading-relaxed text-text-muted">
        Informational only, not financial advice. Always do your own research.
      </p>
    </div>
  );
}
