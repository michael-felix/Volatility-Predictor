import type { Metadata } from "next";
import { FadeIn } from "@/components/FadeIn";
import { api } from "@/lib/api";
import { modelLabel } from "@/lib/modelLabels";
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
        <FadeIn delay={0.05}>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-hairline)] text-left text-[var(--text-secondary)]">
                  <th className="px-4 py-3 font-medium">Model</th>
                  <th className="px-4 py-3 text-right font-medium">RMSE</th>
                  <th className="px-4 py-3 text-right font-medium">MAE</th>
                  <th className="px-4 py-3 text-right font-medium">R²</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(([name, scores]) => {
                  const isWinner = name === winningAlgorithm;
                  return (
                    <tr
                      key={name}
                      className={`border-b border-[var(--border-hairline)] last:border-0 ${
                        isWinner ? "bg-[var(--brand-tint)]" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{modelLabel(name)}</span>
                          {isWinner && (
                            <span className="rounded-full bg-[var(--brand)] px-2 py-0.5 text-xs font-medium text-white">
                              Best · in use
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {scores.rmse.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {scores.mae.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {scores.r2.toFixed(4)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </FadeIn>
      )}

      <FadeIn delay={0.1}>
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
            Model selection always uses{" "}
            <strong className="text-[var(--foreground)]">RMSE</strong>{" "}
            automatically, so the model marked &quot;Best · in use&quot;
            above is always the one actually serving predictions.
          </p>
        </div>
      </FadeIn>
    </div>
  );
}
