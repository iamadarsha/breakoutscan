/* ------------------------------------------------------------------ */
/*  API response types for BreakoutScan backend                       */
/* ------------------------------------------------------------------ */

export interface Stock {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  is_nifty50: boolean;
  is_nifty500: boolean;
}

export interface StockListResponse {
  stocks: Stock[];
  total: number;
  page: number;
  limit: number;
}

export interface LivePrice {
  symbol: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  prev_close: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: string;
}

export interface LivePriceMap {
  [symbol: string]: LivePrice;
}

export interface OHLCV {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceHistory {
  symbol: string;
  timeframe: string;
  candles: OHLCV[];
}

export interface Indicators {
  symbol: string;
  ema_9: number | null;
  ema_21: number | null;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  atr_14: number | null;
  adx_14: number | null;
  bollinger_upper: number | null;
  bollinger_mid: number | null;
  bollinger_lower: number | null;
}

export interface PrebuiltScan {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
}

export interface ScanResultItem {
  symbol: string;
  company_name: string;
  sector?: string;
  ltp?: number;
  change_pct?: number;
  volume?: number;
  signal_strength?: number;
  score?: number;
  rsi_14?: number;
  ema_status?: string;
  matched_conditions?: string[];
}

export interface ScanResult {
  scan_id: string;
  scan_name: string;
  description?: string;
  total_matches: number;
  items: ScanResultItem[];
  run_at: string;
}

export interface ActiveBreakout {
  symbol: string;
  company_name?: string | null;
  trigger_type: string;
  direction: string;
  status: string;
  reference_level: number;
  last_price?: number | null;
  triggered_at?: string | null;
  bars_confirmed: number;
  score?: number | null;
  // False when this is the last CONFIRMED breakout from the durable table
  // (market closed / no fresh live signal yet), not a currently-live signal.
  is_live: boolean;
}

export interface CustomScanCondition {
  indicator: string;
  operator: string;
  value: number | string;
}

export interface CustomScanRequest {
  conditions: CustomScanCondition[];
  universe: string;
  timeframe: string;
}

export interface MarketStatus {
  is_open: boolean;
  session?: string;
  status?: string;
  next_open?: string;
  next_close?: string;
}

export interface MarketBreadth {
  advances: number;
  declines: number;
  unchanged: number;
  total: number;
  advance_decline_ratio: number;
}

export interface IndexData {
  symbol: string;
  name: string;
  value: number;
  last?: number;
  change: number;
  change_pct: number;
  open?: number;
  high?: number;
  low?: number;
  prev_close?: number;
}

export interface SectorData {
  sector: string;
  change_pct: number;
  advances: number;
  declines: number;
  top_gainer: string;
  top_loser: string;
}

export interface WatchlistItem {
  symbol: string;
  name: string;
  added_at: string;
}

export interface Alert {
  id: string;
  user_id: string;
  symbol: string;
  condition_type: string;
  condition_value: number;
  operator: string;
  is_active: boolean;
  triggered_at?: string;
  created_at: string;
}

export interface AlertCreateRequest {
  symbol: string;
  condition_type: string;
  condition_value: number;
  operator: string;
}

export interface FundamentalData {
  symbol: string;
  name: string;
  sector: string;
  market_cap: number;
  pe_ratio: number | null;
  pb_ratio: number | null;
  dividend_yield: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  eps: number | null;
  book_value: number | null;
  face_value: number | null;
}

export interface FundamentalFilters {
  pe_min?: number;
  pe_max?: number;
  pb_min?: number;
  pb_max?: number;
  market_cap_min?: number;
  market_cap_max?: number;
  roe_min?: number;
  dividend_yield_min?: number;
  debt_to_equity_max?: number;
}

/* WebSocket message types */
export interface WsPriceMessage {
  type: "price";
  data: LivePrice;
}

export interface WsSubscribeMessage {
  subscribe: string[];
}

export interface WsUnsubscribeMessage {
  unsubscribe: string[];
}

/* AI Suggestions */
export interface NewsSource {
  title: string;
  url: string;
  source: string;
  published_at?: string;
}

export interface AiSuggestion {
  symbol: string;
  name?: string;
  sector?: string;
  rationale: string;
  confidence?: number;
  timeframe?: string;
  target_horizon?: string;
  /** Why *now* — the single headline or technical signal that triggered this pick. */
  catalyst?: string;
  action?: "BUY" | "SELL";
  /** Expected % move and suggested stop-loss %, as sent by the backend
   * (not preformatted strings — format at render time). */
  target_pct?: number;
  stop_loss_pct?: number;
  tags?: string[];
  news_sources?: NewsSource[];
}

export interface AiSuggestionsResponse {
  suggestions?: AiSuggestion[];
  intraday?: AiSuggestion[];
  weekly?: AiSuggestion[];
  monthly?: AiSuggestion[];
  swing?: AiSuggestion[];
  positional?: AiSuggestion[];
  generated_at?: string;
  /** Which layer actually produced these picks: "gemini" | "groq" | "technical-analysis" | "pending". */
  source?: string;
  headline_count?: number;
}

/** Per-symbol BUY/SELL/HOLD call shown below the chart — unlike AiSuggestion
 * (a curated pick list), this always resolves to one of the three actions
 * for whichever stock the user is actively viewing. */
export interface StockAnalysis {
  symbol: string;
  name?: string;
  sector?: string;
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  rationale: string;
  catalyst?: string;
  target_pct?: number;
  stop_loss_pct?: number;
  tags?: string[];
  news_sources?: NewsSource[];
  /** Which layer produced this call: "groq" | "technical-analysis". */
  source?: string;
  generated_at?: string;
}

/* Company Info */
export interface CompanyInfo {
  symbol: string;
  name: string;
  description?: string;
  sector?: string;
  industry?: string;
  website?: string;
  logo_url?: string;
}
