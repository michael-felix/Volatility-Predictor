"use client";

import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { ReactNode } from "react";

interface ModelComparisonChartProps {
  data: { name: string; label: string; rmse: number; isWinner: boolean }[];
}

/**
 * Horizontal bar ranking of RMSE across candidate models — RMSE is the
 * metric that actually decides the winner, so this chart visualizes the
 * same decision the table's "Best · in use" badge states. The winning
 * model's bar carries the brand color; every other bar is a neutral gray
 * (color follows identity — "the winner" — not an arbitrary per-model hue,
 * since these bars aren't a fixed categorical set that needs distinguishing
 * from each other beyond this one grouping).
 */
export function ModelComparisonChart({ data }: ModelComparisonChartProps) {
  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 48, bottom: 8, left: 8 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={110}
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Bar dataKey="rmse" radius={[0, 4, 4, 0]} maxBarSize={22} isAnimationActive={true}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.isWinner ? "var(--brand)" : "var(--chart-baseline)"}
              />
            ))}
            <LabelList
              dataKey="rmse"
              position="right"
              formatter={(value: ReactNode) => (typeof value === "number" ? value.toFixed(4) : "")}
              style={{ fill: "var(--text-secondary)", fontSize: 12 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
