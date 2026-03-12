/**
 * Equifidy API client — typed wrappers around the FastAPI backend.
 */

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';
const WS  = process.env.NEXT_PUBLIC_WS_URL  || 'ws://localhost:8002';

// ── Fetcher ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface IndexData {
  name: string;
  ltp: number;
  change: number;
  change_pct: number;
  open?: number;
  high?: number;
  low?: number;
  advances?: number;
  declines?: number;
}

export interface LivePrice {
  symbol: string;
  ltp: number;
  change_pct?: number;
  volume?: number;
  open?: number;
  high?: number;
  low?: number;
}

export interface MarketStatus {
  is_open: boolean;
  session: string;
  message: string;
}

export interface PrebuiltScan {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  timeframe: string;
  badge_color: string;
}

export interface ScanResult {
  symbol: string;
  company_name?: string;
  ltp: number;
  change_pct: number;
  volume: number;
  volume_ratio?: number;
  rsi_14?: number;
  ema_status?: string;
  matched_conditions: string[];
  scan_triggered_at: string;
  sector?: string;
}

export interface ScanRunResponse {
  scan_name: string;
  timeframe: string;
  results: ScanResult[];
  result_count: number;
  duration_ms: number;
  run_at: string;
}

export interface WatchlistItem {
  symbol: string;
  company_name?: string;
  ltp: number;
  change_pct: number;
  volume: number;
  rsi_14?: number;
  ema20_status?: string;
  sector?: string;
}

export interface OHLCVBar {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ── API Functions ─────────────────────────────────────────────────────────────

export const api = {
  getIndices:       () => apiFetch<IndexData[]>('/api/indices'),
  getMarketStatus:  () => apiFetch<MarketStatus>('/api/market/status'),
  getAllPrices:      () => apiFetch<Record<string, LivePrice>>('/api/prices'),
  getPrice:         (symbol: string) => apiFetch<LivePrice>(`/api/prices/${symbol}`),

  getPrebuiltScans: () => apiFetch<PrebuiltScan[]>('/api/screener/prebuilt'),
  runPrebuiltScan:  (id: string) => apiFetch<ScanRunResponse>(`/api/screener/prebuilt/${id}/run`, { method: 'POST' }),
  getLatestResults: () => apiFetch<{ results: any[]; total: number }>('/api/screener/results/latest'),

  searchStocks:     (q: string) => apiFetch<any[]>(`/api/stocks/search?q=${encodeURIComponent(q)}`),
  getStock:         (symbol: string) => apiFetch<any>(`/api/stocks/${symbol}`),
  getOHLCV:         (symbol: string, tf = '15min', bars = 200) =>
    apiFetch<{ symbol: string; timeframe: string; bars: OHLCVBar[] }>(`/api/stocks/${symbol}/ohlcv?tf=${tf}&bars=${bars}`),

  getWatchlist:     () => apiFetch<WatchlistItem[]>('/api/watchlist'),
  addToWatchlist:   (symbol: string) => apiFetch<any>(`/api/watchlist/${symbol}`, { method: 'POST' }),
  removeWatchlist:  (symbol: string) => apiFetch<any>(`/api/watchlist/${symbol}`, { method: 'DELETE' }),

  getAlerts:        () => apiFetch<any[]>('/api/alerts'),
  getAlertHistory:  () => apiFetch<any[]>('/api/alerts/history'),
  createAlert:      (data: any) => apiFetch<any>('/api/alerts', { method: 'POST', body: JSON.stringify(data) }),

  // AI Suggestions
  getAISuggestions:     () => apiFetch<any>('/api/ai-suggestions'),
  refreshAISuggestions: () => apiFetch<any>('/api/ai-suggestions/refresh', { method: 'POST' }),
};

// ── WebSocket helpers ─────────────────────────────────────────────────────────

export function connectPriceWS(onMessage: (data: any) => void) {
  const ws = new WebSocket(`${WS}/ws/prices`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onerror = (e) => console.warn('Price WS error', e);
  return ws;
}

export function connectScanWS(onMessage: (data: any) => void) {
  const ws = new WebSocket(`${WS}/ws/scans`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  return ws;
}

export function connectSymbolWS(symbol: string, onMessage: (data: any) => void) {
  const ws = new WebSocket(`${WS}/ws/prices/${symbol}`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  return ws;
}

export default api;
