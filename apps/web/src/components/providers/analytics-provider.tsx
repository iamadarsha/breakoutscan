"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useReportWebVitals } from "next/web-vitals";
import { useAuth } from "@/hooks/use-auth";
import { auth } from "@/lib/auth";
import {
  applyOptOutParam,
  elementLabel,
  flush,
  isTrackingAllowed,
  setAuth,
  track,
} from "@/lib/analytics";

const CLICKABLE = "button, a[href], [role=tab], [role=menuitem], [data-track]";
const SIGN_IN_PENDING = "bs_signin_pending";

/** Mounted once in the root layout. Renders nothing; wires page views, clicks, errors and vitals. */
export function AnalyticsProvider() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const currentPath = useRef<string | null>(null);
  const visibleSince = useRef<number | null>(null);
  const visibleMs = useRef(0);
  const errorsOnPage = useRef(0);

  useEffect(() => {
    applyOptOutParam();
  }, []);

  // Identify: attach the signed-in user's token to batches, and record real sign-ins.
  useEffect(() => {
    if (loading) return;
    if (user) {
      setAuth(() => auth.getAccessToken());
      try {
        if (window.sessionStorage.getItem(SIGN_IN_PENDING)) {
          window.sessionStorage.removeItem(SIGN_IN_PENDING);
          track("sign_in", { provider: auth.name });
        }
      } catch {
        /* storage unavailable */
      }
    } else {
      setAuth(null);
    }
  }, [user, loading]);

  const endPage = (path: string | null) => {
    if (!path) return;
    const now = performance.now();
    if (visibleSince.current !== null) visibleMs.current += now - visibleSince.current;
    visibleSince.current = null;
    const seconds = Math.round(visibleMs.current / 1000);
    visibleMs.current = 0;
    if (seconds > 0) track("page_leave", { seconds }, path);
  };

  // Page views (+ time on the page we just left) on every route change.
  useEffect(() => {
    if (currentPath.current !== null && currentPath.current !== pathname) endPage(currentPath.current);
    if (currentPath.current !== pathname) {
      currentPath.current = pathname;
      errorsOnPage.current = 0;
      visibleSince.current = document.visibilityState === "visible" ? performance.now() : null;
      track("page_view", { signed_in: !!user, theme: document.documentElement.dataset.theme ?? "light" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Time on page and delivery when the tab is hidden or closed.
  useEffect(() => {
    const onHide = () => {
      endPage(currentPath.current);
      void flush(true);
    };
    const onVisibility = () => {
      if (document.visibilityState === "hidden") onHide();
      else if (currentPath.current) visibleSince.current = performance.now();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onHide);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onHide);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Every click on a button, link or tab, labelled by its text (never inputs, never typed values).
  useEffect(() => {
    if (!isTrackingAllowed()) return;
    const onClick = (e: MouseEvent) => {
      const target = e.target as Element | null;
      let el = target?.closest?.(CLICKABLE) ?? null;
      // Clickable table rows (stock lists) and ARIA buttons that are not <button> elements.
      if (!el) {
        const alt = target?.closest?.("tbody tr, [role=button], [role=link]") ?? null;
        if (alt && getComputedStyle(alt).cursor === "pointer") el = alt;
      }
      if (!el) return;
      const props: Record<string, string | number | boolean | null> = {
        label:
          (el.tagName === "TR" ? el.querySelector("td")?.textContent?.trim().slice(0, 40) : elementLabel(el)) || "(no label)",
        tag: el.tagName.toLowerCase(),
      };
      if (el.tagName === "A") {
        try {
          const url = new URL((el as HTMLAnchorElement).href, window.location.href);
          props.href = url.origin === window.location.origin ? url.pathname : url.host;
        } catch {
          /* ignore malformed href */
        }
      }
      track("click", props);
    };
    document.addEventListener("click", onClick, { capture: true });
    return () => document.removeEventListener("click", onClick, { capture: true });
  }, []);

  // JavaScript errors, so crashes show up in the numbers instead of only in user complaints.
  useEffect(() => {
    if (!isTrackingAllowed()) return;
    const report = (message: string, source?: string, line?: number) => {
      if (/ResizeObserver loop/i.test(message) || errorsOnPage.current >= 5) return;
      errorsOnPage.current += 1;
      track("js_error", { message: message.slice(0, 150), source: (source ?? "").split("/").pop()?.slice(0, 60) ?? "", line: line ?? 0 });
    };
    const onError = (e: ErrorEvent) => report(e.message || "error", e.filename, e.lineno);
    const onRejection = (e: PromiseRejectionEvent) =>
      report(String((e.reason as Error | undefined)?.message ?? e.reason ?? "unhandled rejection"));
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  useReportWebVitals((metric) => {
    track("web_vital", { name: metric.name, value: Number(metric.value.toFixed(3)), rating: metric.rating ?? "" });
  });

  return null;
}

/** Call just before starting a sign-in so the eventual return (even after a redirect) is counted once. */
export function markSignInStarted() {
  try {
    window.sessionStorage.setItem(SIGN_IN_PENDING, "1");
  } catch {
    /* storage unavailable */
  }
  track("sign_in_started");
}
