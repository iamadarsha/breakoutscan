/**
 * Format a number as Indian Rupees (e.g. 1,23,456.00)
 */
export function formatINR(value: number, decimals = 2): string {
  const formatted = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
  return formatted;
}

/**
 * Format price with 2 decimals (no currency symbol)
 */
export function formatPrice(value: number): string {
  return value.toFixed(2);
}

/**
 * Format percentage (e.g. +2.45% or -1.30%)
 */
export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format large numbers Indian style (Cr / L / K)
 */
export function formatLargeNumber(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (abs >= 1e7) {
    return `${sign}${(abs / 1e7).toFixed(2)}Cr`;
  }
  if (abs >= 1e5) {
    return `${sign}${(abs / 1e5).toFixed(2)}L`;
  }
  if (abs >= 1e3) {
    return `${sign}${(abs / 1e3).toFixed(1)}K`;
  }
  return `${sign}${abs.toFixed(0)}`;
}

/**
 * Format volume (compact)
 */
export function formatVolume(value: number): string {
  if (value >= 1e7) return `${(value / 1e7).toFixed(2)}Cr`;
  if (value >= 1e5) return `${(value / 1e5).toFixed(1)}L`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toString();
}

/**
 * Format market cap
 */
export function formatMarketCap(value: number): string {
  // Indian units: 1 crore = 1e7, 1 lakh crore = 1e12 (all values are in rupees).
  if (value >= 1e12) return `₹${(value / 1e12).toFixed(2)}L Cr`;
  if (value >= 1e7) {
    const crores = value / 1e7;
    return `₹${crores.toLocaleString("en-IN", { maximumFractionDigits: crores >= 1000 ? 0 : 2 })} Cr`;
  }
  if (value >= 1e5) return `${(value / 1e5).toFixed(2)}L`;
  return formatINR(value);
}

/**
 * Format a timestamp to local time string
 */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format a timestamp to date string
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
