"use client";

import { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Target,
  ShieldAlert,
  ChevronDown,
  Newspaper,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import type { AiSuggestion } from "@/lib/api-types";

interface StockCardProps {
  suggestion: AiSuggestion;
  index: number;
  changePct?: number;
}

export function StockCard({ suggestion, index, changePct }: StockCardProps) {
  const [expanded, setExpanded] = useState(false);

  const confidence = suggestion.confidence ?? 0;
  // Backend sends 1-10; guard against a stray 0-100 value slipping through.
  const confidenceOutOf10 = confidence > 10 ? Math.round(confidence / 10) : confidence;
  const confidencePct = Math.max(0, Math.min(100, confidenceOutOf10 * 10));
  const confidenceLabel =
    confidenceOutOf10 >= 8 ? "High" : confidenceOutOf10 >= 5 ? "Medium" : "Low";
  const confidenceColor =
    confidenceOutOf10 >= 8 ? "bg-bullish" : confidenceOutOf10 >= 5 ? "bg-warning" : "bg-text-muted";

  const isSell = suggestion.action === "SELL";
  const hasChange = changePct != null;
  const changeColor = hasChange
    ? changePct >= 0 ? "text-bullish" : "text-bearish"
    : "text-text-muted";

  const sources = suggestion.news_sources ?? [];
  const tags = suggestion.tags ?? [];

  return (
    <div className="group h-full rounded-panel border border-border bg-card p-4 transition-colors hover:border-accent/40">
      {/* Header */}
      <Link href={`/chart/${suggestion.symbol}`} className="block">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-panel font-semibold text-text-primary group-hover:text-accent transition">
                {suggestion.symbol}
              </span>
              <Badge variant="neutral" className="text-micro">
                #{index + 1}
              </Badge>
              {suggestion.action && (
                <Badge variant={isSell ? "bearish" : "bullish"} className="text-micro">
                  {suggestion.action}
                </Badge>
              )}
            </div>
            {suggestion.name && (
              <p className="mt-0.5 text-label text-text-muted truncate max-w-[200px]">
                {suggestion.name}
              </p>
            )}
          </div>

          <div className="text-right">
            <div className={cn("text-data font-bold tabular-nums", changeColor)}>
              {hasChange
                ? `${changePct >= 0 ? "+" : ""}${changePct.toFixed(1)}%`
                : "—"}
            </div>
          </div>
        </div>
      </Link>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-micro font-medium text-text-muted">
            Confidence
          </span>
          <span className="text-micro font-semibold text-text-secondary">
            {confidenceLabel} · {confidenceOutOf10}/10
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-elevated">
          <div
            className={cn("h-full rounded-full transition-all", confidenceColor)}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>

      {/* Catalyst — the one-line "why now" */}
      {suggestion.catalyst && (
        <div className="mb-3 flex gap-1.5 rounded-md bg-elevated/60 px-2.5 py-2">
          <Zap className="h-3 w-3 flex-shrink-0 mt-0.5 text-accent" />
          <p className="text-label leading-snug text-text-secondary line-clamp-2">
            {suggestion.catalyst}
          </p>
        </div>
      )}

      {/* Targets */}
      <div className="flex items-center gap-3 text-micro text-text-muted mb-3">
        {suggestion.target_pct != null && (
          <span className="flex items-center gap-1">
            {isSell ? <TrendingDown className="h-3 w-3" /> : <Target className="h-3 w-3" />}
            Target: {suggestion.target_pct}%
          </span>
        )}
        {suggestion.stop_loss_pct != null && (
          <span className="flex items-center gap-1">
            <ShieldAlert className="h-3 w-3" />
            SL: {suggestion.stop_loss_pct}%
          </span>
        )}
      </div>

      {/* Why this pick — collapsed by default, expandable for depth */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between rounded-lg border border-border px-3 py-2.5 text-label font-medium text-text-secondary transition hover:border-accent/30 hover:text-text-primary"
      >
        <span>Why this pick</span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")}
        />
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-2.5 border-t border-border/60 pt-2.5">
          <p className="text-label leading-relaxed text-text-secondary">
            {suggestion.rationale}
          </p>

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
                  <li key={i} className="text-micro leading-snug">
                    {src.url ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-text-secondary hover:text-accent hover:underline"
                      >
                        {src.title}
                      </a>
                    ) : (
                      <span className="text-text-secondary">{src.title}</span>
                    )}
                    {src.source && (
                      <span className="text-text-muted"> — {src.source}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
