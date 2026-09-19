import { API_BASE_URL } from "./constants";
import type {
  ActiveBreakout,
  AiSuggestionsResponse,
  Alert,
  AlertCreateRequest,
  CustomScanRequest,
  FundamentalData,
  FundamentalFilters,
  IndexData,
  Indicators,
  LivePrice,
  MarketBreadth,
  MarketStatus,
  PrebuiltScan,
  PriceHistory,
  ScanResult,
  SectorData,
  Stock,
  StockAnalysis,
  StockListResponse,
  WatchlistItem,
} from "./api-types";

/* ------------------------------------------------------------------ */
/*  Generic fetch helpers                                              */
/* ------------------------------------------------------------------ */

/** Retry a fetch-like function with exponential back-off.
 *  Only retries on network errors or 5xx responses (not 4xx client errors). */
async function withRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
): Promise<T> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err: unknown) {
      lastErr = err;
      // Don't retry client errors (400–499)
      if (err instanceof Error && /API 4\d\d/.test(err.message)) throw err;
      if (attempt < maxAttempts - 1) {
        await new Promise((r) => setTimeout(r, 500 * 2 ** attempt));
      }
    }
  }
  throw lastErr;
}

/** Public API call — no auth required */
async function publicFetch<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  return withRetry(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), init?.timeoutMs ?? 15_000);
    return fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
      signal: controller.signal,
    })
      .then(async (res) => {
        clearTimeout(timeout);
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`API ${res.status}: ${text || res.statusText}`);
        }
        return res.json() as T;
      })
      .catch((err) => {
        clearTimeout(timeout);
        throw err;
      });
  });
}

/** Get auth headers from Supabase session (lazy import to avoid SSR issues) */
async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    if (typeof window === "undefined") return {};
    const { createClient } = await import("./supabase/client");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      return { Authorization: `Bearer ${data.session.access_token}` };
    }
  } catch {
    // No auth available — continue without token
  }
  return {};
}

/** Authenticated API call — includes Bearer token */
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  const authHeaders = await getAuthHeaders();
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...(init?.headers ?? {}),
      },
      ...init,
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API ${res.status}: ${text || res.statusText}`);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

/* ------------------------------------------------------------------ */
/*  Stocks                                                             */
/* ------------------------------------------------------------------ */

interface ApiStock {
  symbol: string;
  company_name?: string | null;
  sector?: string | null;
  market_cap?: string | number | null;
  is_nifty50?: boolean;
  is_nifty500?: boolean;
}

function toStock(r: ApiStock): Stock {
  return {
    symbol: r.symbol,
    name: r.company_name || r.symbol,
    sector: r.sector ?? "",
    industry: "",
    market_cap: r.market_cap != null ? Number(r.market_cap) : 0,
    is_nifty50: Boolean(r.is_nifty50),
    is_nifty500: Boolean(r.is_nifty500),
  };
}

export async function fetchStocks(params?: {
  search?: string;
  page?: number;
  limit?: number;
  nifty50?: boolean;
  nifty500?: boolean;
  sector?: string;
}): Promise<StockListResponse> {
  const sp = new URLSearchParams();
  if (params?.search) sp.set("search", params.search);
  if (params?.page) sp.set("page", String(params.page));
  // API paginates with page_size; the UI has always called it limit.
  if (params?.limit) sp.set("page_size", String(params.limit));
  if (params?.nifty50) sp.set("nifty50", "true");
  if (params?.nifty500) sp.set("nifty500", "true");
  if (params?.sector) sp.set("sector", params.sector);
  const qs = sp.toString();
  const resp = await publicFetch<{
    items?: ApiStock[];
    total?: number;
    page?: number;
    page_size?: number;
  }>(`/api/stocks${qs ? `?${qs}` : ""}`);
  return {
    stocks: (resp.items ?? []).map(toStock),
    total: resp.total ?? 0,
    page: resp.page ?? 1,
    limit: resp.page_size ?? params?.limit ?? 0,
  };
}

export async function fetchStock(symbol: string): Promise<Stock> {
  return toStock(await publicFetch<ApiStock>(`/api/stocks/${symbol}`));
}

/* ------------------------------------------------------------------ */
/*  Screener                                                           */
/* ------------------------------------------------------------------ */

export function fetchPrebuiltScans(): Promise<PrebuiltScan[]> {
  return publicFetch<PrebuiltScan[]>("/api/screener/prebuilt");
}

export function runPrebuiltScan(scanId: string): Promise<ScanResult> {
  return publicFetch<ScanResult>("/api/screener/run", {
    method: "POST",
    body: JSON.stringify({ scan_id: scanId }),
  });
}

export function runCustomScan(req: CustomScanRequest): Promise<ScanResult> {
  return publicFetch<ScanResult>("/api/screener/custom", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/* ------------------------------------------------------------------ */
/*  Prices                                                             */
/* ------------------------------------------------------------------ */

export function fetchLivePrice(symbol: string): Promise<LivePrice> {
  return publicFetch<LivePrice>(`/api/prices/live/${symbol}`);
}

export function fetchLivePrices(symbols: string[]): Promise<LivePrice[]> {
  return publicFetch<LivePrice[]>(
    `/api/prices/live?symbols=${symbols.join(",")}`
  );
}

export function fetchPriceHistory(
  symbol: string,
  timeframe: string
): Promise<PriceHistory> {
  return publicFetch<PriceHistory>(
    `/api/prices/history/${symbol}?timeframe=${timeframe}`
  );
}

export function fetchIndicators(symbol: string): Promise<Indicators> {
  return publicFetch<Indicators>(`/api/prices/indicators/${symbol}`);
}

export function fetchStockAnalysis(symbol: string): Promise<StockAnalysis> {
  return publicFetch<StockAnalysis>(`/api/stocks/${symbol}/analysis`);
}

/* ------------------------------------------------------------------ */
/*  Market                                                             */
/* ------------------------------------------------------------------ */

export function fetchMarketStatus(): Promise<MarketStatus> {
  return publicFetch<MarketStatus>("/api/market/status");
}

export function fetchMarketBreadth(): Promise<MarketBreadth> {
  return publicFetch<MarketBreadth>("/api/market/breadth");
}

export function fetchMarketIndices(): Promise<IndexData[]> {
  return publicFetch<IndexData[]>("/api/market/indices");
}

export function fetchMarketSectors(): Promise<SectorData[]> {
  return publicFetch<SectorData[]>("/api/market/sectors");
}

/* ------------------------------------------------------------------ */
/*  Breakouts                                                          */
/* ------------------------------------------------------------------ */

export function fetchActiveBreakouts(): Promise<ActiveBreakout[]> {
  return publicFetch<ActiveBreakout[]>("/api/breakouts/active");
}

/* ------------------------------------------------------------------ */
/*  Watchlist                                                          */
/* ------------------------------------------------------------------ */

export function fetchWatchlist(): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/api/watchlist");
}

export function addToWatchlist(symbol: string): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol }),
  });
}

export function removeFromWatchlist(symbol: string): Promise<void> {
  return apiFetch<void>(`/api/watchlist/${symbol}`, {
    method: "DELETE",
  });
}

/* ------------------------------------------------------------------ */
/*  Alerts                                                             */
/* ------------------------------------------------------------------ */

export function fetchAlerts(): Promise<Alert[]> {
  return apiFetch<Alert[]>("/api/alerts");
}

export function createAlert(req: AlertCreateRequest): Promise<Alert> {
  return apiFetch<Alert>("/api/alerts", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/* ------------------------------------------------------------------ */
/*  Fundamentals                                                       */
/* ------------------------------------------------------------------ */

export async function fetchFundamentals(
  filters: FundamentalFilters
): Promise<FundamentalData[]> {
  const sp = new URLSearchParams();
  // Map client filter keys → API query param names
  if (filters.pe_min != null) sp.set("pe_min", String(filters.pe_min));
  if (filters.pe_max != null) sp.set("pe_max", String(filters.pe_max));
  if (filters.pb_min != null) sp.set("pb_min", String(filters.pb_min));
  if (filters.pb_max != null) sp.set("pb_max", String(filters.pb_max));
  // UI takes market cap in crores; the API/DB stores rupees (1 crore = 1e7).
  if (filters.market_cap_min != null) sp.set("market_cap_min", String(filters.market_cap_min * 1e7));
  if (filters.market_cap_max != null) sp.set("market_cap_max", String(filters.market_cap_max * 1e7));
  if (filters.roe_min != null) sp.set("roe_min", String(filters.roe_min));
  if (filters.dividend_yield_min != null) sp.set("div_yield_min", String(filters.dividend_yield_min));
  if (filters.debt_to_equity_max != null) sp.set("debt_equity_max", String(filters.debt_to_equity_max));
  const qs = sp.toString();

  // API returns { items: [...], total, page, ... } — extract and remap field names
  const resp = await publicFetch<{ items: Record<string, unknown>[] }>(
    `/api/fundamentals${qs ? `?${qs}` : ""}`
  );
  return (resp.items ?? []).map((r) => ({
    symbol: r.symbol as string,
    name: (r.company_name ?? r.symbol) as string,
    sector: (r.sector ?? "") as string,
    market_cap: r.market_cap != null ? Number(r.market_cap) : 0,
    pe_ratio: r.pe != null ? Number(r.pe) : null,
    pb_ratio: r.pb != null ? Number(r.pb) : null,
    roe: r.roe != null ? Number(r.roe) : null,
    dividend_yield: r.div_yield != null ? Number(r.div_yield) : null,
    debt_to_equity: r.debt_equity != null ? Number(r.debt_equity) : null,
    eps: null,
    book_value: null,
    face_value: null,
  }));
}

/* ------------------------------------------------------------------ */
/*  AI Suggestions                                                     */
/* ------------------------------------------------------------------ */

export function fetchAiSuggestions(): Promise<AiSuggestionsResponse> {
  return publicFetch<AiSuggestionsResponse>("/api/ai-suggestions");
}

export function refreshAiSuggestions(): Promise<AiSuggestionsResponse> {
  return publicFetch<AiSuggestionsResponse>("/api/ai-suggestions/refresh", {
    method: "POST",
  });
}

/* ------------------------------------------------------------------ */
/*  System Health                                                      */
/* ------------------------------------------------------------------ */

export interface ApiHealth {
  status: "ok" | "degraded";
  redis: "ok" | "unavailable";
  poller: "running" | "stopped";
  universe_size: number;
  uptime_seconds: number;
}

export async function fetchApiHealth(): Promise<ApiHealth> {
  // Use a short timeout and no retry — this is a probe, not a data call
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 5_000);
  try {
    // Routed through /api/backend-health, not a plain /health fetch — the
    // catch-all proxy always prepends /api/ (which the backend's real
    // /health route doesn't have), and /api/health itself is Next.js's own
    // unrelated self-check. See app/api/backend-health/route.ts.
    const res = await fetch("/api/backend-health", { signal: controller.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error("health check failed");
    return res.json() as Promise<ApiHealth>;
  } catch {
    clearTimeout(t);
    // API completely unreachable — return a synthetic degraded status
    return { status: "degraded", redis: "unavailable", poller: "stopped", universe_size: 0, uptime_seconds: 0 };
  }
}

/* ------------------------------------------------------------------ */
/*  Company Info                                                       */
/* ------------------------------------------------------------------ */

export function fetchCompanyInfo(
  symbol: string
): Promise<import("./api-types").CompanyInfo> {
  return publicFetch<import("./api-types").CompanyInfo>(
    `/api/company/${symbol}`
  );
}
