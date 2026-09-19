"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Zap,
  ScanSearch,
  SlidersHorizontal,
  LineChart,
  Bell,
  BarChart3,
  ArrowRight,
  Gauge,
  Sparkles,
} from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "Real-Time Scanning",
    description: "Live price feeds with sub-second latency. Breakout signals fire the moment conditions are met.",
    color: "text-bullish",
    bg: "bg-bullish/10",
    border: "border-bullish/20",
  },
  {
    icon: ScanSearch,
    title: "12 Prebuilt Scans",
    description: "Volume breakouts, EMA crossovers, RSI divergence, MACD signals, and more ready to run.",
    color: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/20",
  },
  {
    icon: SlidersHorizontal,
    title: "Custom Scanner",
    description: "Build your own scan conditions combining any indicator, timeframe, and universe filter.",
    color: "text-info",
    bg: "bg-info/10",
    border: "border-info/20",
  },
  {
    icon: LineChart,
    title: "Technical Charts",
    description: "Interactive candlestick charts with overlays for EMA, Bollinger Bands, RSI, MACD, and volume.",
    color: "text-warning",
    bg: "bg-warning/10",
    border: "border-warning/20",
  },
  {
    icon: Bell,
    title: "Smart Alerts",
    description: "Set price, volume, or indicator alerts. Get notified the instant your conditions trigger.",
    color: "text-bearish",
    bg: "bg-bearish/10",
    border: "border-bearish/20",
  },
  {
    icon: BarChart3,
    title: "Fundamentals",
    description: "Screen stocks by PE, PB, ROE, market cap, dividend yield, and debt-to-equity ratios.",
    color: "text-bullish",
    bg: "bg-bullish/10",
    border: "border-bullish/20",
  },
];

const stats = [
  { label: "Stocks", value: "500", icon: BarChart3 },
  { label: "Scans", value: "13", icon: ScanSearch },
  { label: "Updates", value: "Live", icon: Gauge },
  { label: "Free", value: "100%", icon: Sparkles },
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease: "easeOut" as const },
  }),
};

export default function HomePage() {
  return (
    <div className="min-h-screen bg-page">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center overflow-hidden px-6 pb-20 pt-32">
        {/* Glow orbs */}
        <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2">
          <div className="h-[600px] w-[800px] rounded-full bg-[radial-gradient(ellipse,rgba(124,92,252,0.15),transparent_70%)]" />
        </div>
        <div className="pointer-events-none absolute right-0 top-40">
          <div className="h-[400px] w-[400px] rounded-full bg-[radial-gradient(ellipse,rgba(0,212,255,0.08),transparent_70%)]" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 flex flex-col items-center text-center"
        >
          <img
            src="/logo-mark.svg"
            alt="BreakoutScan"
            className="mb-6 h-14 w-14 rounded-2xl"
          />
          <h1 className="mb-4 text-5xl font-bold tracking-tight text-text-primary sm:text-6xl lg:text-7xl">
            <span className="gradient-text">BreakoutScan</span>
          </h1>
          <p className="mb-8 max-w-xl text-lg text-text-secondary sm:text-xl">
            India&#39;s Real-Time Stock Breakout Scanner.{" "}
            <br className="hidden sm:block" />
            Spot momentum before the crowd.
          </p>
          <Link
            href="/dashboard"
            className="group inline-flex h-11 items-center gap-2 rounded-lg bg-accent-solid px-6 text-panel font-semibold text-white shadow-accent transition-colors hover:bg-accent-solid-hover"
          >
            Open Dashboard
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>
      </section>

      {/* Stats row */}
      <section className="relative z-10 mx-auto -mt-2 mb-20 max-w-3xl px-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              className="glass-card flex flex-col items-center px-4 py-5"
            >
              <stat.icon className="mb-2 h-5 w-5 text-accent" />
              <span className="text-2xl font-bold text-text-primary">{stat.value}</span>
              <span className="mt-1 text-label text-text-secondary">{stat.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Feature cards */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-32">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-12 text-center text-2xl font-semibold text-text-primary sm:text-3xl"
        >
          Everything you need to find breakouts
        </motion.h2>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feat, i) => (
            <motion.div
              key={feat.title}
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              className={`glass-card group p-6 ${feat.border} ${feat.bg} transition hover:border-opacity-60 hover:shadow-lg`}
            >
              <div className={`mb-4 inline-flex rounded-lg bg-elevated p-2.5 ${feat.color}`}>
                <feat.icon className="h-5 w-5" />
              </div>
              <h3 className="mb-2 text-base font-semibold text-text-primary">{feat.title}</h3>
              <p className="text-data leading-relaxed text-text-secondary">{feat.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-8 text-center text-label text-text-muted">
        BreakoutScan &mdash; Built for Indian markets. Not financial advice.
      </footer>
    </div>
  );
}
