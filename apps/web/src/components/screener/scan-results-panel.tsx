"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { motion } from "framer-motion";
import { SortableResultsTable } from "./sortable-results-table";
import { Badge } from "@/components/ui/badge";
import type { ScanResult } from "@/lib/api-types";
import { formatTime } from "@/lib/format";

interface ScanResultsPanelProps {
  result: ScanResult;
  onClose: () => void;
}

export function ScanResultsPanel({ result, onClose }: ScanResultsPanelProps) {
  const ref = useRef<HTMLDivElement>(null);

  // Bring the results into view as soon as a scan finishes.
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="glass-card scroll-mt-28 overflow-hidden"
    >
      <div className="flex min-h-[44px] items-center justify-between border-b border-border px-4 py-2">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <h3 className="text-panel font-semibold text-text-primary">
            {result.scan_name}
          </h3>
          <Badge variant="neutral">{result.total_matches} results</Badge>
          {result.run_at && (
            <span className="text-label text-text-muted">
              {formatTime(result.run_at)}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close results"
          className="rounded-lg p-2 text-text-secondary transition-colors hover:bg-elevated hover:text-text-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <SortableResultsTable items={result.items ?? []} />
    </motion.div>
  );
}
