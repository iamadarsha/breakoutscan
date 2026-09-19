"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { StatCards } from "@/components/dashboard/stat-cards";
import { BreakoutFeed } from "@/components/dashboard/breakout-feed";
import { BreadthDonut } from "@/components/dashboard/breadth-donut";
import { VolumeSurges } from "@/components/dashboard/volume-surges";
import { SectorHeatmap } from "@/components/dashboard/sector-heatmap";
import { ActiveScanToggles } from "@/components/dashboard/active-scan-toggles";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonCard } from "@/components/ui/skeleton";
import { PullToRefreshIndicator } from "@/components/ui/pull-to-refresh-indicator";
import { useMarketBreadth, useMarketSectors } from "@/hooks/use-market-breadth";
import { useActiveBreakouts } from "@/hooks/use-active-breakouts";
import { usePrebuiltScans, useRunPrebuiltScan } from "@/hooks/use-scan-run";
import { usePullToRefresh } from "@/hooks/use-pull-to-refresh";
import type { ScanResultItem } from "@/lib/api-types";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: breadth, isLoading: breadthLoading } = useMarketBreadth();
  const { data: sectors, isLoading: sectorsLoading } = useMarketSectors();
  const { data: scans, isLoading: scansLoading } = usePrebuiltScans();
  const { data: activeBreakouts = [] } = useActiveBreakouts();
  const runScan = useRunPrebuiltScan();

  const handleRefresh = useCallback(async () => {
    await queryClient.invalidateQueries();
  }, [queryClient]);

  const { pullDistance, refreshing, containerRef } = usePullToRefresh({
    onRefresh: handleRefresh,
  });

  const [breakoutItems, setBreakoutItems] = useState<ScanResultItem[]>([]);
  const [volumeItems, setVolumeItems] = useState<ScanResultItem[]>([]);

  const handleRunScan = useCallback(
    (scanId: string) => {
      runScan.mutate(scanId, {
        onSuccess: (result) => {
          setBreakoutItems((prev) => {
            const newItems = result.items.filter(
              (r) => !prev.some((p) => p.symbol === r.symbol)
            );
            return [...newItems, ...prev].slice(0, 50);
          });
          // Volume surges from any scan with high volume
          const volSurges = result.items.filter((r) => (r.volume ?? 0) > 0);
          if (volSurges.length > 0) {
            setVolumeItems((prev) => {
              const combined = [...volSurges, ...prev];
              const unique = combined.filter(
                (item, idx) =>
                  combined.findIndex((i) => i.symbol === item.symbol) === idx
              );
              return unique.slice(0, 20);
            });
          }
        },
      });
    },
    [runScan]
  );

  // Auto-run three high-yield scans on mount.
  // "bullish_ema_crossover" and "price_above_sma200" reliably return results
  // in normal / bullish markets; "volume_spike" catches intraday surges.
  // We avoid "rsi_oversold" as the default — it returns 0 on bullish days.
  useEffect(() => {
    if (!scans || scans.length === 0) return;
    const DEFAULT_SCANS = ["bullish_ema_crossover", "price_above_sma200", "volume_spike"];
    const scanIds = DEFAULT_SCANS.filter((id) =>
      scans.some((s) => s.id === id)
    );
    // Fall back to first available scan if none of the preferred IDs exist
    const toRun = scanIds.length > 0 ? scanIds : [scans[0].id];
    toRun.forEach((id) => handleRunScan(id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scans]);

  // Periodically refresh breakout data every 30 seconds while market is open
  useEffect(() => {
    if (!scans || scans.length === 0) return;
    const REFRESH_IDS = ["bullish_ema_crossover", "volume_spike"];
    const ids = REFRESH_IDS.filter((id) => scans.some((s) => s.id === id));
    if (ids.length === 0) return;
    const timer = setInterval(() => {
      ids.forEach((id) => handleRunScan(id));
    }, 30_000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scans]);

  // alertCount: all breakout items count as signals (signal_strength is
  // populated only when the backend stores a score — use length as fallback)
  const alertCount = useMemo(
    () =>
      breakoutItems.filter(
        (i) => (i.signal_strength != null ? i.signal_strength > 0.5 : true)
      ).length,
    [breakoutItems]
  );

  return (
    <AppShell>
      <PageTransition>
        <div ref={containerRef}>
        <PullToRefreshIndicator pullDistance={pullDistance} refreshing={refreshing} />
        <motion.div
          className="space-y-6"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.08 } },
          }}
        >
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            <SectionHeading
              title="Dashboard"
              subtitle="Real-time market overview and breakout signals"
            />
          </motion.div>

          {/* Stat Cards */}
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            {breadthLoading ? (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : (
              <StatCards
                breakoutCount={activeBreakouts.length}
                alertCount={alertCount}
                volumeSurgeCount={volumeItems.length}
                breadth={breadth}
              />
            )}
          </motion.div>

          {/* Main Grid */}
          <motion.div
            className="grid gap-6 xl:grid-cols-3 min-w-0"
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            {/* Left: Breakout Feed */}
            <div className="xl:col-span-2 space-y-6 min-w-0">
              <BreakoutFeed items={activeBreakouts} />
              <VolumeSurges items={volumeItems} />
            </div>

            {/* Right: Breadth + Scan Toggles */}
            <div className="space-y-6">
              <BreadthDonut breadth={breadth} />
              {scansLoading ? (
                <SkeletonCard />
              ) : scans ? (
                <ActiveScanToggles
                  scans={scans}
                  onRunScan={handleRunScan}
                />
              ) : null}
            </div>
          </motion.div>

          {/* Sector Heatmap */}
          <motion.div
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
            }}
          >
            {sectorsLoading ? (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : sectors ? (
              <SectorHeatmap sectors={sectors} />
            ) : null}
          </motion.div>
        </motion.div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
