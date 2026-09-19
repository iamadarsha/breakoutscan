import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-page px-6 text-center text-text-primary">
      <div className="text-label font-semibold uppercase text-text-muted">404</div>
      <h1 className="text-title font-semibold">Page not found</h1>
      <p className="max-w-md text-data text-text-secondary">
        That page doesn&apos;t exist or has moved.
      </p>
      <Link
        href="/dashboard"
        className="mt-2 inline-flex h-9 items-center justify-center rounded-lg bg-accent-solid px-4 text-data font-semibold text-white transition-colors hover:bg-accent-solid-hover"
      >
        Go to dashboard
      </Link>
    </div>
  );
}
