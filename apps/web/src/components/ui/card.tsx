import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = {
  children: ReactNode;
  className?: string;
  hover?: boolean;
};

export function Card({ children, className = "", hover = true }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-panel border border-border bg-card backdrop-blur-md shadow-glass p-4 sm:p-5 transition-all duration-300 ease-out",
        hover && "hover:-translate-y-0.5 hover:border-accent/20 hover:shadow-glow ambient-glow",
        className
      )}
    >
      {children}
    </div>
  );
}

