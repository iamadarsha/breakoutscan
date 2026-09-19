"use client";

import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PanelHeader } from "@/components/ui/panel-header";
import { fetchStocks } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import { cn } from "@/lib/cn";
import { haptic } from "@/lib/haptic";
import type { AlertCreateRequest, AlertFrequency } from "@/lib/api-types";

interface AlertFormProps {
  onSubmit: (req: AlertCreateRequest) => void;
  isLoading?: boolean;
}

const FREQUENCIES: { value: AlertFrequency; label: string; hint: string }[] = [
  { value: "once", label: "Once", hint: "First confirmed breakout, then stops" },
  { value: "every_time", label: "Every time", hint: "Every confirmed breakout" },
  { value: "daily_digest", label: "Daily digest", hint: "First breakout each day" },
];

export function AlertForm({ onSubmit, isLoading }: AlertFormProps) {
  const symbolId = useId();
  const [symbolSearch, setSymbolSearch] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [frequency, setFrequency] = useState<AlertFrequency>("once");
  const [showDropdown, setShowDropdown] = useState(false);

  const { data: searchData } = useQuery({
    queryKey: ["alert-stock-search", symbolSearch],
    queryFn: () => fetchStocks({ search: symbolSearch, limit: 8 }),
    enabled: symbolSearch.length >= 2 && showDropdown,
    retry: 0,
  });

  // Instant local matches first; API results replace them when available.
  const suggestions =
    searchData?.stocks && searchData.stocks.length > 0
      ? searchData.stocks.map((s) => ({ symbol: s.symbol, name: s.name }))
      : symbolSearch.length >= 1
        ? searchLocalStocks(symbolSearch, 8).map((s) => ({ symbol: s.symbol, name: s.name }))
        : [];

  const handleSubmit = () => {
    if (!selectedSymbol) return;
    haptic("medium");
    onSubmit({ symbol: selectedSymbol, frequency });
    setSelectedSymbol("");
    setSymbolSearch("");
  };

  const activeHint = FREQUENCIES.find((f) => f.value === frequency)?.hint;

  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader title="New breakout alert" />
      <div className="space-y-4 p-4">
        <div className="relative">
          <label htmlFor={symbolId} className="mb-1 block text-micro font-semibold uppercase text-text-muted">
            Stock
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" />
            <input
              id={symbolId}
              type="text"
              value={selectedSymbol || symbolSearch}
              onChange={(e) => {
                setSymbolSearch(e.target.value);
                setSelectedSymbol("");
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
              placeholder="Search a symbol, e.g. RELIANCE"
              autoComplete="off"
              className="h-9 w-full rounded-lg border border-border bg-card pl-9 pr-3 text-data text-text-primary placeholder-text-muted outline-none transition-colors hover:border-accent/40 focus:border-accent focus:shadow-glow"
            />
          </div>
          {showDropdown && suggestions.length > 0 && !selectedSymbol && (
            <div className="absolute z-10 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-border bg-card shadow-pop">
              {suggestions.map((s) => (
                <button
                  key={s.symbol}
                  type="button"
                  onMouseDown={() => {
                    setSelectedSymbol(s.symbol);
                    setSymbolSearch("");
                    setShowDropdown(false);
                  }}
                  className="flex w-full items-baseline gap-2 px-3 py-2 text-left text-data transition-colors hover:bg-accent/5"
                >
                  <span className="font-mono font-semibold text-text-primary">{s.symbol}</span>
                  <span className="truncate text-label text-text-secondary">{s.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <fieldset>
          <legend className="mb-1 text-micro font-semibold uppercase text-text-muted">Notify me</legend>
          <div className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-elevated p-0.5">
            {FREQUENCIES.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setFrequency(f.value)}
                aria-pressed={frequency === f.value}
                className={cn(
                  "h-8 rounded-md text-label font-semibold transition-colors",
                  frequency === f.value
                    ? "bg-card text-text-primary shadow-card"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-label text-text-muted">{activeHint}</p>
        </fieldset>

        <Button onClick={handleSubmit} disabled={!selectedSymbol || isLoading} className="w-full">
          {isLoading ? "Creating…" : "Create alert"}
        </Button>
      </div>
    </div>
  );
}
