"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { PriceChart } from "@/components/chart/price-chart";
import { TimeframeTabs } from "@/components/chart/timeframe-tabs";
import { IndicatorPills } from "@/components/chart/indicator-pills";
import { StockSnapshot } from "@/components/chart/stock-snapshot";
import { CompanyInfoPanel } from "@/components/chart/company-info-panel";
import { StockAnalysisCard } from "@/components/chart/stock-analysis-card";
import { useLivePrices } from "@/hooks/use-live-prices";
import { fetchStock, fetchIndicators, fetchStocks, fetchLivePrice } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import type { Stock } from "@/lib/api-types";
import { cn } from "@/lib/cn";

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string)?.toUpperCase() ?? "RELIANCE";
  const [timeframe, setTimeframe] = useState("daily");
  const [activeIndicators, setActiveIndicators] = useState<string[]>([]);
  const [chartSearch, setChartSearch] = useState("");
  const [chartSuggestions, setChartSuggestions] = useState<Stock[]>([]);
  const [showChartDropdown, setShowChartDropdown] = useState(false);
  const [chartSelectedIdx, setChartSelectedIdx] = useState(-1);
  const chartDebounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [chartHeight, setChartHeight] = useState(500);

  useEffect(() => {
    const updateHeight = () => setChartHeight(window.innerWidth < 640 ? 350 : 500);
    updateHeight();
    window.addEventListener("resize", updateHeight);
    return () => window.removeEventListener("resize", updateHeight);
  }, []);

  const searchChartStocks = useCallback((query: string) => {
    if (chartDebounceRef.current) clearTimeout(chartDebounceRef.current);
    if (query.length < 1) {
      setChartSuggestions([]);
      setShowChartDropdown(false);
      return;
    }

    // Instant local results first
    const local = searchLocalStocks(query, 10);
    if (local.length > 0) {
      setChartSuggestions(local.map((s) => ({ symbol: s.symbol, name: s.name, sector: s.sector }) as Stock));
      setShowChartDropdown(true);
      setChartSelectedIdx(-1);
    }

    // Then try API for potentially better results
    chartDebounceRef.current = setTimeout(async () => {
      try {
        const res = await fetchStocks({ search: query, limit: 10 });
        if (res.stocks && res.stocks.length > 0) {
          setChartSuggestions(res.stocks);
          setShowChartDropdown(true);
          setChartSelectedIdx(-1);
        }
      } catch {
        // Local results already shown — no-op
      }
    }, 300);
  }, []);

  const navigateToSymbol = useCallback(
    (sym: string) => {
      router.push(`/chart/${sym.toUpperCase()}`);
      setChartSearch("");
      setChartSuggestions([]);
      setShowChartDropdown(false);
    },
    [router]
  );

  const livePrices = useLivePrices([symbol]);
  const wsPrice = livePrices[symbol];

  // REST fallback for when WebSocket doesn't deliver (e.g. market closed)
  const { data: restPrice } = useQuery({
    queryKey: ["livePrice", symbol],
    queryFn: () => fetchLivePrice(symbol),
    retry: 0,
    staleTime: 30_000,
    enabled: !wsPrice,
  });
  const livePrice = wsPrice ?? restPrice;

  // Use local NSE data as immediate placeholder while API loads
  const localStock = searchLocalStocks(symbol, 1)[0];
  const placeholderStock: Stock | undefined = localStock
    ? { symbol: localStock.symbol, name: localStock.name, sector: localStock.sector ?? "", industry: "", market_cap: 0, is_nifty50: false, is_nifty500: false }
    : undefined;

  const { data: stockData } = useQuery({
    queryKey: ["stock", symbol],
    queryFn: () => fetchStock(symbol),
    placeholderData: placeholderStock,
    retry: 0,
    staleTime: 60_000,
  });
  const stock = stockData ?? placeholderStock;

  const { data: indicators } = useQuery({
    queryKey: ["indicators", symbol],
    queryFn: () => fetchIndicators(symbol),
  });

  const toggleIndicator = (ind: string) => {
    setActiveIndicators((prev) =>
      prev.includes(ind) ? prev.filter((i) => i !== ind) : [...prev, ind]
    );
  };

  return (
    <AppShell>
      <PageTransition>
        <div className="space-y-3 sm:space-y-4">
          {/* Symbol Search */}
          <div className="relative z-20 max-w-md">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (chartSelectedIdx >= 0 && chartSuggestions[chartSelectedIdx]) {
                  navigateToSymbol(chartSuggestions[chartSelectedIdx].symbol);
                } else if (chartSearch.trim()) {
                  navigateToSymbol(chartSearch.trim());
                }
              }}
            >
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted z-10" />
              <input
                type="text"
                value={chartSearch}
                onChange={(e) => {
                  setChartSearch(e.target.value);
                  searchChartStocks(e.target.value);
                }}
                onFocus={() => chartSuggestions.length > 0 && setShowChartDropdown(true)}
                onBlur={() => setTimeout(() => setShowChartDropdown(false), 200)}
                onKeyDown={(e) => {
                  if (!showChartDropdown || chartSuggestions.length === 0) return;
                  if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setChartSelectedIdx((prev) => (prev < chartSuggestions.length - 1 ? prev + 1 : 0));
                  } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setChartSelectedIdx((prev) => (prev > 0 ? prev - 1 : chartSuggestions.length - 1));
                  } else if (e.key === "Escape") {
                    setShowChartDropdown(false);
                  }
                }}
                placeholder="Search stocks... e.g. RELIANCE, TCS, INFY"
                className="h-10 w-full rounded-lg border border-border bg-card pl-10 pr-4 text-sm text-text-primary placeholder-text-muted outline-none transition focus:border-accent"
              />
            </form>
            {showChartDropdown && chartSuggestions.length > 0 && (
              <div className="absolute left-0 top-full z-50 mt-1 w-full max-h-[320px] overflow-y-auto rounded-lg border border-border shadow-lg" style={{ backgroundColor: '#0d1117' }}>
                {chartSuggestions.map((s, i) => (
                  <button
                    key={s.symbol}
                    type="button"
                    onMouseDown={() => navigateToSymbol(s.symbol)}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-card",
                      i === chartSelectedIdx && "bg-card"
                    )}
                  >
                    <span className="font-mono font-semibold text-accent">{s.symbol}</span>
                    <span className="truncate text-text-secondary">{s.name}</span>
                    <span className="ml-auto text-xs text-text-muted">{s.sector}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Stock Info */}
          <StockSnapshot stock={stock} livePrice={livePrice} />

          {/* Chart Controls */}
          <div className="flex flex-wrap items-center gap-2 sm:justify-between sm:gap-3">
            <TimeframeTabs active={timeframe} onChange={setTimeframe} />
            <IndicatorPills
              active={activeIndicators}
              onToggle={toggleIndicator}
            />
          </div>

          {/* Main Chart */}
          <PriceChart symbol={symbol} interval={timeframe} height={chartHeight} />

          {/* AI BUY/SELL/HOLD Call */}
          <StockAnalysisCard key={symbol} symbol={symbol} />

          {/* Company Info */}
          <CompanyInfoPanel symbol={symbol} />

          {/* Indicator Values */}
          {indicators && (
            <div className="rounded-panel border border-border bg-card p-3 sm:p-5">
              <h3 className="mb-2 sm:mb-3 text-xs sm:text-sm font-semibold text-text-primary">
                Technical Indicators
              </h3>
              <div className="grid grid-cols-3 gap-3 sm:gap-4 lg:grid-cols-6">
                {[
                  { label: "EMA 9", value: indicators.ema_9 },
                  { label: "EMA 21", value: indicators.ema_21 },
                  { label: "RSI (14)", value: indicators.rsi_14 },
                  { label: "MACD", value: indicators.macd },
                  { label: "ADX (14)", value: indicators.adx_14 },
                  { label: "ATR (14)", value: indicators.atr_14 },
                ].map((ind) => (
                  <div key={ind.label}>
                    <div className="text-[10px] uppercase tracking-wider text-text-muted">
                      {ind.label}
                    </div>
                    <div className="mt-0.5 font-mono text-sm text-text-primary">
                      {ind.value?.toFixed(2) ?? "-"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </PageTransition>
    </AppShell>
  );
}
