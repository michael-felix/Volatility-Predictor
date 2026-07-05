import { ApiStatusBadge } from "@/components/ApiStatusBadge";
import { TickerListClient } from "@/components/TickerListClient";
import { api } from "@/lib/api";
import type { TickerInfo } from "@/lib/types";

export default async function HomePage() {
  let tickers: TickerInfo[] = [];
  let loadError: string | null = null;

  try {
    tickers = await api.getTickers();
  } catch {
    loadError = "Could not reach the API. Is the backend running?";
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Tickers</h1>
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
