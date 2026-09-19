"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Search, Sun, Moon, LogIn, LogOut, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { LiveDot } from "@/components/ui/live-dot";
import { useMarketStatus } from "@/hooks/use-market-breadth";
import { cn } from "@/lib/cn";
import { useTheme } from "@/components/providers/theme-provider";
import { useAuth } from "@/hooks/use-auth";
import { auth } from "@/lib/auth";
import { fetchStocks } from "@/lib/api";
import { searchLocalStocks } from "@/lib/nse-stocks";
import type { Stock } from "@/lib/api-types";

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
    await auth.signOut();
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

    // Local names are cleaner, so only ask the API when the local list has no match
    if (local.length > 0) return;
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

  const isOpen = Boolean(status?.is_open);
  const initial = (user?.email?.[0] ?? "?").toUpperCase();

  return (
    <header className="glass-topbar sticky top-0 z-30">
      <div className="flex h-12 items-center gap-3 px-3 sm:px-5">
        {/* Mobile: logo only — the search needs the room */}
        <img
          src="/logo-mark.svg"
          alt="BreakoutScan"
          className="h-7 w-7 shrink-0 rounded-md lg:hidden"
        />

        {/* Search is the primary control of a terminal: it gets the left edge and the room. */}
        <div className="relative z-20 min-w-0 flex-1 sm:max-w-md" ref={dropdownRef}>
          <form onSubmit={handleSearch} role="search">
            <Search className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-text-muted" />
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
              placeholder="Search stocks…"
              aria-label="Search stocks"
              className="h-9 w-full rounded-lg border border-border bg-page pl-9 pr-12 text-data text-text-primary placeholder-text-muted outline-none transition-colors focus:border-accent focus:bg-card focus:shadow-glow"
            />
            <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-border bg-card px-1.5 py-0.5 font-mono text-micro text-text-muted sm:inline">
              ⌘K
            </kbd>
          </form>
          {showDropdown && suggestions.length > 0 && (
            <div className="fixed left-3 right-3 top-[52px] z-[100] max-h-[320px] overflow-y-auto rounded-lg border border-border bg-card shadow-pop sm:absolute sm:left-0 sm:right-auto sm:top-full sm:mt-1 sm:w-full">
              {suggestions.map((stock, i) => (
                <button
                  key={stock.symbol}
                  type="button"
                  onMouseDown={() => navigateToChart(stock.symbol)}
                  className={cn(
                    "flex w-full items-baseline gap-3 px-3 py-2 text-left text-data transition-colors",
                    i === selectedIdx ? "bg-accent/10" : "hover:bg-accent/5"
                  )}
                >
                  <span className="font-mono font-semibold text-text-primary">{stock.symbol}</span>
                  <span className="truncate text-text-secondary">{stock.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Session status: one indicator, with the hours it refers to */}
          <div
            className="hidden items-center gap-2 rounded-md border border-border px-2.5 py-1 sm:flex"
            title="NSE session 09:15–15:30 IST, Mon–Fri"
          >
            <LiveDot color={isOpen ? "green" : "red"} />
            <span
              className={cn(
                "text-label font-semibold uppercase",
                isOpen ? "text-bullish" : "text-text-secondary"
              )}
            >
              {isOpen ? "Market open" : "Market closed"}
            </span>
          </div>

          <button
            onClick={toggleTheme}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-elevated hover:text-text-primary"
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {!authLoading &&
            (user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu((v) => !v)}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-solid text-label font-semibold text-white transition-colors hover:bg-accent-solid-hover"
                  title={user.email ?? "Account"}
                  aria-label="Account menu"
                  aria-expanded={showUserMenu}
                >
                  {initial}
                </button>
                {showUserMenu && (
                  <div className="absolute right-0 top-full z-[100] mt-2 w-56 overflow-hidden rounded-lg border border-border bg-card shadow-pop">
                    <div className="border-b border-border px-3 py-2.5">
                      <p className="truncate text-label text-text-muted">Signed in as</p>
                      <p className="truncate text-data font-medium text-text-primary">{user.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        router.push("/settings");
                      }}
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-data text-text-secondary transition-colors hover:bg-accent/5 hover:text-text-primary"
                    >
                      <User className="h-4 w-4" /> Settings
                    </button>
                    <button
                      onClick={handleSignOut}
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-data text-bearish transition-colors hover:bg-bearish/5"
                    >
                      <LogOut className="h-4 w-4" /> Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleSignIn}
                className="flex h-8 items-center gap-1.5 rounded-lg bg-accent-solid px-3 text-label font-semibold text-white transition-colors hover:bg-accent-solid-hover"
              >
                <LogIn className="h-3.5 w-3.5" />
                Sign in
              </button>
            ))}
        </div>
      </div>
    </header>
  );
}
