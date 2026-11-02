import { ArrowDown, ArrowUp, Equal, type LucideIcon } from "lucide-react";

import type { Overview } from "@/lib/analytics";
import { formatMoney, formatMonth, formatPercent } from "@/lib/format";

function StatCard({
  label,
  value,
  note,
  highlight = false,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
  highlight?: boolean;
}) {
  const style = highlight ? "border-brand-border bg-brand-tint" : "border-border bg-surface";
  return (
    <div className={`rounded-card border p-5 shadow-card ${style}`}>
      <p className="text-sm text-muted">{label}</p>
      <div className="mt-1 text-2xl font-bold">{value}</div>
      {note && <p className="mt-1 text-sm text-muted">{note}</p>}
    </div>
  );
}

const CHANGE_STYLES: Record<"up" | "down" | "same", { icon: LucideIcon; word: string; tone: string }> =
  {
    up: { icon: ArrowUp, word: "higher", tone: "text-danger" },
    down: { icon: ArrowDown, word: "lower", tone: "text-success" },
    same: { icon: Equal, word: "no change", tone: "text-muted" },
  };

function ChangeValue({ percent }: { percent: string }) {
  const number = Number(percent);
  const direction = number > 0 ? "up" : number < 0 ? "down" : "same";
  const { icon: Icon, word, tone } = CHANGE_STYLES[direction];
  return (
    <span className={`flex items-center gap-1 ${tone}`}>
      <Icon aria-hidden className="size-5 shrink-0" />
      {direction === "same" ? word : `${formatPercent(percent)} ${word}`}
    </span>
  );
}

function changeNote(overview: Overview): string {
  const { change } = overview;
  if (change.percent === null) {
    return change.previous_cost === null
      ? "No earlier month to compare"
      : "Month not finished, so no fair comparison yet";
  }
  if (change.compared_days !== null) {
    return `Compared with the first ${change.compared_days} days of last month`;
  }
  return "Compared with the month before";
}

export function StatCards({ overview, months }: { overview: Overview; months: number }) {
  const { currency } = overview;
  const latestLabel = `${formatMonth(overview.latest_month)}${
    overview.latest_is_partial ? " so far" : ""
  }`;
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        highlight
        label="Total Expenditure"
        value={formatMoney(overview.total, currency)}
        note={`Last ${months} months`}
      />
      <StatCard label={latestLabel} value={formatMoney(overview.latest_cost, currency)} />
      <StatCard
        label="Month before"
        value={
          overview.previous_cost === null ? "No bill" : formatMoney(overview.previous_cost, currency)
        }
      />
      <StatCard
        label="Change"
        value={
          overview.change.percent === null ? (
            "Not available"
          ) : (
            <ChangeValue percent={overview.change.percent} />
          )
        }
        note={changeNote(overview)}
      />
    </div>
  );
}
