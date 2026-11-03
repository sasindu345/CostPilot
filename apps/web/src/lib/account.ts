"use client";

import { useMutation } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/lib/api";
import type { components } from "@/lib/api-types";
import { LOGIN_PATH } from "@/lib/current-user";

type DeleteAccountRequest = components["schemas"]["DeleteAccountRequest"];

const EXPORT_FILE_NAME = "costpilot-export.json";

/** Downloads every record in the workspace as one JSON file. */
export function useExportData() {
  return useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/account/export");
      if (!response.ok) {
        throw new ApiError(response.status, "We could not prepare your data. Please try again.");
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = EXPORT_FILE_NAME;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: (body: DeleteAccountRequest) =>
      apiRequest<void>("/account", {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      }),
    // A full page load forgets everything cached about the deleted user.
    // LOGIN_PATH is an API route that redirects to Keycloak, not a Next.js page.
    onSuccess: () => window.location.assign(LOGIN_PATH),
  });
}
