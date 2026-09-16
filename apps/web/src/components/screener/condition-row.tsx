"use client";

import { Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";

const INDICATORS = [
  { value: "close", label: "Close Price" },
  { value: "volume", label: "Volume" },
  { value: "rsi", label: "RSI (14)" },
  { value: "ema20", label: "EMA (20)" },
  { value: "ema50", label: "EMA (50)" },
  { value: "macd", label: "MACD" },
  { value: "macd_signal", label: "MACD Signal" },
  { value: "bb_upper", label: "BB Upper" },
  { value: "bb_lower", label: "BB Lower" },
  { value: "atr", label: "ATR" },
  { value: "adx", label: "ADX" },
  { value: "change_pct", label: "Change %" },
];

const OPERATORS = [
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
  { value: "eq", label: "=" },
  { value: "crosses_above", label: "Crosses Above" },
  { value: "crosses_below", label: "Crosses Below" },
];

interface ConditionRowProps {
  indicator: string;
  operator: string;
  value: string;
  onChange: (field: "indicator" | "operator" | "value", val: string) => void;
  onRemove: () => void;
  canRemove?: boolean;
}

export function ConditionRow({
  indicator,
  operator,
  value,
  onChange,
  onRemove,
  canRemove = true,
}: ConditionRowProps) {
  const selectClass = cn(
    "h-9 rounded-lg border border-border bg-page px-3 text-sm text-text-primary outline-none transition",
    "focus:border-accent focus:ring-1 focus:ring-accent-glow",
    "hover:border-border"
  );

  return (
    <div className="flex items-center gap-2">
      <select
        value={indicator}
        onChange={(e) => onChange("indicator", e.target.value)}
        className={cn(selectClass, "flex-[2]")}
      >
        {INDICATORS.map((ind) => (
          <option key={ind.value} value={ind.value}>
            {ind.label}
          </option>
        ))}
      </select>

      <select
        value={operator}
        onChange={(e) => onChange("operator", e.target.value)}
        className={cn(selectClass, "flex-1")}
      >
        {OPERATORS.map((op) => (
          <option key={op.value} value={op.value}>
            {op.label}
          </option>
        ))}
      </select>

      <input
        type="text"
        value={value}
        onChange={(e) => onChange("value", e.target.value)}
        placeholder="Value"
        className={cn(
          "h-9 flex-1 rounded-lg border border-border bg-page px-3 text-sm text-text-primary placeholder-text-muted outline-none transition",
          "focus:border-accent focus:ring-1 focus:ring-accent-glow"
        )}
      />

      <button
        onClick={onRemove}
        disabled={!canRemove}
        className={cn(
          "rounded-full p-2 transition",
          canRemove
            ? "text-text-secondary hover:bg-elevated hover:text-bearish"
            : "cursor-not-allowed text-border"
        )}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}
