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

import type { Overview } from "@/lib/analytics";
import { formatMoney, formatMonth } from "@/lib/format";

const COLORS = {
  line: "var(--token-chart-line)",
  area: "var(--token-chart-area)",
  grid: "var(--token-border)",
  axis: "var(--token-muted)",
  surface: "var(--token-surface)",
};
const CHART_HEIGHT = 240;
const AXIS_WIDTH = 64;
const LABEL_SIZE = 12;

type TooltipProps = {
  active?: boolean;
  payload?: { payload: { month: string; label: string; value: number | null } }[];
  currency: string;
};

function ChartTooltip({ active, payload, currency }: TooltipProps) {
  const point = payload?.[0]?.payload;
  if (!active || !point) {
    return null;
  }
  return (
    <div className="rounded-control border border-border bg-surface px-3 py-2 shadow-card">
      <p className="text-sm text-muted">{point.label}</p>
      <p className="font-semibold">
        {point.value === null ? "No bill" : formatMoney(point.value, currency)}
      </p>
    </div>
  );
}

/** One series, so the card's title names it and no legend is needed. The axis starts at zero. */
export function SpendingChart({ overview }: { overview: Overview }) {
  const { currency, trend } = overview;
  const data = trend.map((point) => ({
    month: point.month,
    label: formatMonth(point.month),
    value: point.cost === null ? null : Number(point.cost),
  }));

  return (
    <div>
      <div
        role="img"
        aria-label={`Spending per month. Latest: ${formatMoney(overview.latest_cost, currency)}.`}
      >
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={COLORS.grid} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fill: COLORS.axis, fontSize: LABEL_SIZE }}
            />
            <YAxis
              domain={[0, "auto"]}
              width={AXIS_WIDTH}
              tickLine={false}
              axisLine={false}
              tick={{ fill: COLORS.axis, fontSize: LABEL_SIZE }}
              tickFormatter={(value: number) => formatMoney(value, currency).replace(/\.00$/, "")}
            />
            <Tooltip
              content={<ChartTooltip currency={currency} />}
              cursor={{ stroke: COLORS.axis }}
            />
            <Area
              type="linear"
              dataKey="value"
              stroke={COLORS.line}
              strokeWidth={2}
              fill={COLORS.area}
              fillOpacity={1}
              dot={{ r: 4, fill: COLORS.line, stroke: COLORS.surface, strokeWidth: 2 }}
              activeDot={{ r: 6, fill: COLORS.line, stroke: COLORS.surface, strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-muted">View as table</summary>
        <table className="mt-2 w-full">
          <thead>
            <tr className="text-left text-muted">
              <th scope="col" className="py-1 font-medium">
                Month
              </th>
              <th scope="col" className="py-1 text-right font-medium">
                Cost
              </th>
            </tr>
          </thead>
          <tbody>
            {trend.map((point) => (
              <tr key={point.month} className="border-t border-border">
                <td className="py-1">{formatMonth(point.month)}</td>
                <td className="py-1 text-right">
                  {point.cost === null ? "No bill" : formatMoney(point.cost, currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
