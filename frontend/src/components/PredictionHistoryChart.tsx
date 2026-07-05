"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PredictionResponse } from "@/lib/types";

interface PredictionHistoryChartProps {
  predictions: PredictionResponse[];
}

interface TooltipPayloadItem {
  value: number;
  payload: {
    label: string;
    asOfDate: string;
    annualizedVolPct: number;
    expectedMoveDollars: number;
  };
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-md border border-black/10 bg-[var(--chart-surface)] px-3 py-2 text-sm shadow-sm dark:border-white/10">
      <div className="text-[var(--text-secondary)]">{point.label}</div>
      <div className="font-semibold">{point.annualizedVolPct.toFixed(1)}% annualized</div>
      <div className="text-xs text-[var(--text-muted)]">
        Expected move: ±${point.expectedMoveDollars.toFixed(2)} · based on {point.asOfDate} data
      </div>
    </div>
  );
}

/**
 * Single-series line-with-wash chart of annualized volatility over time.
 * A single series needs no legend box (the title already names what's
 * plotted) — identity comes from the chart heading, not a swatch.
 */
export function PredictionHistoryChart({ predictions }: PredictionHistoryChartProps) {
  if (predictions.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-black/10 text-sm text-[var(--text-muted)] dark:border-white/10">
        No prediction history yet — run a prediction to start building this chart.
      </div>
    );
  }

  // Keyed on when each prediction was actually generated, not the trading
  // day its data is drawn from (`as_of_date`) — the latter only changes
  // once a day when new market data arrives, so several predictions run
  // back-to-back on the same day's data would otherwise collapse onto a
  // single duplicated x-axis label and the chart would read as flat.
  const formatter = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  // API returns newest-first; charts read left-to-right chronologically.
  const data = [...predictions].reverse().map((p) => ({
    label: formatter.format(new Date(p.generated_at)),
    asOfDate: p.as_of_date,
    annualizedVolPct: p.annualized_volatility_pct,
    expectedMoveDollars: p.expected_move_dollars,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid
            stroke="var(--chart-grid)"
            strokeWidth={1}
            vertical={false}
          />
          <XAxis
            dataKey="label"
            stroke="var(--chart-baseline)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            stroke="var(--chart-baseline)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(value: number) => `${value.toFixed(0)}%`}
          />
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="annualizedVolPct"
            stroke="var(--chart-line)"
            strokeWidth={2}
            fill="var(--chart-area)"
            fillOpacity={0.1}
            dot={{ r: 3, fill: "var(--chart-line)", stroke: "var(--chart-surface)", strokeWidth: 2 }}
            activeDot={{ r: 4, stroke: "var(--chart-surface)", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
