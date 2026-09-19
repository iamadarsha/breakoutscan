/**
 * Catch-all API proxy route.
 *
 * Forwards all /api/* requests to the backend service at runtime using
 * INTERNAL_API_URL (server-side env var, not baked at build time).
 *
 * Production: set INTERNAL_API_URL to the backend's real origin (see
 * config/production-env.example) — this is a server-only env var, never
 * baked into the client bundle.
 * Local dev: defaults to http://localhost:8001
 */
import { type NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.INTERNAL_API_URL ?? "http://localhost:8001";

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const url = `${BACKEND}/api/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");

  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
      // @ts-expect-error duplex required for streaming body
      duplex: "half",
    });

    // fetch() has already decoded the body, so forwarding the upstream
    // encoding/length headers would mislabel plain bytes as gzip and break
    // every response large enough to be compressed by the backend's edge.
    const responseHeaders = new Headers(res.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");
    responseHeaders.delete("transfer-encoding");

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    console.error("[API proxy] failed to reach backend:", url, err);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
export async function PUT(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
export async function OPTIONS(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, (await params).path);
}
