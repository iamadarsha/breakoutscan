"use client";

import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { QueryClientProvider } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/query-client";
import { ThemeProvider, ThemedToaster } from "@/components/providers/theme-provider";
import { AnalyticsProvider } from "@/components/providers/analytics-provider";
import type { ReactNode } from "react";

import "./globals.css";

// IBM Plex: engineered for dense data UIs. Plex Sans has tabular figures and a
// clear 1/l/I; Plex Mono carries every price so digits align down a column.
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  const queryClient = getQueryClient();

  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexMono.variable}`}
      data-theme="light"
      suppressHydrationWarning
    >
      <head>
        <title>BreakoutScan</title>
        <meta
          name="description"
          content="India's real-time NSE/BSE breakout screener."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="theme-color" content="#f2f4f7" id="theme-color-meta" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            {children}
            <ThemedToaster />
            <AnalyticsProvider />
          </ThemeProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
