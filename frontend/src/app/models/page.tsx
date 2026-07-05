import type { Metadata } from "next";
import { FadeIn } from "@/components/FadeIn";
import { ModelComparisonChart } from "@/components/ModelComparisonChart";
import { api } from "@/lib/api";
import { modelDescription, modelLabel } from "@/lib/modelLabels";
import type { ModelInfoResponse } from "@/lib/types";

export const metadata: Metadata = {
  title: "Model Comparison — Volatility Platform",
  description: "Compare candidate models and their cross-validated accuracy.",
};

export default async function ModelsPage() {
  let modelInfo: ModelInfoResponse | null = null;
  try {
    modelInfo = await api.getModelInfo();
  } catch {
    modelInfo = null;
  }

  const candidates = modelInfo
    ? Object.entries(modelInfo.candidate_metrics).sort(([, a], [, b]) => a.rmse - b.rmse)
    : [];
  const winningAlgorithm = modelInfo?.algorithm;

  const chartData = candidates.map(([name, scores]) => ({
    name,
    label: modelLabel(name),
    rmse: scores.rmse,
    isWinner: name === winningAlgorithm,
  }));

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <FadeIn>
        <div>
          <h1 className="text-2xl font-semibold">Model Comparison</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Every candidate algorithm is cross-validated on the same data each
            training run; the lowest-error model is automatically used for
            live predictions — no manual override.
          </p>
        </div>
      </FadeIn>

      {candidates.length === 0 ? (
        <FadeIn delay={0.05}>
          <p className="text-sm text-[var(--text-muted)]">
            No model has been trained yet — train one from any ticker&apos;s
            page first.
          </p>
        </FadeIn>
      ) : (
        <>
          <FadeIn delay={0.05}>
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-medium text-[var(--text-secondary)]">
                RMSE by model (lower is better)
              </h2>
              <ModelComparisonChart data={chartData} />
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-hairline)] text-left text-[var(--text-secondary)]">
                    <th className="px-4 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 text-right font-medium">RMSE</th>
                    <th className="px-4 py-3 text-right font-medium">MAE</th>
                    <th className="px-4 py-3 text-right font-medium">R²</th>
                    <th className="px-4 py-3 text-right font-medium">QLIKE</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map(([name, scores]) => {
                    const isWinner = name === winningAlgorithm;
                    const description = modelDescription(name);
                    return (
                      <tr
                        key={name}
                        className={`border-b border-[var(--border-hairline)] transition-colors last:border-0 hover:bg-[var(--brand-tint)] ${
                          isWinner ? "bg-[var(--brand-tint)]" : ""
                        }`}
                      >
                        <td className="max-w-xs px-4 py-3 align-top">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{modelLabel(name)}</span>
                            {isWinner && (
                              <span className="rounded-full bg-[var(--brand)] px-2 py-0.5 text-xs font-medium whitespace-nowrap text-white">
                                Best · in use
                              </span>
                            )}
                          </div>
                          {description && (
                            <p className="mt-1 text-xs leading-relaxed text-[var(--text-muted)]">
                              {description}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right align-top tabular-nums">
                          {scores.rmse.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-right align-top tabular-nums">
                          {scores.mae.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-right align-top tabular-nums">
                          {scores.r2.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-right align-top tabular-nums">
                          {scores.qlike.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </FadeIn>
        </>
      )}

      <FadeIn delay={0.15}>
        <div className="card space-y-2 p-4 text-sm text-[var(--text-secondary)]">
          <p>
            <strong className="text-[var(--foreground)]">RMSE</strong>{" "}
            and{" "}
            <strong className="text-[var(--foreground)]">MAE</strong>{" "}
            measure average prediction error on held-out data the model
            wasn&apos;t trained on — lower is better.{" "}
            <strong className="text-[var(--foreground)]">R²</strong>{" "}
            measures how much better the model does than just guessing the
            average — higher is better; 0 means no better than average,
            negative means worse.
          </p>
          <p>
            <strong className="text-[var(--foreground)]">QLIKE</strong>{" "}
            is the standard loss function used specifically for volatility
            forecasts in financial research, rather than a generic regression
            metric — lower is better. It penalizes{" "}
            <em>underpredicting</em> volatility (missing a real spike) more
            heavily than overpredicting by the same amount, matching the
            real-world cost of being caught off-guard by risk.
          </p>
          <p>
            Model selection always uses{" "}
            <strong className="text-[var(--foreground)]">RMSE</strong>{" "}
            automatically, so the model marked &quot;Best · in use&quot;
            above is always the one actually serving predictions — QLIKE is
            shown alongside it as a second, domain-specific opinion, and the
            two don&apos;t always agree on the ranking.
          </p>
        </div>
      </FadeIn>
    </div>
  );
}
