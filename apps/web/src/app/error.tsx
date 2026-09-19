"use client";

import { useEffect } from "react";
import Link from "next/link";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  // Keep the technical detail for developers; users get a way forward, not a stack message.
  useEffect(() => {
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-page px-6 text-center text-text-primary">
      <div className="text-label font-semibold uppercase text-bearish">Something went wrong</div>
      <h1 className="text-title font-semibold">This page hit a snag.</h1>
      <p className="max-w-md text-data text-text-secondary">
        Your data is safe. Try again, or head back to the dashboard.
      </p>
      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={reset}
          className="inline-flex h-9 items-center justify-center rounded-lg bg-accent-solid px-4 text-data font-semibold text-white transition-colors hover:bg-accent-solid-hover"
        >
          Try again
        </button>
        <Link
          href="/dashboard"
          className="inline-flex h-9 items-center justify-center rounded-lg border border-border bg-card px-4 text-data font-semibold text-text-primary transition-colors hover:border-accent/40"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
