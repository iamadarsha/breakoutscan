import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
}

/** Page title: the only text on a screen at the `title` size. */
export function SectionHeading({
  title,
  subtitle,
  action,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-3", className)}>
      <div className="min-w-0 flex-1">
        <h1 className="text-title font-semibold text-text-primary">{title}</h1>
        {subtitle && <p className="mt-0.5 text-data text-text-secondary">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
