"use client";

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Overview = components["schemas"]["OverviewResponse"];
export type ServiceComparison = components["schemas"]["ServiceComparisonResponse"];
export type UnusualCost = components["schemas"]["UnusualCostResponse"];
export type CostType = "billed" | "effective";

export type Filters = {
  months: number;
  costType?: CostType;
  currency?: string;
  provider?: string;
};

export const PERIOD_OPTIONS = [3, 6, 12, 24];

function query(filters: Filters, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams({ months: String(filters.months), ...extra });
  if (filters.costType) params.set("cost_type", filters.costType);
  if (filters.currency) params.set("currency", filters.currency);
  if (filters.provider) params.set("provider", filters.provider);
  return params.toString();
}

export function useOverview(filters: Filters) {
  return useQuery({
    queryKey: ["analytics", "overview", filters],
    queryFn: () => apiRequest<Overview | null>(`/analytics/overview?${query(filters)}`),
  });
}

export function useUnusualCosts(filters: Filters) {
  return useQuery({
    queryKey: ["analytics", "unusual", filters],
    queryFn: () => apiRequest<UnusualCost[]>(`/analytics/unusual?${query(filters)}`),
  });
}

export function useComparison(filters: Filters, first?: string, second?: string) {
  return useQuery({
    queryKey: ["analytics", "compare", filters, first, second],
    enabled: Boolean(first && second),
    queryFn: () =>
      apiRequest<ServiceComparison[]>(
        `/analytics/compare?${query(filters, { first: first ?? "", second: second ?? "" })}`,
      ),
  });
}
