"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";

export const LOGIN_PATH = "/api/auth/login";

export type CurrentUser = {
  user_id: string;
  email: string;
  display_name: string;
  workspace_id: string;
  workspace_name: string;
  role: string;
  account_url: string;
};

export function useCurrentUser() {
  return useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiRequest<CurrentUser>("/me"),
    retry: false,
  });
}

export function useSignOut() {
  return useMutation({
    mutationFn: () =>
      apiRequest<{ logout_url: string }>("/auth/logout", { method: "POST" }),
    onSuccess: ({ logout_url }) => window.location.assign(logout_url),
  });
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : parts[0].slice(0, 2);
  return letters.toUpperCase();
}
