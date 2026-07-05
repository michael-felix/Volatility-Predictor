"use client";

import { useEffect, useState } from "react";
import type { HealthResponse } from "@/lib/types";

type Status = "checking" | "ok" | "degraded" | "unreachable";

const STATUS_CONFIG: Record<Status, { label: string; color: string }> = {
  checking: { label: "Checking API…", color: "var(--text-muted)" },
  ok: { label: "API online", color: "var(--status-good)" },
  degraded: { label: "API degraded (DB unreachable)", color: "var(--status-warning)" },
  unreachable: { label: "API unreachable", color: "var(--status-critical)" },
};

/** Polls GET /api/health (a same-origin Next.js route that proxies the
 * backend) so the dashboard always shows current API/DB status — never
 * color alone: an icon dot is paired with a text label per the project's
 * accessibility conventions. Calling the proxy rather than the backend
 * directly matters concretely here: some ad-blocker filter lists flag
 * `/health`-style paths as tracking beacons and silently drop the request,
 * which broke this badge for those visitors even though the API was fine. */
export function ApiStatusBadge() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        const health = (await response.json()) as HealthResponse;
        if (cancelled) return;
        setStatus(health.mongodb_connected ? "ok" : "degraded");
      } catch {
        if (!cancelled) setStatus("unreachable");
      }
    }

    check();
    const interval = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const { label, color } = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
      <span
        aria-hidden
        className="inline-block h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span>{label}</span>
    </div>
  );
}
