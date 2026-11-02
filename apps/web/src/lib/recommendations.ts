"use client";

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Recommendation = components["schemas"]["RecommendationResponse"];

export function useRecommendations() {
  return useQuery({
    queryKey: ["analytics", "recommendations"],
    queryFn: () => apiRequest<Recommendation[]>("/recommendations"),
  });
}
