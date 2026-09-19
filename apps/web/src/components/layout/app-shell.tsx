"use client";

import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { IndexTickerBar } from "./index-ticker-bar";
import { MobileNav } from "./mobile-nav";
import { ApiOfflineBanner } from "./api-offline-banner";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-page text-text-primary lg:flex">
      <Sidebar />
      <div className="flex min-h-screen flex-1 flex-col overflow-x-hidden min-w-0">
        <ApiOfflineBanner />
        <Topbar />
        <IndexTickerBar />
        <main className="flex-1 overflow-x-hidden px-3 py-4 pb-20 sm:px-5 sm:py-5 lg:pb-6">
          <div className="mx-auto w-full max-w-[1680px]">{children}</div>
          {/* Footer — visible on mobile (hidden on desktop where sidebar has it) */}
          <footer className="mt-8 border-t border-border/50 pt-4 pb-2 text-center lg:hidden">
            <p className="text-micro text-text-muted">Made with love by a fellow trader</p>
            <p className="text-label font-medium text-text-secondary mt-0.5">Trade With Adarsha</p>
            <a
              href="https://www.instagram.com/iamadarsha/"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 py-2 text-label text-text-secondary transition-colors hover:text-accent"
            >
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
              Follow @iamadarsha
            </a>
          </footer>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
