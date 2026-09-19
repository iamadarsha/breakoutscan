"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  BellRing,
  ChartCandlestick,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  SearchCheck,
  Sparkles,
  Target,
  Eye,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/cn";

const mainNav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/screener", label: "Screener", icon: SearchCheck },
  { href: "/ai-picks", label: "AI Picks", icon: Sparkles },
  { href: "/chart/RELIANCE", label: "Charts", icon: ChartCandlestick },
  { href: "/watchlist", label: "Watchlist", icon: Eye },
] as const;

const analysisNav = [
  { href: "/fundamentals", label: "Fundamentals", icon: Target },
  { href: "/alerts", label: "Alerts", icon: BellRing },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  const renderNavItem = ({
    href,
    label,
    icon: Icon,
  }: {
    href: string;
    label: string;
    icon: typeof LayoutDashboard;
  }) => {
    const isActive = pathname === href || pathname.startsWith(href + "/");

    return (
      <Link
        key={href}
        href={href}
        title={collapsed ? label : undefined}
        className={cn(
          "relative flex items-center rounded-lg py-2 text-data font-medium transition-colors",
          collapsed ? "justify-center px-2" : "gap-2.5 px-3",
          isActive
            ? "bg-accent/10 text-accent"
            : "text-text-secondary hover:bg-elevated hover:text-text-primary"
        )}
      >
        {isActive && (
          <span className="absolute inset-y-1.5 -left-2 w-[3px] rounded-r-full bg-accent" />
        )}
        <Icon className="h-4 w-4 shrink-0" />
        {!collapsed && <span>{label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        "glass-sidebar hidden flex-col py-4 transition-[width] duration-200 lg:sticky lg:top-0 lg:flex lg:h-screen lg:shrink-0 lg:overflow-y-auto",
        collapsed ? "w-[60px] px-2" : "w-[208px] px-3"
      )}
    >
      {/* Logo */}
      <Link
        href="/"
        className={cn(
          "mb-5 flex items-center",
          collapsed ? "justify-center" : "gap-2.5 px-1"
        )}
      >
        <img
          src="/logo-mark.svg"
          alt="BreakoutScan"
          className="h-8 w-8 shrink-0 rounded-lg"
        />
        {!collapsed && (
          <div>
            <div className="text-panel font-semibold leading-tight text-text-primary">BreakoutScan</div>
            <div className="text-micro uppercase text-text-muted">Live terminal</div>
          </div>
        )}
      </Link>

      {/* Main nav */}
      {!collapsed && (
        <div className="mb-1 px-3 text-micro font-semibold uppercase text-text-muted">
          Main
        </div>
      )}
      <nav className="space-y-0.5">
        {mainNav.map((item) => renderNavItem(item))}
      </nav>

      {/* Analysis nav */}
      {!collapsed && (
        <div className="mb-1 mt-5 px-3 text-micro font-semibold uppercase text-text-muted">
          Analysis
        </div>
      )}
      {collapsed && <div className="my-3 border-t border-border" />}
      <nav className="space-y-0.5">
        {analysisNav.map((item) => renderNavItem(item))}
      </nav>

      <div className="flex-1" />

      {/* Bottom actions */}
      <div className="mt-4 space-y-1">
        <button
          onClick={() => router.push("/settings")}
          className={cn(
            "flex w-full items-center rounded-lg py-2 text-data font-medium transition-colors",
            collapsed ? "justify-center px-2" : "gap-2.5 px-3",
            pathname === "/settings"
              ? "bg-accent/10 text-accent"
              : "text-text-secondary hover:bg-elevated hover:text-text-primary"
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </button>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-lg py-1.5 text-text-muted transition-colors hover:bg-elevated hover:text-text-primary"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className="mt-3 border-t border-border pt-3 px-2 text-center">
          <p className="text-micro normal-case tracking-normal text-text-muted">
            Made with love by a fellow trader
          </p>
          <p className="text-micro normal-case tracking-normal font-medium text-text-secondary mt-0.5">
            Trade With Adarsha
          </p>
          <a
            href="https://www.instagram.com/iamadarsha/"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-micro normal-case tracking-normal text-text-muted hover:text-accent transition-colors"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
            Follow @iamadarsha
          </a>
        </div>
      )}
    </aside>
  );
}
