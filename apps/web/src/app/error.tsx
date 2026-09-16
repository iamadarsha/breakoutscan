"use client";

type ErrorPageProps = {
  error: Error;
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-page px-6 text-center text-text-primary">
      <div className="text-xs uppercase tracking-[0.22em] text-bearish">
        Runtime error
      </div>
      <h1 className="text-3xl font-bold">Something failed to load.</h1>
      <p className="max-w-md text-sm text-text-secondary">{error.message}</p>
      <button
        onClick={reset}
        className="inline-flex h-10 items-center justify-center rounded-full bg-gradient-to-br from-[#7C5CFC] to-[#5B3FD4] px-4 text-sm font-semibold shadow-accent"
      >
        Retry
      </button>
    </div>
  );
}

