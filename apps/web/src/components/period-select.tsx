import { PERIOD_OPTIONS } from "@/lib/analytics";

type PeriodSelectProps = {
  value: number;
  onChange: (months: number) => void;
};

export function PeriodSelect({ value, onChange }: PeriodSelectProps) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted">
      <select
        aria-label="Period"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="rounded-control border border-border bg-surface px-3 py-2 font-medium text-foreground"
      >
        {PERIOD_OPTIONS.map((months) => (
          <option key={months} value={months}>
            Last {months} months
          </option>
        ))}
      </select>
    </label>
  );
}
