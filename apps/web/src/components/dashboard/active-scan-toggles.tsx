"use client";

import { useState } from "react";
import { Play, Pause } from "lucide-react";
import { cn } from "@/lib/cn";
import { PanelHeader } from "@/components/ui/panel-header";
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
    <div className="glass-card overflow-hidden">
      <PanelHeader title="Quick scans" meta="tap to run" />
      <div className="grid grid-cols-2 gap-1.5 p-3">
        {scans.slice(0, 6).map((scan) => {
          const isActive = activeScans.has(scan.id);
          return (
            <button
              key={scan.id}
              onClick={() => toggleScan(scan.id)}
              aria-pressed={isActive}
              className={cn(
                "flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-data transition-colors",
                isActive
                  ? "border-accent/40 bg-accent/10 text-text-primary"
                  : "border-border bg-card text-text-secondary hover:border-accent/30 hover:bg-accent/5 hover:text-text-primary"
              )}
            >
              {isActive ? (
                <Pause className="h-3.5 w-3.5 shrink-0 text-accent" />
              ) : (
                <Play className="h-3.5 w-3.5 shrink-0 text-text-muted" />
              )}
              <span className="truncate">{scan.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
