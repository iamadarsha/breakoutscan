"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Sparkles,
  BarChart3,
  Eye,
  Ellipsis,
  Target,
  BellRing,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/cn";

// Five destinations fit a thumb; everything else lives behind "More" so no page is unreachable on a phone.
const NAV_ITEMS = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard, match: "/dashboard" },
  { href: "/screener", label: "Screener", icon: Search, match: "/screener" },
  { href: "/ai-picks", label: "AI Picks", icon: Sparkles, match: "/ai-picks" },
  { href: "/chart/RELIANCE", label: "Charts", icon: BarChart3, match: "/chart" },
  { href: "/watchlist", label: "Watchlist", icon: Eye, match: "/watchlist" },
];

const MORE_ITEMS = [
  { href: "/fundamentals", label: "Fundamentals", icon: Target },
  { href: "/alerts", label: "Alerts", icon: BellRing },
  { href: "/settings", label: "Settings", icon: Settings },
];

const isActive = (pathname: string, match: string) =>
  pathname === match || pathname.startsWith(match + "/") || pathname.startsWith(match + "s");

export function MobileNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreActive = MORE_ITEMS.some((m) => pathname === m.href || pathname.startsWith(m.href + "/"));

  // Close the sheet whenever the route changes or Escape is pressed.
  useEffect(() => {
    setMoreOpen(false);
  }, [pathname]);
  useEffect(() => {
    if (!moreOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMoreOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [moreOpen]);

  const tabClass = (active: boolean) =>
    cn(
      "flex min-h-[48px] min-w-[56px] flex-col items-center justify-center gap-0.5 px-2 text-micro font-medium transition-colors",
      active ? "text-accent" : "text-text-muted hover:text-text-secondary"
    );

  return (
    <>
      {moreOpen && (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setMoreOpen(false)}
        />
      )}

      {moreOpen && (
        <div
          id="more-menu"
          role="menu"
          className="fixed bottom-[68px] right-3 z-50 w-56 overflow-hidden rounded-xl border border-border bg-card shadow-pop lg:hidden"
        >
          {MORE_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              role="menuitem"
              className={cn(
                "flex items-center gap-3 border-b border-border-subtle px-4 py-3 text-data font-medium transition-colors last:border-0",
                pathname === href ? "bg-accent/10 text-accent" : "text-text-primary hover:bg-accent/5"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>
      )}

      <nav
        aria-label="Primary"
        className="safe-area-bottom fixed inset-x-0 bottom-0 z-50 border-t border-border bg-card lg:hidden"
      >
        <div className="flex items-center justify-around py-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon, match }) => {
            const active = isActive(pathname, match);
            return (
              <Link key={href} href={href} className={tabClass(active)} aria-current={active ? "page" : undefined}>
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </Link>
            );
          })}
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            aria-expanded={moreOpen}
            aria-controls="more-menu"
            className={tabClass(moreOpen || moreActive)}
          >
            <Ellipsis className="h-5 w-5" />
            <span>More</span>
          </button>
        </div>
      </nav>
    </>
  );
}
