import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface PanelHeaderProps {
  title: string;
  /** Quiet context next to the title: counts, "as of" time, units. */
  meta?: ReactNode;
  /** Right-aligned control: a filter, toggle or link. */
  action?: ReactNode;
  className?: string;
}

/**
 * The single header every data panel uses, so the eye learns one pattern:
 * title (semibold) → meta (muted) ··· action. A hairline separates it from data.
 */
export function PanelHeader({ title, meta, action, className }: PanelHeaderProps) {
  return (
    <div
      className={cn(
        "flex min-h-[44px] items-center gap-3 border-b border-border px-4 py-2.5",
        className
      )}
    >
      <h3 className="text-panel font-semibold text-text-primary">{title}</h3>
      {meta && <span className="text-label text-text-muted">{meta}</span>}
      {action && <div className="ml-auto flex items-center gap-2">{action}</div>}
    </div>
  );
}
