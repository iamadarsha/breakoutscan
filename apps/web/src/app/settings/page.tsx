"use client";

import { AppShell } from "@/components/layout/app-shell";
import { PageTransition } from "@/components/layout/page-transition";
import { SectionHeading } from "@/components/ui/section-heading";
import { PanelHeader } from "@/components/ui/panel-header";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/components/providers/theme-provider";
import { useApiHealth } from "@/hooks/use-api-health";
import { Sun, Moon, LogOut, LogIn } from "lucide-react";
import { auth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

// What each provider does, so a data problem can be traced to its source.
const PROVIDERS = [
  { name: "Upstox + NSE", desc: "Live prices, indices, market breadth" },
  { name: "Yahoo Finance", desc: "Price history, indicators, fundamentals" },
  { name: "Gemini 3.5 Flash Lite", desc: "AI Picks (news-driven)" },
  { name: "Groq", desc: "Per-stock BUY / HOLD / SELL call" },
  { name: "Google News RSS", desc: "Market headlines" },
];

const ABOUT = [
  { label: "Universe", value: "NIFTY 500" },
  { label: "Prebuilt scans", value: "13" },
  { label: "Breakout triggers", value: "12" },
];

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const { data: health, isError, isPending } = useApiHealth();
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    auth
      .getUser()
      .then((user) => setUserEmail(user?.email ?? null))
      .catch(() => setUserEmail(null));
  }, []);

  const handleSignOut = async () => {
    await auth.signOut();
    setUserEmail(null);
    router.refresh();
  };

  const serviceOk = !isError && health?.status !== "degraded";

  return (
    <AppShell>
      <PageTransition>
        <div className="mx-auto max-w-3xl space-y-5">
          <SectionHeading title="Settings" subtitle="Appearance, data sources and your account" />

          <section className="glass-card overflow-hidden">
            <PanelHeader title="Appearance" />
            <div className="flex items-center justify-between gap-4 px-4 py-3">
              <div>
                <p className="text-data font-medium text-text-primary">Theme</p>
                <p className="text-label text-text-muted">
                  Currently {theme === "dark" ? "dark" : "light"}. Applies to this visit only.
                </p>
              </div>
              <button
                onClick={toggleTheme}
                className="flex h-9 items-center gap-2 rounded-lg border border-border bg-card px-3 text-data font-medium text-text-primary transition-colors hover:border-accent/40 hover:bg-accent/5"
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                Switch to {theme === "dark" ? "light" : "dark"}
              </button>
            </div>
          </section>

          <section className="glass-card overflow-hidden">
            <PanelHeader
              title="Data sources"
              meta="what powers each part of the app"
              action={
                isPending ? (
                  <Badge variant="neutral">Checking…</Badge>
                ) : (
                  <Badge variant={serviceOk ? "bullish" : "warning"}>
                    {serviceOk ? "All services operational" : "Degraded"}
                  </Badge>
                )
              }
            />
            <ul>
              {PROVIDERS.map((p) => (
                <li
                  key={p.name}
                  className="flex items-baseline justify-between gap-4 border-b border-border-subtle px-4 py-2.5 last:border-0"
                >
                  <span className="text-data font-medium text-text-primary">{p.name}</span>
                  <span className="text-right text-label text-text-secondary">{p.desc}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="glass-card overflow-hidden">
            <PanelHeader title="About" />
            <dl>
              {ABOUT.map((row) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between border-b border-border-subtle px-4 py-2.5 text-data last:border-0"
                >
                  <dt className="text-text-secondary">{row.label}</dt>
                  <dd className="font-mono font-medium tabular-nums text-text-primary">{row.value}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="glass-card overflow-hidden">
            <PanelHeader title="Account" />
            <div className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-data font-medium text-text-primary">
                  {userEmail ? userEmail : "Not signed in"}
                </p>
                <p className="text-label text-text-muted">
                  {userEmail
                    ? "Sign out to switch accounts"
                    : "Sign in for a personal watchlist and alerts"}
                </p>
              </div>
              {userEmail ? (
                <button
                  onClick={handleSignOut}
                  className="flex h-9 shrink-0 items-center gap-2 rounded-lg border border-bearish/30 px-3 text-data font-medium text-bearish transition-colors hover:bg-bearish/10"
                >
                  <LogOut className="h-4 w-4" /> Sign out
                </button>
              ) : (
                <button
                  onClick={() => router.push("/login")}
                  className="flex h-9 shrink-0 items-center gap-2 rounded-lg bg-accent-solid px-3 text-data font-semibold text-white transition-colors hover:bg-accent-solid-hover"
                >
                  <LogIn className="h-4 w-4" /> Sign in
                </button>
              )}
            </div>
          </section>
        </div>
      </PageTransition>
    </AppShell>
  );
}
