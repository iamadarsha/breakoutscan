"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { fetchStocks } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import { cn } from "@/lib/cn";

interface AddStockModalProps {
  open: boolean;
  onClose: () => void;
  onAdd: (symbol: string) => void;
  existingSymbols: string[];
}

export function AddStockModal({
  open,
  onClose,
  onAdd,
  existingSymbols,
}: AddStockModalProps) {
  const [search, setSearch] = useState("");

  // Instant local results
  const localResults = useMemo(
    () => (search.length >= 1 ? searchLocalStocks(search, 20) : []),
    [search]
  );

  // API results (may take longer / may fail) — guarded with retry:0 and staleTime
  const { data } = useQuery({
    queryKey: ["stocks-search", search],
    queryFn: () => fetchStocks({ search, limit: 20 }),
    enabled: open && search.length >= 2,
    staleTime: 60_000,
    retry: 0,
    gcTime: 60_000,
  });

  // Merge: prefer API results if available, otherwise use local
  const stocks = useMemo(() => {
    const apiStocks = data?.stocks ?? [];
    if (apiStocks.length > 0) return apiStocks;
    return localResults.map((s) => ({
      symbol: s.symbol,
      name: s.name,
      sector: s.sector,
    }));
  }, [data, localResults]);

  return (
    <Modal open={open} onClose={onClose} title="Add Stock to Watchlist">
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by symbol or name..."
          autoFocus
          className="h-10 w-full rounded-lg border border-border bg-card pl-10 pr-3 text-data text-text-primary placeholder-text-muted outline-none transition-colors hover:border-accent/40 focus:border-accent focus:shadow-glow"
          aria-label="Search stocks to add"
        />
      </div>

      <div className="max-h-64 overflow-y-auto">
        {stocks.map((stock) => {
          const isAdded = existingSymbols.includes(stock.symbol);
          return (
            <button
              key={stock.symbol}
              disabled={isAdded}
              onClick={() => {
                onAdd(stock.symbol);
                onClose();
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors",
                isAdded
                  ? "cursor-not-allowed opacity-40"
                  : "hover:bg-accent/5"
              )}
            >
              <div>
                <span className="font-mono text-data font-semibold text-text-primary">
                  {stock.symbol}
                </span>
                <div className="text-label text-text-secondary">{stock.name}</div>
              </div>
              {isAdded ? (
                <span className="text-label text-text-muted">Added</span>
              ) : (
                <Plus className="h-4 w-4 text-accent" />
              )}
            </button>
          );
        })}
        {search.length >= 1 && stocks.length === 0 && (
          <div className="py-8 text-center text-data text-text-muted">
            No stocks found
          </div>
        )}
        {search.length === 0 && (
          <div className="py-8 text-center text-data text-text-muted">
            Type to search for stocks
          </div>
        )}
      </div>
    </Modal>
  );
}
