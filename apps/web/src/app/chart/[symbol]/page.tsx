"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { PriceChart } from "@/components/chart/price-chart";
import { IndicatorPills } from "@/components/chart/indicator-pills";
import { StockSnapshot } from "@/components/chart/stock-snapshot";
import { PanelHeader } from "@/components/ui/panel-header";
import { CompanyInfoPanel } from "@/components/chart/company-info-panel";
import { StockAnalysisCard } from "@/components/chart/stock-analysis-card";
import { useLivePrices } from "@/hooks/use-live-prices";
import { fetchStock, fetchIndicators, fetchLivePrice } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import type { Stock } from "@/lib/api-types";

export default function ChartPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() ?? "RELIANCE";
  const [activeIndicators, setActiveIndicators] = useState<string[]>([]);
  const [chartHeight, setChartHeight] = useState(500);

  useEffect(() => {
    const updateHeight = () => setChartHeight(window.innerWidth < 640 ? 350 : 500);
    updateHeight();
    window.addEventListener("resize", updateHeight);
    return () => window.removeEventListener("resize", updateHeight);
  }, []);

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
        <div className="space-y-4">
          {/* Stock Info */}
          <StockSnapshot stock={stock} livePrice={livePrice} />

          {/* Indicators (interval is switched from the chart's own toolbar) */}
          <IndicatorPills
            active={activeIndicators}
            onToggle={toggleIndicator}
          />

          {/* Main Chart */}
          <PriceChart symbol={symbol} interval="daily" height={chartHeight} />

          {/* AI BUY/SELL/HOLD Call */}
          <StockAnalysisCard key={symbol} symbol={symbol} />

          {/* Company Info */}
          <CompanyInfoPanel symbol={symbol} />

          {/* Indicator Values */}
          {indicators && (
            <div className="rounded-panel border border-border bg-card shadow-card">
              <PanelHeader title="Technical indicators" meta="daily" />
              <div className="grid grid-cols-3 lg:grid-cols-6">
                {[
                  { label: "EMA 9", value: indicators.ema_9 },
                  { label: "EMA 21", value: indicators.ema_21 },
                  { label: "RSI (14)", value: indicators.rsi_14 },
                  { label: "MACD", value: indicators.macd },
                  { label: "ADX (14)", value: indicators.adx_14 },
                  { label: "ATR (14)", value: indicators.atr_14 },
                ].map((ind) => (
                  <div key={ind.label} className="border-b border-r border-border-subtle px-4 py-2.5 last:border-r-0">
                    <div className="text-micro font-semibold uppercase text-text-muted">
                      {ind.label}
                    </div>
                    <div className="font-mono text-data font-medium tabular-nums text-text-primary">
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
