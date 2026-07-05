"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { TickerInfo } from "@/lib/types";

interface TickerListClientProps {
  tickers: TickerInfo[];
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
        className="w-full max-w-xs rounded-md border border-black/10 bg-[var(--chart-surface)] px-3 py-2 text-sm outline-none focus:border-[var(--chart-line)] dark:border-white/10"
      />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((t) => (
          <Link
            key={t.ticker}
            href={`/tickers/${t.ticker}`}
            className="rounded-lg border border-black/10 bg-[var(--chart-surface)] p-4 transition hover:border-[var(--chart-line)] dark:border-white/10"
          >
            <div className="text-lg font-semibold">{t.ticker}</div>
            <div className="mt-1 text-sm text-[var(--text-secondary)]">
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
