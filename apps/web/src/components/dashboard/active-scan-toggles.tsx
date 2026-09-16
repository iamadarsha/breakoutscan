"use client";

import { useState } from "react";
import { Play, Pause } from "lucide-react";
import { cn } from "@/lib/cn";
import type { PrebuiltScan } from "@/lib/api-types";

interface ActiveScanTogglesProps {
  scans: PrebuiltScan[];
  onRunScan: (scanId: string) => void;
}

export function ActiveScanToggles({ scans, onRunScan }: ActiveScanTogglesProps) {
  const [activeScans, setActiveScans] = useState<Set<string>>(new Set());

  const toggleScan = (scanId: string) => {
    setActiveScans((prev) => {
      const next = new Set(prev);
      if (next.has(scanId)) {
        next.delete(scanId);
      } else {
        next.add(scanId);
        onRunScan(scanId);
      }
      return next;
    });
  };

  return (
    <div className="glass-card rounded-panel p-5">
      <h3 className="mb-4 text-sm font-semibold text-text-primary">Active Scans</h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {scans.slice(0, 6).map((scan) => {
          const isActive = activeScans.has(scan.id);
          return (
            <button
              key={scan.id}
              onClick={() => toggleScan(scan.id)}
              className={cn(
                "flex items-center gap-2 rounded-full border px-3 py-2.5 text-left text-sm transition",
                isActive
                  ? "border-accent bg-accent/10 text-text-primary"
                  : "border-border bg-page text-text-secondary hover:border-border hover:text-text-primary"
              )}
            >
              {isActive ? (
                <Pause className="h-3.5 w-3.5 shrink-0 text-accent" />
              ) : (
                <Play className="h-3.5 w-3.5 shrink-0" />
              )}
              <span className="truncate text-xs">{scan.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
