"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Filter, RotateCcw, Sparkles } from "lucide-react";
import type { FundamentalFilters } from "@/lib/api-types";
import { cn } from "@/lib/cn";

interface FilterSidebarProps {
  filters: FundamentalFilters;
  onChange: (filters: FundamentalFilters) => void;
  onApply: () => void;
  onReset: () => void;
  onApplyPreset: (name: string, filters: FundamentalFilters) => void;
  activePreset?: string | null;
}

/** A handful of the most commonly used screener.in-style value/quality/
 * income screens, mapped onto the filter fields this app actually has.
 * Not a clone of screener.in's own scoring — same well-known screening
 * concepts (low PE, high ROE, low debt, etc.), applied to our live data. */
const PRESET_SCREENS: { name: string; description: string; filters: FundamentalFilters }[] = [
  {
    name: "Low PE (Value)",
    description: "Cheap relative to earnings",
    filters: { pe_min: 0, pe_max: 15 },
  },
  {
    name: "High ROE (Quality)",
    description: "Efficient at generating profit",
    filters: { roe_min: 20 },
  },
  {
    name: "Low Debt",
    description: "Conservative balance sheets",
    filters: { debt_to_equity_max: 0.2 },
  },
  {
    name: "High Dividend Yield",
    description: "Income-focused picks",
    filters: { dividend_yield_min: 3 },
  },
  {
    name: "Undervalued Growth",
    description: "Low price-to-book, decent ROE",
    filters: { pb_max: 1.5, roe_min: 12 },
  },
  {
    name: "Quality Large Caps",
    description: "Big, profitable, low debt",
    filters: { market_cap_min: 20000, roe_min: 15, debt_to_equity_max: 0.5 },
  },
];

const filterFields: {
  key: keyof FundamentalFilters;
  label: string;
  placeholder: string;
}[] = [
  { key: "pe_min", label: "PE Min", placeholder: "e.g. 5" },
  { key: "pe_max", label: "PE Max", placeholder: "e.g. 30" },
  { key: "pb_min", label: "PB Min", placeholder: "e.g. 0.5" },
  { key: "pb_max", label: "PB Max", placeholder: "e.g. 5" },
  { key: "market_cap_min", label: "Market Cap Min (Cr)", placeholder: "e.g. 1000" },
  { key: "market_cap_max", label: "Market Cap Max (Cr)", placeholder: "e.g. 100000" },
  { key: "roe_min", label: "ROE Min (%)", placeholder: "e.g. 15" },
  { key: "dividend_yield_min", label: "Div Yield Min (%)", placeholder: "e.g. 1" },
  { key: "debt_to_equity_max", label: "D/E Max", placeholder: "e.g. 1" },
];

export function FilterSidebar({
  filters,
  onChange,
  onApply,
  onReset,
  onApplyPreset,
  activePreset,
}: FilterSidebarProps) {
  const handleChange = (key: keyof FundamentalFilters, value: string) => {
    const num = value === "" ? undefined : Number(value);
    onChange({ ...filters, [key]: num });
  };

  return (
    <div className="rounded-panel border border-border bg-card p-5">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">Popular Screens</h3>
      </div>
      <div className="mb-5 space-y-1.5">
        {PRESET_SCREENS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            onClick={() => onApplyPreset(preset.name, preset.filters)}
            className={cn(
              "flex w-full flex-col items-start rounded-xl border px-3 py-2 text-left transition",
              activePreset === preset.name
                ? "border-accent bg-accent/10"
                : "border-border/60 hover:border-accent/40 hover:bg-elevated"
            )}
          >
            <span className="text-xs font-semibold text-text-primary">{preset.name}</span>
            <span className="text-[10px] text-text-muted">{preset.description}</span>
          </button>
        ))}
      </div>

      <div className="mb-4 flex items-center gap-2 border-t border-border/60 pt-4">
        <Filter className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">Custom Filters</h3>
      </div>

      <div className="space-y-3">
        {filterFields.map((field) => (
          <Input
            key={field.key}
            label={field.label}
            type="number"
            placeholder={field.placeholder}
            value={filters[field.key] ?? ""}
            onChange={(e) => handleChange(field.key, e.target.value)}
          />
        ))}
      </div>

      <div className="mt-5 flex gap-2">
        <Button onClick={onApply} className="flex-1">
          Apply Filters
        </Button>
        <button
          onClick={onReset}
          className="rounded-full border border-border p-2.5 text-text-secondary transition hover:bg-elevated hover:text-text-primary"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
