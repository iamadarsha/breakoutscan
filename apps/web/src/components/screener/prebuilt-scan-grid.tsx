"use client";

import { Fragment, useEffect, useState, type ReactNode } from "react";
import {
  TrendingUp,
  BarChart3,
  Zap,
  ArrowUpRight,
  Target,
  Activity,
  Waves,
  Shield,
  ArrowDownRight,
  Flame,
  GitBranch,
  Signal,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/cn";
import type { PrebuiltScan } from "@/lib/api-types";

const iconMap: Record<string, typeof TrendingUp> = {
  "trending-up": TrendingUp,
  "bar-chart": BarChart3,
  zap: Zap,
  "arrow-up-right": ArrowUpRight,
  target: Target,
  activity: Activity,
  waves: Waves,
  shield: Shield,
  "arrow-down-right": ArrowDownRight,
  flame: Flame,
  "git-branch": GitBranch,
  signal: Signal,
};

const CATEGORIES = [
  "All",
  "Intraday",
  "Swing",
  "Pattern",
  "Volume",
  "Momentum",
  "Breakout",
  "Moving Averages",
];

interface PrebuiltScanGridProps {
  scans: PrebuiltScan[];
  activeScanId?: string | null;
  onRunScan: (scanId: string) => void;
  isLoading?: boolean;
  /** Rendered full-width directly under the row that contains the active scan. */
  results?: ReactNode;
}

/** Mirrors the grid's `grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` breakpoints. */
function useGridColumns(): number {
  const [cols, setCols] = useState(4);
  useEffect(() => {
    const update = () => {
      const w = window.innerWidth;
      setCols(w >= 1280 ? 4 : w >= 1024 ? 3 : 2);
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return cols;
}

export function PrebuiltScanGrid({
  scans,
  activeScanId,
  onRunScan,
  isLoading,
  results,
}: PrebuiltScanGridProps) {
  const [activeCategory, setActiveCategory] = useState("All");
  const cols = useGridColumns();

  const filtered =
    activeCategory === "All"
      ? scans
      : scans.filter(
          (s) => s.category.toLowerCase() === activeCategory.toLowerCase()
        );

  // Results go after the last card of the active card's row (or the end if it is filtered out).
  const activeIndex = filtered.findIndex((s) => s.id === activeScanId);
  const resultsAfter =
    activeIndex < 0
      ? filtered.length - 1
      : Math.min(filtered.length, (Math.floor(activeIndex / cols) + 1) * cols) - 1;

  return (
    <div>
      {/* Category filter: quiet chips, the active one is the only filled element */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            aria-pressed={activeCategory === cat}
            className={cn(
              "rounded-md px-3 py-2 text-label font-medium transition-colors lg:px-2.5 lg:py-1",
              activeCategory === cat
                ? "bg-text-primary text-card"
                : "border border-border bg-card text-text-secondary hover:border-accent/40 hover:text-text-primary"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Scan cards: name first, then what it finds, then category + the run action */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filtered.map((scan, index) => {
          const Icon = iconMap[scan.icon ?? ""] ?? Zap;
          const isActive = activeScanId === scan.id;

          return (
            <Fragment key={scan.id}>
              <button
                onClick={() => onRunScan(scan.id)}
                disabled={isLoading}
                aria-pressed={isActive}
                className={cn(
                  "group relative flex flex-col items-start rounded-panel border p-3 text-left transition-colors disabled:cursor-wait",
                  isActive
                    ? "border-accent bg-accent/[0.06]"
                    : "border-border bg-card hover:border-accent/40 hover:bg-accent/[0.03]"
                )}
              >
                <div className="flex w-full items-center gap-2">
                  <span
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                      isActive ? "bg-accent/15 text-accent" : "bg-elevated text-text-secondary"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <h4 className="truncate text-data font-semibold text-text-primary">{scan.name}</h4>
                </div>
                <p className="mt-1.5 line-clamp-2 text-label sm:min-h-[32px] text-text-secondary">
                  {scan.description}
                </p>

                <div className="mt-2 flex w-full items-center justify-between">
                  <span className="text-micro font-semibold uppercase text-text-muted">
                    {scan.category}
                  </span>
                  <span
                    className={cn(
                      "flex items-center gap-1 text-label font-semibold transition-colors",
                      isActive ? "text-accent" : "text-text-muted group-hover:text-accent"
                    )}
                  >
                    {isActive && isLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <>Run <span aria-hidden>→</span></>
                    )}
                  </span>
                </div>

                {isActive && isLoading && (
                  <div className="absolute inset-x-0 bottom-0 h-0.5 overflow-hidden rounded-b-panel bg-border">
                    <div className="h-full w-1/3 animate-pulse bg-accent" />
                  </div>
                )}
              </button>
              {results && index === resultsAfter && (
                <div className="col-span-full">{results}</div>
              )}
            </Fragment>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="py-12 text-center text-data text-text-muted">
          No scans in this category
        </div>
      )}
    </div>
  );
}
