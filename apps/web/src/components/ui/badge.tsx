import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

type BadgeVariant = "bullish" | "bearish" | "neutral" | "accent" | "warning";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

// Tinted fill + same-hue text, no border: reads as a status, not a button.
const variantStyles: Record<BadgeVariant, string> = {
  bullish: "bg-bullish/10 text-bullish",
  bearish: "bg-bearish/10 text-bearish",
  neutral: "bg-text-secondary/10 text-text-secondary",
  accent: "bg-accent/10 text-accent",
  warning: "bg-warning/10 text-warning",
};

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-label font-semibold tabular-nums",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
