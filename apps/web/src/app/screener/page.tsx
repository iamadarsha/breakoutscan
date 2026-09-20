"use client";
import { track } from "@/lib/analytics";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { PrebuiltScanGrid } from "@/components/screener/prebuilt-scan-grid";
import { ScanResultsPanel } from "@/components/screener/scan-results-panel";
import { CustomScanBuilder } from "@/components/screener/custom-scan-builder";
import { SkeletonTable } from "@/components/ui/skeleton";
import {
  usePrebuiltScans,
  useRunPrebuiltScan,
  useRunCustomScan,
} from "@/hooks/use-scan-run";
import type { ScanResult, CustomScanCondition } from "@/lib/api-types";

export default function ScreenerPage() {
  const { data: scans, isLoading: scansLoading } = usePrebuiltScans();
  const runPrebuilt = useRunPrebuiltScan();
  const runCustom = useRunCustomScan();
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);

  const closeResults = () => {
    setResult(null);
    setActiveScanId(null);
  };

  const handleRunPrebuilt = (scanId: string) => {
    if (runPrebuilt.isPending) return;
    setActiveScanId(scanId);
    setResult(null);
    runPrebuilt.mutate(scanId, {
      onSuccess: (data) => {
        // Counted here, not in the API layer: the dashboard also runs scans on its own in the background.
        track("scan_run", { scan_id: scanId, kind: "prebuilt", matches: data?.total_matches ?? 0 });
        setResult(data);
      },
    });
  };

  const handleRunCustom = (
    conditions: CustomScanCondition[],
    universe: string,
    timeframe: string
  ) => {
    setActiveScanId("custom");
    runCustom.mutate(
      { conditions, universe, timeframe },
      {
        onSuccess: (data) => {
          track("scan_run", { scan_id: "custom", kind: "custom", matches: data?.total_matches ?? 0 });
          setResult(data);
        },
      }
    );
  };

  return (
    <AppShell>
      <PageTransition>
        <div className="space-y-5">
          <SectionHeading
            title="Screener"
            subtitle="Run prebuilt scans or build your own custom conditions"
          />

          {/* Prebuilt Scans Grid */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <h3 className="mb-2 flex items-baseline gap-2 text-panel font-semibold text-text-primary">
              Prebuilt scans
              <span className="text-label font-normal text-text-muted">
                {scans ? `${scans.length} ready to run` : ""}
              </span>
            </h3>
            {scansLoading ? (
              <SkeletonTable rows={3} />
            ) : (
              <PrebuiltScanGrid
                scans={scans ?? []}
                activeScanId={activeScanId}
                onRunScan={handleRunPrebuilt}
                isLoading={runPrebuilt.isPending}
                results={
                  <AnimatePresence>
                    {result && activeScanId !== "custom" && (
                      <ScanResultsPanel result={result} onClose={closeResults} />
                    )}
                  </AnimatePresence>
                }
              />
            )}
          </motion.div>

          {/* Custom Scan Builder */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <CustomScanBuilder
              onRun={handleRunCustom}
              isLoading={runCustom.isPending}
            />
          </motion.div>

          {/* Custom scan results sit under the builder that produced them */}
          <AnimatePresence>
            {result && activeScanId === "custom" && (
              <ScanResultsPanel result={result} onClose={closeResults} />
            )}
          </AnimatePresence>
        </div>
      </PageTransition>
    </AppShell>
  );
}
