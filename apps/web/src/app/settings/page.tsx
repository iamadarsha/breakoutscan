"use client";

import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { useTheme } from "@/components/providers/theme-provider";
import { Sun, Moon, Database, Globe, Info, ExternalLink, LogOut } from "lucide-react";
import { cn } from "@/lib/cn";
import { motion } from "framer-motion";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

const DATA_SOURCES = [
  { name: "Yahoo Finance", desc: "OHLCV data & technical indicators", status: "active" },
  { name: "Indian Stock API", desc: "Live NSE market data & indices", status: "active" },
  { name: "Gemini 3.5 Flash Lite", desc: "AI-powered stock suggestions", status: "active" },
  { name: "Google News RSS", desc: "Market news aggregation", status: "active" },
];

const item = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUserEmail(user?.email ?? null);
    });
  }, []);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    setUserEmail(null);
    router.refresh();
  };

  return (
    <AppShell>
      <PageTransition>
        <div className="space-y-6">
          <SectionHeading
            title="Settings"
            subtitle="Application preferences and data source configuration"
          />

          {/* Theme */}
          <motion.div variants={item} className="glass-card rounded-panel p-5">
            <h3 className="mb-4 text-sm font-semibold text-text-primary">Appearance</h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">Theme</p>
                <p className="text-xs text-text-muted">Switch between dark and light mode</p>
              </div>
              <button
                onClick={toggleTheme}
                className={cn(
                  "flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium transition",
                  "hover:border-accent/30 hover:text-text-primary"
                )}
              >
                {theme === "dark" ? (
                  <>
                    <Sun className="h-4 w-4" /> Light Mode
                  </>
                ) : (
                  <>
                    <Moon className="h-4 w-4" /> Dark Mode
                  </>
                )}
              </button>
            </div>
          </motion.div>

          {/* Data Sources */}
          <motion.div variants={item} className="glass-card rounded-panel p-5">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Database className="h-4 w-4" /> Data Sources
            </h3>
            <div className="space-y-3">
              {DATA_SOURCES.map((src) => (
                <div
                  key={src.name}
                  className="flex items-center justify-between rounded-lg border border-border bg-page px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-text-primary">{src.name}</p>
                    <p className="text-xs text-text-muted">{src.desc}</p>
                  </div>
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-bullish">
                    <span className="h-1.5 w-1.5 rounded-full bg-bullish" />
                    Connected
                  </span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* App Info */}
          <motion.div variants={item} className="glass-card rounded-panel p-5">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-text-primary">
              <Info className="h-4 w-4" /> About
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">App Version</span>
                <span className="font-mono text-text-primary">0.1.0</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Universe</span>
                <span className="font-mono text-text-primary">NIFTY 500</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Indicators</span>
                <span className="font-mono text-text-primary">14 (RSI, EMA, SMA, MACD, BB...)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Prebuilt Scans</span>
                <span className="font-mono text-text-primary">13</span>
              </div>
            </div>
          </motion.div>

          {/* Account */}
          <motion.div variants={item} className="glass-card rounded-panel p-5">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-text-primary">
              <LogOut className="h-4 w-4" /> Account
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">
                  {userEmail ? `Signed in as ${userEmail}` : "Not signed in"}
                </p>
                <p className="text-xs text-text-muted">
                  {userEmail ? "Sign out to switch accounts or re-authenticate" : "Sign in to access watchlist, alerts, and more"}
                </p>
              </div>
              {userEmail ? (
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-2 rounded-full border border-red-500/30 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-500/10"
                >
                  <LogOut className="h-4 w-4" /> Sign Out
                </button>
              ) : (
                <button
                  onClick={() => router.push("/login")}
                  className="flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-2 text-sm font-medium text-accent transition hover:bg-accent/20"
                >
                  Sign In
                </button>
              )}
            </div>
          </motion.div>

          {/* Coming Soon */}
          <motion.div variants={item} className="rounded-panel border border-dashed border-border bg-card/40 p-6 text-center">
            <Globe className="mx-auto h-8 w-8 text-text-muted" />
            <p className="mt-3 text-sm font-medium text-text-secondary">
              More settings coming soon
            </p>
            <p className="mt-1 text-xs text-text-muted">
              Notification preferences, portfolio tracking, and custom watchlist alerts
            </p>
          </motion.div>
        </div>
      </PageTransition>
    </AppShell>
  );
}
