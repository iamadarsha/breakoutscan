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
  sm: "h-9 px-3 text-xs",
  md: "h-10 sm:h-11 px-4 sm:px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-br from-[#7C5CFC] to-[#5B3FD4] text-white shadow-accent hover:shadow-lg hover:shadow-accent/30",
  secondary:
    "border border-accent/40 bg-accent/5 text-accent hover:bg-accent/10 hover:border-accent/60",
  ghost:
    "text-text-secondary hover:bg-elevated hover:text-text-primary",
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
        "inline-flex items-center justify-center rounded-full font-semibold transition-all duration-200 press-scale disabled:opacity-50 disabled:pointer-events-none",
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

