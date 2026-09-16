"use client";

import { TIMEFRAME_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/cn";

const INTRADAY_VALUES = new Set(["1min", "5min", "15min"]);

interface TimeframeTabsProps {
  active: string;
  onChange: (tf: string) => void;
}

export function TimeframeTabs({ active, onChange }: TimeframeTabsProps) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-page p-1">
      {TIMEFRAME_OPTIONS.map((opt) => {
        const isDisabled = INTRADAY_VALUES.has(opt.value);
        return (
          <button
            key={opt.value}
            onClick={() => !isDisabled && onChange(opt.value)}
            disabled={isDisabled}
            title={isDisabled ? "Intraday charts coming soon" : undefined}
            className={cn(
              "rounded-full px-3 py-1.5 text-xs font-semibold transition",
              isDisabled
                ? "cursor-not-allowed text-text-muted opacity-40"
                : active === opt.value
                  ? "bg-accent text-white"
                  : "text-text-secondary hover:text-text-primary"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
