import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    // Always associate the label, even when the caller doesn't pass an id.
    const autoId = useId();
    const inputId = id ?? autoId;
    return (
      <div className="flex min-w-0 flex-col gap-1">
        {label && (
          <label
            htmlFor={inputId}
            className="truncate text-micro font-semibold uppercase text-text-muted"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          className={cn(
            "h-9 w-full min-w-0 rounded-lg border border-border bg-card px-3 font-mono text-data tabular-nums text-text-primary placeholder-text-muted outline-none transition-colors",
            "hover:border-accent/40 focus:border-accent focus:shadow-glow",
            error && "border-bearish focus:border-bearish",
            className
          )}
          {...props}
        />
        {error && <span className="text-label text-bearish">{error}</span>}
      </div>
    );
  }
);

Input.displayName = "Input";
