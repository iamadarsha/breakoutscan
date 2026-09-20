/**
 * First-party usage analytics (browser side).
 *
 * What it records: anonymous visitor/session ids, page views, time on page, clicks (element label only,
 * never typed text), a few product events, JS errors and web vitals.
 * What it never records: keystrokes, form values, query strings, IP addresses (server side), emails.
 * Respected: Do Not Track, Global Privacy Control, and the in-app opt-out (Settings, or `?bs_optout=1`).
 * Events are batched and sent to `/api/analytics/collect`; see docs/ANALYTICS.md.
 */
import { API_BASE_URL } from "./constants";

const VISITOR_KEY = "bs_vid";
const SESSION_KEY = "bs_sess";
const CONTEXT_KEY = "bs_ctx";
const OPT_OUT_KEY = "bs_optout";
const SESSION_IDLE_MS = 30 * 60 * 1000;
const FLUSH_DELAY_MS = 2_000;
const MAX_BATCH = 50;
const ENDPOINT = `${API_BASE_URL}/api/analytics/collect`;

type Props = Record<string, string | number | boolean | null>;
interface QueuedEvent {
  name: string;
  ts: number;
  path: string;
  props: Props;
}

let queue: QueuedEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let tokenProvider: (() => Promise<string | null>) | null = null;
let cachedToken: string | null = null;
let retried = false;

const isBrowser = () => typeof window !== "undefined";

function envEnabled(): boolean {
  if (process.env.NEXT_PUBLIC_ANALYTICS === "off") return false;
  return process.env.NODE_ENV === "production" || process.env.NEXT_PUBLIC_ANALYTICS === "on";
}

function safeStorage(kind: "local" | "session"): Storage | null {
  try {
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null; // blocked or private mode: analytics simply stays off
  }
}

export function isOptedOut(): boolean {
  if (!isBrowser()) return true;
  return safeStorage("local")?.getItem(OPT_OUT_KEY) === "1";
}

export function setOptOut(value: boolean): void {
  const store = safeStorage("local");
  if (!store) return;
  if (value) {
    store.setItem(OPT_OUT_KEY, "1");
    queue = [];
  } else {
    store.removeItem(OPT_OUT_KEY);
  }
}

/** Tracking is allowed only in production builds, when not opted out and without a privacy signal. */
export function isTrackingAllowed(): boolean {
  if (!isBrowser() || !envEnabled() || isOptedOut()) return false;
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
  if (navigator.doNotTrack === "1" || nav.globalPrivacyControl === true) return false;
  return safeStorage("local") !== null;
}

/** `?bs_optout=1` excludes this browser (e.g. the owner's own visits); `?bs_optout=0` re-includes it. */
export function applyOptOutParam(): void {
  if (!isBrowser()) return;
  const v = new URLSearchParams(window.location.search).get("bs_optout");
  if (v === "1" || v === "0") setOptOut(v === "1");
}

function uid(): string {
  const c = typeof crypto !== "undefined" ? crypto : undefined;
  if (c?.randomUUID) return c.randomUUID();
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}

function visitorId(): string {
  const store = safeStorage("local")!;
  let id = store.getItem(VISITOR_KEY);
  if (!id) {
    id = uid();
    store.setItem(VISITOR_KEY, id);
  }
  return id;
}

interface SessionState {
  id: string;
  last: number;
}

/** A session ends after 30 minutes of no activity (shared across tabs via localStorage). */
function touchSession(): { id: string; isNew: boolean } {
  const store = safeStorage("local")!;
  const now = Date.now();
  let state: SessionState | null = null;
  try {
    state = JSON.parse(store.getItem(SESSION_KEY) ?? "null");
  } catch {
    state = null;
  }
  let isNew = false;
  if (!state || now - state.last > SESSION_IDLE_MS) {
    state = { id: uid(), last: now };
    isNew = true;
    captureContext();
  }
  state.last = now;
  store.setItem(SESSION_KEY, JSON.stringify(state));
  return { id: state.id, isNew };
}

/** Referrer and UTM tags are read once when a session starts, then reused for its batches. */
function captureContext(): void {
  const params = new URLSearchParams(window.location.search);
  let referrer: string | null = null;
  try {
    if (document.referrer && new URL(document.referrer).origin !== window.location.origin) {
      const r = new URL(document.referrer);
      referrer = `${r.origin}${r.pathname}`.slice(0, 300); // never keep the referrer's query string
    }
  } catch {
    referrer = null;
  }
  const ctx = {
    referrer,
    utm_source: params.get("utm_source")?.slice(0, 100) ?? null,
    utm_medium: params.get("utm_medium")?.slice(0, 100) ?? null,
    utm_campaign: params.get("utm_campaign")?.slice(0, 100) ?? null,
  };
  safeStorage("session")?.setItem(CONTEXT_KEY, JSON.stringify(ctx));
}

function context(): Record<string, string | null> {
  try {
    return JSON.parse(safeStorage("session")?.getItem(CONTEXT_KEY) ?? "{}");
  } catch {
    return {};
  }
}

/** The provider tells us when a user is signed in so events can be attributed to their opaque id. */
export function setAuth(provider: (() => Promise<string | null>) | null): void {
  tokenProvider = provider;
  if (!provider) cachedToken = null;
}

export function track(name: string, props: Props = {}, pathOverride?: string): void {
  if (!isTrackingAllowed()) return;
  const path = pathOverride ?? window.location.pathname;
  if (path.startsWith("/admin")) return; // the owner's metrics page is never tracked
  touchSession();
  queue.push({ name, ts: Date.now(), path, props });
  if (queue.length >= MAX_BATCH) void flush();
  else schedule();
}

function schedule(): void {
  if (timer) return;
  timer = setTimeout(() => {
    timer = null;
    void flush();
  }, FLUSH_DELAY_MS);
}

async function authHeader(unloading: boolean): Promise<Record<string, string>> {
  if (!tokenProvider) return {};
  if (unloading) return cachedToken ? { Authorization: `Bearer ${cachedToken}` } : {};
  try {
    const token = await Promise.race([
      tokenProvider(),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), 1_500)),
    ]);
    cachedToken = token ?? cachedToken;
  } catch {
    /* anonymous batch */
  }
  return cachedToken ? { Authorization: `Bearer ${cachedToken}` } : {};
}

export async function flush(unloading = false): Promise<void> {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (!queue.length || !isTrackingAllowed()) {
    queue = [];
    return;
  }
  const events = queue.splice(0, MAX_BATCH);
  const { id: sessionId } = touchSession();
  const ctx = context();
  const body = JSON.stringify({
    visitor_id: visitorId(),
    session_id: sessionId,
    events: events.map((e) => ({ name: e.name, ts: e.ts, path: e.path, props: e.props })),
    referrer: ctx.referrer ?? null,
    utm_source: ctx.utm_source ?? null,
    utm_medium: ctx.utm_medium ?? null,
    utm_campaign: ctx.utm_campaign ?? null,
    viewport_w: Math.min(window.innerWidth, 20_000),
    app_version: (process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ?? "dev").slice(0, 7),
  });
  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await authHeader(unloading)) },
      body,
      keepalive: true,
    });
    if (!res.ok && res.status >= 500) throw new Error(String(res.status));
    retried = false;
  } catch {
    // Network blip: put the events back once so a brief outage doesn't lose visits.
    if (!retried && !unloading) {
      retried = true;
      queue = [...events, ...queue].slice(0, 200);
      schedule();
    }
  }
  if (queue.length) schedule();
}

/** Label for a clicked element: explicit data-track, then aria-label, title, then its visible text. */
export function elementLabel(el: Element): string {
  const explicit = el.getAttribute("data-track") ?? el.getAttribute("aria-label") ?? el.getAttribute("title");
  const text = (el as HTMLElement).innerText ?? el.textContent ?? "";
  // Big card buttons contain paragraphs; the first line is the name.
  const lead = el.querySelector("h1,h2,h3,h4,h5,h6")?.textContent?.trim() || el.firstElementChild?.textContent?.trim();
  const firstLine = (el.childElementCount > 1 && lead ? lead : text.split("\n").map((l) => l.trim()).find(Boolean)) ?? "";
  return (explicit ?? firstLine).replace(/\s+/g, " ").trim().slice(0, 60);
}
