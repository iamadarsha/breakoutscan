import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  if (process.env.NEXT_PUBLIC_AUTH_PROVIDER === "firebase") return supabaseResponse;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return supabaseResponse;

  const supabase = createServerClient(
    url,
    key,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // Just refresh the session — don't gate any pages behind auth.
  // Auth is only required at the feature level (e.g. watchlist add).
  //
  // Never let a Supabase outage break every single page load: found live
  // (2026-09-15) that a stale/unreachable NEXT_PUBLIC_SUPABASE_URL here
  // means this call fails on literally every request site-wide, since
  // this middleware's matcher covers nearly the whole app.
  try {
    await supabase.auth.getUser();
  } catch (err) {
    console.error("[supabase middleware] session refresh failed:", err);
  }

  return supabaseResponse;
}
