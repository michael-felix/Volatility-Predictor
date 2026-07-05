import { ApiStatusBadge } from "@/components/ApiStatusBadge";
import { TickerListClient } from "@/components/TickerListClient";
import { api } from "@/lib/api";
import type { TickerWithLatestPrediction } from "@/lib/types";

export default async function HomePage() {
  let tickers: TickerWithLatestPrediction[] = [];
  let loadError: string | null = null;

  try {
    const tickerInfos = await api.getTickers();
    tickers = await Promise.all(
      tickerInfos.map(async (t) => {
        try {
          const history = await api.getPredictionHistory(t.ticker, 1);
          return { ...t, latestPrediction: history[0] ?? null };
        } catch {
          return { ...t, latestPrediction: null };
        }
      }),
    );
  } catch {
    loadError = "Could not reach the API. Is the backend running?";
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Market Overview</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Predicted volatility across tracked tickers.
          </p>
        </div>
        <ApiStatusBadge />
      </div>

      {loadError ? (
        <p className="text-sm text-[var(--status-critical)]">{loadError}</p>
      ) : (
        <TickerListClient tickers={tickers} />
      )}
    </div>
  );
}
