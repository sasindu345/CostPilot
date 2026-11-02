"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "@/lib/api";
import type { components } from "@/lib/api-types";

export type Conversation = components["schemas"]["ConversationResponse"];
export type ChatMessage = components["schemas"]["MessageResponse"];
export type Source = components["schemas"]["SourceResponse"];
export type AssistantInfo = components["schemas"]["AssistantInfoResponse"];

export type AnswerTrace = {
  routes?: string[];
  facts?: { label: string; value: string }[];
  limitations?: string[];
  checks?: {
    answer_attempts?: number;
    used_template?: boolean;
    blocked_by_guardrail?: boolean;
    evidence_dropped?: number;
  };
  metrics?: { ai_calls?: number; input_tokens?: number; output_tokens?: number; total_ms?: number };
};

export type ChatEvent = {
  type: "status" | "text" | "replace" | "done";
  text: string;
  sources: Source[];
};

const CONVERSATIONS_KEY = ["assistant", "conversations"];
const EVENT_SEPARATOR = "\n\n";
const DATA_PREFIX = "data: ";

export function useAssistantInfo() {
  return useQuery({
    queryKey: ["assistant", "info"],
    queryFn: () => apiRequest<AssistantInfo>("/assistant/info"),
  });
}

export function useConversations() {
  return useQuery({
    queryKey: CONVERSATIONS_KEY,
    queryFn: () => apiRequest<Conversation[]>("/assistant/conversations"),
  });
}

export function useMessages(conversationId?: string) {
  return useQuery({
    queryKey: ["assistant", "messages", conversationId],
    enabled: Boolean(conversationId),
    queryFn: () =>
      apiRequest<ChatMessage[]>(`/assistant/conversations/${conversationId}/messages`),
  });
}

export function useRefreshChat() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["assistant"] });
}

export function useStartConversation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => apiRequest<Conversation>("/assistant/conversations", { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: CONVERSATIONS_KEY }),
  });
}

/** Reads the answer as it arrives, and calls `onEvent` for each step. */
export async function askQuestion(
  conversationId: string,
  question: string,
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const response = await fetch(`/api/assistant/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      body?.error?.message ?? "Something went wrong. Please try again.",
      body?.error?.code,
    );
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      return;
    }
    buffer += value;
    const parts = buffer.split(EVENT_SEPARATOR);
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (part.startsWith(DATA_PREFIX)) {
        onEvent(JSON.parse(part.slice(DATA_PREFIX.length)) as ChatEvent);
      }
    }
  }
}
