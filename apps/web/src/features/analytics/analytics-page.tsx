"use client";

import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Card } from "@/components/card";
import { SpendingChart } from "@/components/charts/spending-chart";
import { TopServices } from "@/components/charts/top-services";
import { ErrorPanel, LoadingPanel } from "@/components/data-states";
import { PeriodSelect } from "@/components/period-select";
import { ProviderSelect } from "@/components/provider-select";
import {
  useComparison,
  useOverview,
  useUnusualCosts,
  type CostType,
  type Filters,
  type Overview,
} from "@/lib/analytics";
import { formatMoney, formatMonth, formatPercent } from "@/lib/format";

const DEFAULT_MONTHS = 6;
const SELECT_STYLE =
  "rounded-control border border-border bg-surface px-3 py-2 font-medium text-foreground";

function CompareMonths({ filters, overview }: { filters: Filters; overview: Overview }) {
  const months = overview.trend.filter((point) => point.cost !== null).map((point) => point.month);
  const [first, setFirst] = useState<string>();
  const [second, setSecond] = useState<string>();
  const firstMonth = first ?? months.at(-2);
  const secondMonth = second ?? months.at(-1);
  const { data: rows } = useComparison(filters, firstMonth, secondMonth);

  if (months.length < 2) {
    return <p className="text-muted">You need bills for two months to compare them.</p>;
  }

  function monthSelect(label: string, value: string | undefined, onChange: (v: string) => void) {
    return (
      <label className="text-sm text-muted">
        {label}{" "}
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={SELECT_STYLE}
        >
          {months.map((month) => (
            <option key={month} value={month}>
              {formatMonth(month)}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        {monthSelect("Compare", firstMonth, setFirst)}
        {monthSelect("with", secondMonth, setSecond)}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted">
              <th scope="col" className="py-2 font-medium">
                Service
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                {firstMonth && formatMonth(firstMonth)}
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                {secondMonth && formatMonth(secondMonth)}
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Change
              </th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.service} className="border-t border-border">
                <td className="py-2 font-medium">{row.service}</td>
                <td className="py-2 text-right">{formatMoney(row.first_cost, overview.currency)}</td>
                <td className="py-2 text-right">
                  {formatMoney(row.second_cost, overview.currency)}
                </td>
                <td className="py-2 text-right">
                  {Number(row.difference) > 0 ? "+" : ""}
                  {formatMoney(row.difference, overview.currency)}
                  {row.percent !== null && ` (${formatPercent(row.percent)})`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UnusualSpending({ filters, overview }: { filters: Filters; overview: Overview }) {
  const { data: items } = useUnusualCosts(filters);

  if (!items?.length) {
    return <p className="text-muted">Nothing unusual found in your latest full month.</p>;
  }
  return (
    <ul className="grid gap-3">
      {items.map((item) => (
        <li key={item.service} className="flex gap-3 rounded-control bg-danger-tint p-3">
          <CircleAlert aria-hidden className="size-5 shrink-0 text-danger" />
          <p>
            <span className="font-semibold">{item.service}</span> cost{" "}
            {formatMoney(item.cost, overview.currency)} in {formatMonth(item.month)}. It usually
            costs about {formatMoney(item.usual_cost, overview.currency)}.
          </p>
        </li>
      ))}
    </ul>
  );
}

export function AnalyticsPage() {
  const [months, setMonths] = useState(DEFAULT_MONTHS);
  const [costType, setCostType] = useState<CostType>("billed");
  const [currency, setCurrency] = useState<string>();
  const [provider, setProvider] = useState<string>();
  const filters = { months, costType, currency, provider };
  const { data: overview, error, isPending, refetch } = useOverview(filters);

  return (
    <section>
      <h1 className="text-3xl font-bold">Analytics</h1>
      <p className="mt-1 text-muted">Explore your spending history and find unusual changes.</p>

      <div className="my-6 flex flex-wrap items-center gap-3">
        <PeriodSelect value={months} onChange={setMonths} />
        <label className="text-sm text-muted">
          <span className="sr-only">Cost type</span>
          <select
            value={costType}
            onChange={(event) => setCostType(event.target.value as CostType)}
            className={SELECT_STYLE}
          >
            <option value="billed">Billed cost</option>
            <option value="effective">Effective cost</option>
          </select>
        </label>
        {overview && (
          <ProviderSelect providers={overview.providers} value={provider} onChange={setProvider} />
        )}
        {overview && overview.currencies.length > 1 && (
          <label className="text-sm text-muted">
            <span className="sr-only">Currency</span>
            <select
              value={overview.currency}
              onChange={(event) => setCurrency(event.target.value)}
              className={SELECT_STYLE}
            >
              {overview.currencies.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {isPending && <LoadingPanel label="Loading your analytics…" />}
      {error && <ErrorPanel message={error.message} onRetry={() => refetch()} />}
      {overview === null && (
        <div className="rounded-card border border-border bg-surface p-10 text-center">
          <p className="font-medium">No spending to analyse yet</p>
          <Link href="/documents" className="mt-2 inline-block font-medium text-brand">
            Upload a bill
          </Link>
        </div>
      )}
      {overview && (
        <div className="grid gap-4">
          {overview.currencies.length > 1 && (
            <p className="rounded-control bg-brand-tint p-3 text-sm">
              Your bills use {overview.currencies.length} currencies. Each one is shown on its own,
              and they are never added together.
            </p>
          )}
          <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
            <Card title="Monthly Cloud Spending">
              <SpendingChart overview={overview} />
            </Card>
            <Card title={`Top Services (${formatMonth(overview.latest_month)})`}>
              <TopServices overview={overview} />
            </Card>
          </div>
          <Card title="Compare Two Months">
            <CompareMonths filters={filters} overview={overview} />
          </Card>
          <Card title="Unusual Spending">
            <UnusualSpending filters={filters} overview={overview} />
          </Card>
        </div>
      )}
    </section>
  );
}
