"use client";

import { useState } from "react";
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
import { motion } from "framer-motion";
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
}

export function PrebuiltScanGrid({
  scans,
  activeScanId,
  onRunScan,
  isLoading,
}: PrebuiltScanGridProps) {
  const [activeCategory, setActiveCategory] = useState("All");

  const filtered =
    activeCategory === "All"
      ? scans
      : scans.filter(
          (s) => s.category.toLowerCase() === activeCategory.toLowerCase()
        );

  return (
    <div>
      {/* Category filter pills */}
      <div className="mb-5 flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-xs font-medium transition",
              activeCategory === cat
                ? "bg-accent text-white shadow-accent"
                : "border border-border bg-card text-text-secondary hover:border-accent/40 hover:text-text-primary"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Card grid */}
      <motion.div
        className="grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-3 xl:grid-cols-4"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.04 } },
        }}
      >
        {filtered.map((scan) => {
          const Icon = iconMap[scan.icon ?? ""] ?? Zap;
          const isActive = activeScanId === scan.id;

          return (
            <motion.button
              key={scan.id}
              variants={{
                hidden: { opacity: 0, y: 16, scale: 0.97 },
                visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.3, ease: "easeOut" } },
              }}
              whileHover={{ scale: 1.02, transition: { duration: 0.15 } }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onRunScan(scan.id)}
              disabled={isLoading}
              className={cn(
                "group relative flex flex-col items-start rounded-panel border backdrop-blur-md p-3 sm:p-4 text-left shadow-glass transition-all",
                isActive
                  ? "border-accent bg-accent/[0.08] shadow-glow"
                  : "border-border bg-card hover:border-accent/50 hover:-translate-y-0.5"
              )}
            >
              <div
                className={cn(
                  "mb-3 rounded-lg p-2.5",
                  isActive
                    ? "bg-accent/15 text-accent"
                    : "bg-elevated text-text-secondary group-hover:text-text-primary"
                )}
              >
                <Icon className="h-5 w-5" />
              </div>
              <h4 className="mb-0.5 text-xs sm:text-sm font-semibold text-text-primary leading-tight">
                {scan.name}
              </h4>
              <p className="text-[10px] sm:text-xs leading-relaxed text-text-secondary line-clamp-2">
                {scan.description}
              </p>

              <div className="mt-3 flex w-full items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">
                  {scan.category}
                </span>
                <span
                  className={cn(
                    "rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition",
                    isActive && !isLoading
                      ? "bg-accent/20 text-accent"
                      : "bg-elevated text-text-muted group-hover:bg-accent group-hover:text-white"
                  )}
                >
                  {isActive && isLoading ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    "Run"
                  )}
                </span>
              </div>

              {/* Loading bar */}
              {isActive && isLoading && (
                <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-border">
                  <div className="h-full w-1/3 animate-pulse rounded-full bg-accent" />
                </div>
              )}
            </motion.button>
          );
        })}
      </motion.div>

      {filtered.length === 0 && (
        <div className="py-12 text-center text-sm text-text-muted">
          No scans in this category
        </div>
      )}
    </div>
  );
}
