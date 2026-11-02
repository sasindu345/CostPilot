import type { Overview } from "@/lib/analytics";
import { formatMoney } from "@/lib/format";

export function TopServices({ overview }: { overview: Overview }) {
  return (
    <ul className="grid gap-4">
      {overview.top_services.map((service) => (
        <li key={service.name}>
          <div className="flex justify-between gap-3">
            <span className="truncate font-medium">{service.name}</span>
            <span className="font-semibold">{formatMoney(service.cost, overview.currency)}</span>
          </div>
          <div className="mt-1 flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-chart-track">
              <div
                className="h-full rounded-full bg-chart-line"
                style={{ width: `${Number(service.share_percent)}%` }}
              />
            </div>
            <span className="w-14 text-right text-sm text-muted">{service.share_percent}%</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
