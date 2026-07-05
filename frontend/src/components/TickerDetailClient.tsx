"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ModelInfoResponse, PredictionResponse } from "@/lib/types";
import { PredictionHistoryChart } from "./PredictionHistoryChart";
import { StatTile } from "./StatTile";

interface TickerDetailClientProps {
  ticker: string;
  initialHistory: PredictionResponse[];
}

export function TickerDetailClient({ ticker, initialHistory }: TickerDetailClientProps) {
  const [history, setHistory] = useState(initialHistory);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const latest = history[0] ?? null;

  useEffect(() => {
    api
      .getModelInfo()
      .then(setModelInfo)
      .catch(() => setModelInfo(null));
  }, []);

  async function handlePredict() {
    setPredicting(true);
    setError(null);
    try {
      const prediction = await api.predict(ticker);
      setHistory((prev) => [prediction, ...prev]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Prediction failed.");
    } finally {
      setPredicting(false);
    }
  }

  async function handleTrain() {
    setTraining(true);
    setError(null);
    try {
      // Trains the one shared, pooled model across all configured tickers
      // (see project architecture notes) — not a per-ticker model.
      const info = await api.train(null, 5);
      setModelInfo(info);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Training failed.");
    } finally {
      setTraining(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handlePredict}
          disabled={predicting}
          className="rounded-md bg-[var(--chart-line)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {predicting ? "Predicting…" : "Predict volatility"}
        </button>
        <button
          onClick={handleTrain}
          disabled={training}
          className="rounded-md border border-black/10 px-4 py-2 text-sm font-medium transition hover:border-[var(--chart-line)] disabled:opacity-50 dark:border-white/10"
        >
          {training ? "Training…" : "Retrain shared model (all tickers)"}
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-[var(--status-critical)]/30 bg-[var(--status-critical)]/10 px-3 py-2 text-sm text-[var(--status-critical)]">
          {error}
        </div>
      )}

      {latest && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Annualized volatility"
            value={`${latest.annualized_volatility_pct.toFixed(1)}%`}
            sublabel={`${latest.horizon_days}-day horizon`}
          />
          <StatTile
            label="Expected move"
            value={`±$${latest.expected_move_dollars.toFixed(2)}`}
            sublabel={`±${latest.expected_move_pct.toFixed(2)}%`}
          />
          <StatTile label="Current price" value={`$${latest.current_price.toFixed(2)}`} />
          <StatTile
            label="Expected range"
            value={`$${latest.expected_price_range_low.toFixed(0)}–$${latest.expected_price_range_high.toFixed(0)}`}
          />
        </div>
      )}

      <div>
        <h2 className="mb-2 text-sm font-medium text-[var(--text-secondary)]">
          Prediction history
        </h2>
        <PredictionHistoryChart predictions={history} />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium text-[var(--text-secondary)]">Active model</h2>
        {modelInfo ? (
          <div className="rounded-lg border border-black/10 bg-[var(--chart-surface)] p-4 text-sm dark:border-white/10">
            <div>
              <span className="text-[var(--text-secondary)]">Algorithm:</span>{" "}
              {modelInfo.algorithm}
            </div>
            <div>
              <span className="text-[var(--text-secondary)]">Version:</span> {modelInfo.version}
            </div>
            <div>
              <span className="text-[var(--text-secondary)]">Training samples:</span>{" "}
              {modelInfo.training_samples}
            </div>
            <div>
              <span className="text-[var(--text-secondary)]">CV RMSE:</span>{" "}
              {modelInfo.metrics.rmse?.toFixed(4) ?? "—"}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">
            No model trained yet — click &quot;Retrain shared model&quot; above.
          </p>
        )}
      </div>
    </div>
  );
}
