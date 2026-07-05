import type { Metadata } from "next";
import { RiskBadge } from "@/components/RiskBadge";

export const metadata: Metadata = {
  title: "Guide — Volatility Platform",
  description: "How to read and use the volatility dashboard.",
};

export default function GuidePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Guide</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          What volatility means, how to read your predictions, and how this
          dashboard works.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">What is volatility?</h2>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          Volatility measures how much a stock&apos;s price tends to swing up
          or down over time — not whether it&apos;s going up or down, just how{" "}
          <em>turbulent</em>{" "}
          the ride is likely to be. A stock with low volatility moves in
          small, steady steps; a stock with high volatility can swing
          sharply in either direction over a short period. Volatility
          isn&apos;t inherently bad — it can mean bigger losses{" "}
          <em>or</em>{" "}
          bigger gains — but it does mean less certainty about where the
          price will land.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Reading your predictions</h2>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          Each prediction on this dashboard breaks down into four numbers.
          Here&apos;s what they mean, using an example prediction:
        </p>

        <div className="card space-y-3 p-4 text-sm">
          <div>
            <span className="font-semibold">Annualized volatility — 24.5%</span>
            <p className="mt-0.5 text-[var(--text-secondary)]">
              The industry-standard way to quote volatility, scaled to a
              one-year period so it&apos;s comparable across different stocks
              and time horizons — similar to how the VIX index is quoted.
              Higher means more turbulent.
            </p>
          </div>
          <div>
            <span className="font-semibold">Expected move — ±$10.67 (±3.5%)</span>
            <p className="mt-0.5 text-[var(--text-secondary)]">
              A concrete translation of that percentage into dollars, for the
              specific forecast horizon (e.g. the next 5 trading days) — the
              price could reasonably move this much in either direction.
            </p>
          </div>
          <div>
            <span className="font-semibold">Expected range — $298–$319</span>
            <p className="mt-0.5 text-[var(--text-secondary)]">
              The current price plus/minus the expected move — a rough band
              the price is likely to stay within over the forecast horizon.
            </p>
          </div>
          <div>
            <span className="font-semibold">Current price</span>
            <p className="mt-0.5 text-[var(--text-secondary)]">
              The most recent closing price the prediction is based on.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Risk levels</h2>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          To make annualized volatility easier to scan at a glance, this
          dashboard buckets it into three plain-language levels. These
          thresholds are illustrative — broad market indices have
          historically averaged roughly 15–20% annualized volatility, and
          individual stocks typically run higher:
        </p>
        <div className="card space-y-3 p-4 text-sm">
          <div className="flex items-center gap-3">
            <RiskBadge level="low" />
            <span className="text-[var(--text-secondary)]">Below 15% annualized</span>
          </div>
          <div className="flex items-center gap-3">
            <RiskBadge level="medium" />
            <span className="text-[var(--text-secondary)]">15–30% annualized</span>
          </div>
          <div className="flex items-center gap-3">
            <RiskBadge level="high" />
            <span className="text-[var(--text-secondary)]">Above 30% annualized</span>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">How the model works</h2>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          Predictions come from a machine learning model trained on
          historical daily price data — recent returns, rolling volatility,
          and moving averages — pooled across every ticker this dashboard
          tracks, rather than one model per stock. This gives the model more
          data to learn general volatility patterns from, and lets it score
          any ticker with enough price history, not just ones it happened to
          train on.
        </p>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          The model is retrained periodically as new price data comes in.
          You can see which model version produced a given prediction, and
          its training details, under &quot;Active model&quot; on each
          ticker&apos;s page.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Using the dashboard</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-[var(--text-secondary)]">
          <li>
            <strong className="text-[var(--foreground)]">Search</strong>{" "}
            for a ticker from the Dashboard, or click a card to open its
            detail page.
          </li>
          <li>
            <strong className="text-[var(--foreground)]">Predict volatility</strong>{" "}
            runs the model fresh against the latest price data for that
            ticker.
          </li>
          <li>
            <strong className="text-[var(--foreground)]">Retrain shared model</strong>{" "}
            retrains the one model used across all tickers — useful after
            new price data has been ingested.
          </li>
          <li>
            The{" "}
            <strong className="text-[var(--foreground)]">prediction history chart</strong>{" "}
            tracks how a ticker&apos;s predicted volatility has changed over
            past predictions.
          </li>
        </ul>
      </section>

      <section className="card space-y-2 p-4">
        <h2 className="text-sm font-semibold">Disclaimer</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          This is an educational/portfolio project, not a financial product.
          Predictions are statistical estimates based on historical price
          patterns — they are not guarantees of future price behavior and
          should not be used as the sole basis for any investment decision.
          Markets can move for reasons no historical-pattern model can
          anticipate.
        </p>
      </section>
    </div>
  );
}
