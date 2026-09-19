"use client";

import { INDICATOR_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/cn";

interface IndicatorPillsProps {
  active: string[];
  onToggle: (indicator: string) => void;
}

export function IndicatorPills({ active, onToggle }: IndicatorPillsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {INDICATOR_OPTIONS.map((opt) => {
        const isActive = active.includes(opt.value);
        return (
          <button
            key={opt.value}
            onClick={() => onToggle(opt.value)}
            aria-pressed={isActive}
            className={cn(
              "rounded-md border px-3 py-2 text-label font-medium transition-colors lg:py-1",
              isActive
                ? "border-accent/50 bg-accent/10 text-accent"
                : "border-border bg-card text-text-secondary hover:border-accent/40 hover:text-text-primary"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
