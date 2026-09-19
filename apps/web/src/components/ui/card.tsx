import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = {
  children: ReactNode;
  className?: string;
};

/** Flat surface: hairline border, 10px radius, no hover lift (data doesn't float). */
export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-panel border border-border bg-card p-4 shadow-card",
        className
      )}
    >
      {children}
    </div>
  );
}
