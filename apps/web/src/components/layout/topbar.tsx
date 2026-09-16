"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Bell, Search, Sun, Moon, LogIn, LogOut, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { LiveDot } from "@/components/ui/live-dot";
import { CountdownBar } from "@/components/ui/countdown-bar";
import { useMarketStatus, useMarketIndices } from "@/hooks/use-market-breadth";
import { formatPrice, formatPercent } from "@/lib/format";
import { cn } from "@/lib/cn";
import { useTheme } from "@/components/providers/theme-provider";
import { useAuth } from "@/hooks/use-auth";
import { createClient } from "@/lib/supabase/client";
import { fetchStocks } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import type { Stock } from "@/lib/api-types";

function useIsMarketLive(): boolean {
  const [live, setLive] = useState(false);

  useEffect(() => {
    function check() {
      const now = new Date();
      // Convert to IST (UTC+5:30)
      const utc = now.getTime() + now.getTimezoneOffset() * 60000;
      const ist = new Date(utc + 5.5 * 3600000);
      const day = ist.getDay(); // 0=Sun,6=Sat
      const hours = ist.getHours();
      const mins = ist.getMinutes();
      const totalMins = hours * 60 + mins;
      // Weekday 9:15 - 15:30 IST
      const isWeekday = day >= 1 && day <= 5;
      const inHours = totalMins >= 9 * 60 + 15 && totalMins <= 15 * 60 + 30;
      setLive(isWeekday && inHours);
    }
    check();
    const interval = setInterval(check, 60_000);
    return () => clearInterval(interval);
  }, []);

  return live;
}

function IndexTicker({
  name,
  last,
  changePct,
}: {
  name: string;
  last: number;
  changePct: number;
}) {
  const prevRef = useRef(last);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (last > prevRef.current) setFlash("up");
    else if (last < prevRef.current) setFlash("down");
    prevRef.current = last;
    const t = setTimeout(() => setFlash(null), 600);
    return () => clearTimeout(t);
  }, [last]);

  return (
    <div className="flex shrink-0 items-center gap-2 px-1">
      <span className="text-[11px] font-medium text-text-muted">{name}</span>
      <span
        className={cn(
          "font-mono text-sm tabular-nums text-text-primary transition-colors",
          flash === "up" && "flash-bullish",
          flash === "down" && "flash-bearish"
        )}
      >
        {formatPrice(last)}
      </span>
      <span
        className={cn(
          "font-mono text-xs tabular-nums",
          changePct >= 0 ? "text-bullish" : "text-bearish"
        )}
      >
        {formatPercent(changePct)}
      </span>
    </div>
  );
}

export function Topbar() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const { data: status } = useMarketStatus();
  const { data: indices } = useMarketIndices();
  const isMarketLive = useIsMarketLive();
  const { theme, toggleTheme } = useTheme();
  const { user, loading: authLoading } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSignIn = () => router.push("/login");

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    setShowUserMenu(false);
    router.refresh();
  };

  // Global Ctrl+K / Cmd+K shortcut to focus search
  useEffect(() => {
    function handleGlobalKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleGlobalKey);
    return () => document.removeEventListener("keydown", handleGlobalKey);
  }, []);

  const searchStocks = useCallback((query: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 1) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    // Instant local results first
    const local = searchLocalStocks(query, 8);
    if (local.length > 0) {
      setSuggestions(local.map((s) => ({ symbol: s.symbol, name: s.name, sector: s.sector }) as Stock));
      setShowDropdown(true);
      setSelectedIdx(-1);
    }

    // Then try API for potentially better results
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetchStocks({ search: query, limit: 8 });
        if (res.stocks && res.stocks.length > 0) {
          setSuggestions(res.stocks);
          setShowDropdown(true);
          setSelectedIdx(-1);
        }
      } catch {
        // Local results already shown — no-op
      }
    }, 300);
  }, []);

  const navigateToChart = useCallback(
    (symbol: string) => {
      router.push(`/chart/${symbol.toUpperCase()}`);
      setSearch("");
      setSuggestions([]);
      setShowDropdown(false);
    },
    [router]
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIdx >= 0 && suggestions[selectedIdx]) {
      navigateToChart(suggestions[selectedIdx].symbol);
    } else if (search.trim()) {
      navigateToChart(search.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  };

  return (
    <header className="glass-topbar flex flex-col">
      {/* Mobile: compact row with search + status */}
      <div className="flex h-12 items-center justify-between gap-2 px-3 sm:h-14 sm:gap-4 sm:px-6">
        {/* Index tickers — hidden on mobile, shown on sm+ */}
        <div className="hidden sm:flex flex-1 items-center gap-5 overflow-x-auto scrollbar-none">
          {indices?.slice(0, 5).map((idx) => (
            <IndexTicker
              key={idx.symbol}
              name={idx.name ?? idx.symbol}
              last={idx.last ?? idx.value}
              changePct={idx.change_pct}
            />
          ))}
        </div>

        {/* Mobile: App logo — icon only, the search bar needs the room */}
        <img
          src="/logo-mark.svg"
          alt="BreakoutScan"
          className="sm:hidden h-7 w-7 shrink-0 rounded-md"
        />

        <div className="flex items-center gap-2 sm:gap-3">
          {/* Search with autocomplete */}
          <div className="relative" ref={dropdownRef}>
            <form onSubmit={handleSearch}>
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted z-10" />
              <input
                ref={searchInputRef}
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  searchStocks(e.target.value);
                }}
                onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
                onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                onKeyDown={handleKeyDown}
                placeholder="Search..."
                className="h-9 w-32 rounded-xl border border-border bg-card pl-8 pr-2 text-sm text-text-primary placeholder-text-muted outline-none transition-all focus:border-accent focus:w-40 sm:h-10 sm:w-48 sm:pl-9 sm:pr-14 sm:focus:w-64"
              />
              <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-border bg-page px-1.5 py-0.5 text-[10px] text-text-muted hidden sm:inline">
                ⌘K
              </kbd>
            </form>
            {showDropdown && suggestions.length > 0 && (
              <div className="fixed left-3 right-3 top-[56px] z-[100] max-h-[320px] overflow-y-auto rounded-xl border border-border shadow-2xl sm:absolute sm:left-auto sm:right-0 sm:top-full sm:mt-1 sm:w-80" style={{ backgroundColor: '#0d1117' }}>
                {suggestions.map((stock, i) => (
                  <button
                    key={stock.symbol}
                    type="button"
                    onMouseDown={() => navigateToChart(stock.symbol)}
                    className={cn(
                      "flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition press-scale",
                      i === selectedIdx ? "bg-white/10" : "hover:bg-white/5"
                    )}
                  >
                    <span className="font-mono font-semibold text-accent">
                      {stock.symbol}
                    </span>
                    <span className="truncate text-text-secondary">
                      {stock.name}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-full p-2 sm:p-2.5 text-text-secondary transition hover:bg-elevated hover:text-text-primary min-h-[36px] min-w-[36px] flex items-center justify-center"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>

          {/* Live market indicator — hidden on mobile */}
          {isMarketLive && (
            <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-bullish/20 bg-bullish/5 px-2.5 py-1">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-bullish opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-bullish" />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-bullish">
                LIVE
              </span>
            </div>
          )}

          {/* Notification bell — hidden on mobile */}
          <button
            className="hidden sm:block relative rounded-lg p-2 text-text-muted transition hover:bg-elevated cursor-default opacity-60"
            title="Notifications coming soon"
          >
            <Bell className="h-4 w-4" />
          </button>

          {/* Auth: Login CTA or User avatar */}
          {!authLoading && (
            user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu((v) => !v)}
                  className="flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1.5 sm:px-3 sm:py-2 text-accent transition hover:bg-accent/20 press-scale min-h-[36px]"
                  title={user.email ?? "Account"}
                >
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline text-xs font-semibold max-w-[80px] truncate">
                    {user.email?.split("@")[0] ?? "Account"}
                  </span>
                </button>
                {showUserMenu && (
                  <div className="absolute right-0 top-full mt-2 z-[100] w-52 overflow-hidden rounded-xl border border-border shadow-2xl" style={{ backgroundColor: '#0d1117' }}>
                    <div className="px-4 py-3 border-b border-border">
                      <p className="text-xs text-text-muted truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={() => { setShowUserMenu(false); router.push("/settings"); }}
                      className="flex w-full items-center gap-3 px-4 py-3 text-sm text-text-secondary hover:bg-white/10 transition"
                    >
                      <User className="h-4 w-4" /> Settings
                    </button>
                    <button
                      onClick={handleSignOut}
                      className="flex w-full items-center gap-3 px-4 py-3 text-sm text-red-400 hover:bg-white/10 transition"
                    >
                      <LogOut className="h-4 w-4" /> Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleSignIn}
                className="flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-3 py-1.5 sm:px-3.5 sm:py-2 text-accent transition hover:bg-accent/20 press-scale min-h-[36px]"
              >
                <LogIn className="h-4 w-4" />
                <span className="text-xs font-semibold">
                  Sign In
                </span>
              </button>
            )
          )}

          {/* Live/Closed status pill */}
          <div className="hidden sm:flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5">
            <LiveDot color={status?.is_open ? "green" : "red"} />
            <span
              className={cn(
                "text-[10px] font-semibold uppercase tracking-[0.15em]",
                status?.is_open ? "text-bullish" : "text-bearish"
              )}
            >
              {status?.is_open ? "Live" : "Closed"}
            </span>
          </div>
        </div>
      </div>

      {/* Market countdown bar */}
      <div className="px-3 pb-1.5 sm:px-6 sm:pb-2">
        <CountdownBar isOpen={status?.is_open ?? false} />
      </div>
    </header>
  );
}
