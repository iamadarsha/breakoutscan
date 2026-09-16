"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Filter, RotateCcw } from "lucide-react";
import type { FundamentalFilters } from "@/lib/api-types";

interface FilterSidebarProps {
  filters: FundamentalFilters;
  onChange: (filters: FundamentalFilters) => void;
  onApply: () => void;
  onReset: () => void;
}

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
}: FilterSidebarProps) {
  const handleChange = (key: keyof FundamentalFilters, value: string) => {
    const num = value === "" ? undefined : Number(value);
    onChange({ ...filters, [key]: num });
  };

  return (
    <div className="rounded-panel border border-border bg-card p-5">
      <div className="mb-4 flex items-center gap-2">
        <Filter className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">Filters</h3>
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
