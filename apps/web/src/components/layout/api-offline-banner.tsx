"use client";

import { useApiHealth } from "@/hooks/use-api-health";

/**
 * Shows a slim banner at the top of the page when the backend is unreachable
 * or in a degraded state.  Auto-dismisses as soon as the health probe succeeds.
 */
export function ApiOfflineBanner() {
  const { data, isError, isPending } = useApiHealth();

  // Don't render until we have a definitive answer
  if (isPending) return null;

  const isOffline = isError || data?.status === "degraded";
  if (!isOffline) return null;

  const redisDown = data?.redis === "unavailable";
  const pollerDown = data?.poller === "stopped";

  let message = "Data service unavailable — live prices may be stale.";
  if (!data) message = "Cannot reach the data server. Retrying…";
  else if (redisDown && pollerDown) message = "Data service degraded — cache and live-data feed are offline. Retrying…";
  else if (redisDown) message = "Cache layer offline — some data may be stale. Retrying…";
  else if (pollerDown) message = "Live-price feed stopped — data may be stale. Retrying…";

  return (
    <div
      role="alert"
      className="flex items-center justify-center gap-2 border-b border-warning/30 bg-warning/10 px-4 py-1.5 text-label font-medium text-warning"
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-warning animate-pulse" />
      {message}
    </div>
  );
}
