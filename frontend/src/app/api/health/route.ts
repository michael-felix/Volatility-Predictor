import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Proxies the backend's /health check through Next.js's own server, so the
 * browser only ever calls same-origin `/api/health` rather than reaching
 * out to the backend's onrender.com domain directly. This isn't just about
 * hiding the backend URL — some ad-blocker filter lists specifically flag
 * path patterns like `/health`/`/ping`/`/status` as tracking-beacon
 * heuristics, which was silently breaking the status badge for anyone with
 * an ad blocker enabled, even though the API itself was working fine.
 */
export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ status: "unreachable", mongodb_connected: false }, { status: 502 });
  }
}
