"use client";

import { useId, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";
import type { SectorData } from "@/lib/api-types";

interface SectorHeatmapProps {
  sectors: SectorData[];
}

type Rgb = [number, number, number];

const DEEP_GREEN: Rgb = [4, 120, 87];
const NEUTRAL: Rgb = [226, 230, 238];
const DEEP_RED: Rgb = [159, 18, 57];
/** Moves at or beyond this size get the fully saturated colour. */
const FULL_SCALE_PCT = 3;
const PREVIEW_COUNT = 3;

function mix(a: Rgb, b: Rgb, t: number): Rgb {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

/** Continuous deep-red <- neutral -> deep-green scale, so 2.9% looks nearly as strong as 3%. */
function heatRgb(changePct: number): Rgb {
  const t = Math.max(-1, Math.min(1, changePct / FULL_SCALE_PCT));
  return t >= 0 ? mix(NEUTRAL, DEEP_GREEN, t) : mix(NEUTRAL, DEEP_RED, -t);
}

function luminance([r, g, b]: Rgb): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function heatStyle(changePct: number): { background: string; color: string } {
  const rgb = heatRgb(changePct);
  return {
    background: `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`,
    color: luminance(rgb) > 0.32 ? "#0f172a" : "#ffffff",
  };
}

function PreviewChip({ sector }: { sector: SectorData }) {
  const style = heatStyle(sector.change_pct);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-label font-semibold"
      style={style}
    >
      <span className="max-w-[140px] truncate">{sector.sector}</span>
      <span className="font-mono tabular-nums">{formatPercent(sector.change_pct, 1)}</span>
    </span>
  );
}

export function SectorHeatmap({ sectors }: SectorHeatmapProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  const sorted = useMemo(
    () => [...sectors].sort((a, b) => b.change_pct - a.change_pct),
    [sectors]
  );
  const leaders = sorted.slice(0, PREVIEW_COUNT);
  const laggards = sorted
    .slice(Math.max(PREVIEW_COUNT, sorted.length - PREVIEW_COUNT))
    .reverse();

  return (
    <div className="glass-card rounded-panel p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="-my-2 flex min-h-[44px] w-full items-center justify-between gap-3 text-left"
      >
        <span className="flex items-baseline gap-2">
          <span className="text-data font-semibold text-text-primary">Sector Performance</span>
          <span className="text-label text-text-muted">{sectors.length} sectors</span>
        </span>
        <span className="flex items-center gap-1.5 text-label font-medium text-text-muted">
          {open ? "Hide" : "Show all"}
          <ChevronDown
            className={cn("h-4 w-4 transition-transform duration-300", open && "rotate-180")}
          />
        </span>
      </button>

      {sectors.length === 0 && (
        <div className="py-12 text-center text-data text-text-muted">
          No sector data available
        </div>
      )}

      {sectors.length > 0 && !open && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {leaders.map((s) => (
            <PreviewChip key={s.sector} sector={s} />
          ))}
          <span className="px-1 text-text-muted">···</span>
          {laggards.map((s) => (
            <PreviewChip key={s.sector} sector={s} />
          ))}
        </div>
      )}

      <div
        id={panelId}
        className={cn(
          "grid transition-[grid-template-rows] duration-300 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <div className="grid grid-cols-2 gap-2 pt-4 sm:grid-cols-3 lg:grid-cols-4">
            {open &&
              sorted.map((sector) => (
                <div
                  key={sector.sector}
                  style={heatStyle(sector.change_pct)}
                  className="flex flex-col items-center justify-center rounded-lg px-3 py-3 text-center shadow-sm transition-transform hover:scale-[1.02]"
                >
                  <span className="text-label font-semibold leading-tight">{sector.sector}</span>
                  <span className="mt-1.5 font-mono text-lg font-bold tabular-nums">
                    {formatPercent(sector.change_pct, 1)}
                  </span>
                  <span className="mt-2 flex gap-3 text-micro font-medium opacity-80">
                    <span>▲ {sector.advances}</span>
                    <span>▼ {sector.declines}</span>
                  </span>
                  {sector.top_gainer && sector.top_loser && (
                    <span className="mt-1 max-w-full truncate text-micro opacity-70">
                      {sector.top_gainer} / {sector.top_loser}
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
