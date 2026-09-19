"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { auth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const { redirected } = await auth.signInWithGoogle();
      if (!redirected) {
        router.push("/");
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-page">
      <div className="w-full max-w-sm space-y-8 px-6">
        {/* Back to app */}
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 py-2 text-data text-text-secondary transition-colors hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </button>

        {/* Logo */}
        <div className="text-center">
          <img
            src="/logo-mark.svg"
            alt="BreakoutScan"
            className="mx-auto h-16 w-16 rounded-2xl"
          />
          <h1 className="mt-4 text-xl font-semibold text-text-primary">
            BreakoutScan
          </h1>
          <p className="mt-1 text-data text-text-secondary">
            India&apos;s real-time NSE/BSE breakout screener
          </p>
        </div>

        {/* Sign in button */}
        <button
          onClick={handleGoogleSignIn}
          disabled={loading}
          className="flex h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-card px-4 text-data font-semibold text-text-primary shadow-card transition-colors hover:border-accent/40 hover:bg-elevated disabled:opacity-50"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          {loading ? "Signing in..." : "Continue with Google"}
        </button>

        {error && (
          <p className="text-center text-label text-bearish">{error}</p>
        )}

        <p className="text-center text-label text-text-muted">
          Sign in to access your personal watchlist and alerts.
          By signing in, you agree to use this tool for informational purposes
          only. Not financial advice.
        </p>
      </div>
    </div>
  );
}
