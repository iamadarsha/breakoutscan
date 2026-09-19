import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { haptic } from "@/lib/haptic";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-label",
  md: "h-9 px-4 text-data",
  lg: "h-11 px-6 text-panel",
};

// Only ONE solid accent button should be visible per screen — it marks the primary action.
const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-accent-solid text-white shadow-accent hover:bg-accent-solid-hover",
  secondary:
    "border border-border bg-card text-text-primary hover:border-accent/50 hover:bg-accent/5",
  ghost: "text-text-secondary hover:bg-elevated hover:text-text-primary",
};

export function Button({
  children,
  className = "",
  variant = "primary",
  size = "md",
  onClick,
  ...props
}: ButtonProps) {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    haptic("light");
    onClick?.(e);
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition-colors duration-150 press-scale disabled:pointer-events-none disabled:opacity-50",
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
