import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Equifidy — India\'s Most Powerful Stock Screener',
  description: 'Real-time NSE & BSE stock screener with 12 pre-built scans, live charts, alerts and watchlists.',
  keywords: 'stock screener india, NSE screener, BSE screener, technical analysis, breakout stocks',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
