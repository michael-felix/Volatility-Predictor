import Link from "next/link";
import { TickerDetailClient } from "@/components/TickerDetailClient";
import { api } from "@/lib/api";
import type { PredictionResponse } from "@/lib/types";

export default async function TickerDetailPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;

  let history: PredictionResponse[] = [];
  try {
    history = await api.getPredictionHistory(ticker);
  } catch {
    // No history yet is a normal state, not an error worth surfacing.
    history = [];
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Link href="/" className="text-sm text-[var(--text-secondary)] hover:underline">
          ← All tickers
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">{ticker}</h1>
      </div>

      <TickerDetailClient ticker={ticker} initialHistory={history} />
    </div>
  );
}
