"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "@/components/providers/theme-provider";

interface PriceChartProps {
  symbol?: string;
  interval?: string;
  height?: number;
}

const INTERVAL_MAP: Record<string, string> = {
  "1min": "1",
  "5min": "5",
  "15min": "15",
  daily: "D",
  "1d": "D",
  "1w": "W",
  "1M": "M",
};

export function PriceChart({
  symbol = "RELIANCE",
  interval = "D",
  height = 500,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const tvInterval = INTERVAL_MAP[interval] ?? interval;

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    // TradingView's embed script manipulates the DOM relative to its own
    // <script> tag once it finishes loading (async, off TradingView's CDN).
    // Rebuilding the widget synchronously on every symbol/interval change
    // means rapid navigation (e.g. double-clicking search results) wipes
    // the container out from under a still-loading script, which then
    // throws trying to reach a <script> tag that's already been removed.
    // Debouncing collapses a burst of rapid changes into a single rebuild
    // after things settle, so at most one script is ever in flight.
    const timer = setTimeout(() => {
      container.innerHTML = "";

      const widgetDiv = document.createElement("div");
      widgetDiv.className = "tradingview-widget-container";
      widgetDiv.style.height = `${height}px`;
      widgetDiv.style.width = "100%";

      const innerDiv = document.createElement("div");
      innerDiv.className = "tradingview-widget-container__widget";
      innerDiv.style.height = "100%";
      innerDiv.style.width = "100%";
      widgetDiv.appendChild(innerDiv);

      const script = document.createElement("script");
      script.src =
        "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
      script.type = "text/javascript";
      script.async = true;
      script.textContent = JSON.stringify({
        autosize: true,
        symbol: `BSE:${symbol}`,
        interval: tvInterval,
        timezone: "Asia/Kolkata",
        theme: theme === "dark" ? "dark" : "light",
        style: "1",
        locale: "en",
        backgroundColor:
          theme === "dark" ? "rgba(10, 14, 26, 1)" : "rgba(255, 255, 255, 1)",
        gridColor:
          theme === "dark" ? "rgba(26, 34, 53, 0.5)" : "rgba(230, 232, 240, 0.5)",
        hide_top_toolbar: false,
        hide_legend: false,
        allow_symbol_change: true,
        save_image: false,
        calendar: false,
        studies: ["RSI@tv-basicstudies", "MAExp@tv-basicstudies"],
        support_host: "https://www.tradingview.com",
      });
      widgetDiv.appendChild(script);
      container.appendChild(widgetDiv);
    }, 250);

    return () => {
      clearTimeout(timer);
      container.innerHTML = "";
    };
  }, [symbol, tvInterval, theme, height]);

  return (
    <div
      ref={containerRef}
      className="w-full overflow-hidden rounded-lg border border-border"
      style={{ height: `${height}px` }}
    />
  );
}
