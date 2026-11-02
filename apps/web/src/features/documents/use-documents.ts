"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Document = components["schemas"]["DocumentResponse"];

const DOCUMENTS_KEY = ["documents"];
const REFRESH_WHILE_WORKING_MS = 2000;

function isWorking(document: Document): boolean {
  return document.status === "queued" || document.status === "processing";
}

export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_KEY,
    queryFn: () => apiRequest<Document[]>("/documents"),
    refetchInterval: (query) =>
      query.state.data?.some(isWorking) ? REFRESH_WHILE_WORKING_MS : false,
  });
}

function useDocumentAction<Input>(action: (input: Input) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: () => client.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  });
}

export function useUploadDocument() {
  return useDocumentAction((file: File) => {
    const body = new FormData();
    body.append("file", file);
    return apiRequest<Document>("/documents", { method: "POST", body });
  });
}

export function useDeleteDocument() {
  return useDocumentAction((id: string) =>
    apiRequest<void>(`/documents/${id}`, { method: "DELETE" }),
  );
}

export function useReprocessDocument() {
  return useDocumentAction((id: string) =>
    apiRequest<Document>(`/documents/${id}/reprocess`, { method: "POST" }),
  );
}
