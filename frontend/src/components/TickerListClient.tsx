"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { getRiskLevel } from "@/lib/riskLevel";
import type { TickerWithLatestPrediction } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";

interface TickerListClientProps {
  tickers: TickerWithLatestPrediction[];
}

export function TickerListClient({ tickers }: TickerListClientProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const normalized = query.trim().toUpperCase();
    if (!normalized) return tickers;
    return tickers.filter((t) => t.ticker.includes(normalized));
  }, [tickers, query]);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search tickers…"
        className="w-full max-w-xs rounded-md border border-[var(--border-hairline)] bg-[var(--chart-surface)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
      />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((t) => (
          <Link
            key={t.ticker}
            href={`/tickers/${t.ticker}`}
            className="card p-4 transition hover:border-[var(--brand)] hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">{t.ticker}</span>
              {t.latestPrediction && (
                <RiskBadge level={getRiskLevel(t.latestPrediction.annualized_volatility_pct)} />
              )}
            </div>

            {t.latestPrediction ? (
              <div className="mt-2">
                <div className="text-xl font-semibold">
                  {t.latestPrediction.annualized_volatility_pct.toFixed(1)}%
                </div>
                <div className="text-xs text-[var(--text-muted)]">annualized volatility</div>
              </div>
            ) : (
              <div className="mt-2 text-sm text-[var(--text-muted)]">No prediction yet</div>
            )}

            <div className="mt-3 border-t border-[var(--border-hairline)] pt-2 text-xs text-[var(--text-muted)]">
              {t.bar_count > 0
                ? `${t.bar_count} bars · through ${t.latest_trading_date}`
                : "No data ingested yet"}
            </div>
          </Link>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-sm text-[var(--text-muted)]">
            No tickers match &quot;{query}&quot;.
          </div>
        )}
      </div>
    </div>
  );
}
