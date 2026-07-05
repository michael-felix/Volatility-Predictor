"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { getRiskLevel } from "@/lib/riskLevel";
import type { ModelInfoResponse, PredictionResponse } from "@/lib/types";
import { PredictionHistoryChart } from "./PredictionHistoryChart";
import { RiskBadge } from "./RiskBadge";
import { Spinner } from "./Spinner";
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
        <motion.button
          onClick={handlePredict}
          disabled={predicting}
          whileTap={{ scale: 0.96 }}
          className="flex items-center gap-2 rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {predicting && <Spinner />}
          {predicting ? "Predicting…" : "Predict volatility"}
        </motion.button>
        <motion.button
          onClick={handleTrain}
          disabled={training}
          whileTap={{ scale: 0.96 }}
          className="flex items-center gap-2 rounded-md border border-[var(--border-hairline)] px-4 py-2 text-sm font-medium transition hover:border-[var(--brand)] disabled:opacity-50"
        >
          {training && <Spinner />}
          {training ? "Training…" : "Retrain shared model (all tickers)"}
        </motion.button>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden rounded-md border border-[var(--status-critical)]/30 bg-[var(--status-critical)]/10 px-3 py-2 text-sm text-[var(--status-critical)]"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {latest && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-4"
        >
          {/* Each StatTile below crossfades its own value when a new
              prediction arrives (keyed internally on the value string) --
              this block itself never unmounts/remounts on new data, since
              doing so via AnimatePresence previously caused a layout shift
              that corrupted the chart's ResizeObserver-driven redraw. */}
          <div className="card flex items-start gap-3 p-4">
            <RiskBadge level={getRiskLevel(latest.annualized_volatility_pct)} />
            <p className="text-sm text-[var(--text-secondary)]">
              Based on recent patterns,{" "}
              <strong className="text-[var(--foreground)]">{ticker}</strong>&apos;s price could
              reasonably move{" "}
              <strong className="text-[var(--foreground)]">
                ±${latest.expected_move_dollars.toFixed(2)} (±
                {latest.expected_move_pct.toFixed(1)}%)
              </strong>{" "}
              over the next {latest.horizon_days} trading days. Not sure what this means?{" "}
              <Link href="/guide" className="underline hover:text-[var(--foreground)]">
                Read the guide
              </Link>
              .
            </p>
          </div>

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
        </motion.div>
      )}

      <div>
        <h2 className="mb-2 text-sm font-medium text-[var(--text-secondary)]">
          Prediction history
        </h2>
        <PredictionHistoryChart predictions={history} />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-[var(--text-secondary)]">Active model</h2>
          <Link
            href="/models"
            className="text-xs text-[var(--brand)] underline hover:no-underline"
          >
            Compare all models →
          </Link>
        </div>
        {modelInfo ? (
          <div className="card p-4 text-sm">
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
