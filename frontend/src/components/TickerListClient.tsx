"use client";

import { AnimatePresence, motion, type Variants } from "framer-motion";
import Link from "next/link";
import { useMemo, useState } from "react";
import { getRiskLevel } from "@/lib/riskLevel";
import type { TickerWithLatestPrediction } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";

interface TickerListClientProps {
  tickers: TickerWithLatestPrediction[];
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

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
        className="w-full max-w-xs rounded-md border border-[var(--border-hairline)] bg-[var(--chart-surface)] px-3 py-2 text-sm outline-none transition-colors hover:border-[var(--brand)]/50 focus:border-[var(--brand)]"
      />

      <motion.div
        className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        <AnimatePresence mode="popLayout">
          {filtered.map((t) => (
            <motion.div
              key={t.ticker}
              layout
              variants={cardVariants}
              exit={{ opacity: 0, scale: 0.96 }}
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <Link
                href={`/tickers/${t.ticker}`}
                className="card block p-4 transition-colors hover:border-[var(--brand)] hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <span className="text-lg font-semibold">{t.ticker}</span>
                  {t.latestPrediction && (
                    <RiskBadge
                      level={getRiskLevel(t.latestPrediction.annualized_volatility_pct)}
                    />
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
            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>

      {filtered.length === 0 && (
        <div className="mt-4 text-sm text-[var(--text-muted)]">
          No tickers match &quot;{query}&quot;.
        </div>
      )}
    </div>
  );
}
