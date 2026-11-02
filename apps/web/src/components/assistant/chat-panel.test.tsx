import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/components/assistant/chat-panel";

const INFO = { suggestions: ["Summarize my cloud spending"], is_free_tier: true };
const CHAT = { id: "1", title: "Chat", created_at: "2026-10-31T10:00:00Z" };

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

/** Sends events, then stays open, so the page is seen while the answer is still arriving. */
function openEventStream(...events: object[]) {
  const text = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("");
  const body = new ReadableStream({
    start: (controller) => controller.enqueue(new TextEncoder().encode(text)),
  });
  return new Response(body, { status: 200 });
}

function renderPanel(handleAsk: () => Response, messages: unknown[] = []) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/info")) return json(INFO);
      if (url.endsWith("/conversations")) return init?.method === "POST" ? json(CHAT) : json([CHAT]);
      return init?.method === "POST" ? handleAsk() : json(messages);
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ChatPanel />
    </QueryClientProvider>,
  );
}

describe("ChatPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the free key notice and suggestions", async () => {
    renderPanel(() => json({}));

    expect(await screen.findByText(/free Gemini key/)).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Summarize my cloud spending" }),
    ).toBeInTheDocument();
  });

  it("shows an answer as it streams in", async () => {
    renderPanel(() =>
      openEventStream(
        { type: "status", text: "Writing your answer", sources: [] },
        { type: "text", text: "You spent ", sources: [] },
        { type: "text", text: "248.60 USD.", sources: [] },
      ),
    );

    fireEvent.click(await screen.findByRole("button", { name: "Summarize my cloud spending" }));

    expect(await screen.findByText("You spent 248.60 USD.")).toBeInTheDocument();
    expect(screen.getByText("Summarize my cloud spending")).toBeInTheDocument();
  });

  it("shows saved messages with their sources", async () => {
    renderPanel(
      () => json({}),
      [
        { id: "1", role: "user", content: "How can I save?", created_at: "", sources: [] },
        {
          id: "2",
          role: "assistant",
          content: "Use lifecycle rules.",
          created_at: "",
          sources: [{ title: "S3 lifecycle", url: "https://docs.test/s3" }],
          grade: "A",
          trace: {
            routes: ["optimization"],
            facts: [{ label: "Total", value: "10.00 USD" }],
            checks: { answer_attempts: 1, used_template: false },
            metrics: { ai_calls: 2, total_ms: 1500 },
          },
        },
      ],
    );

    expect(await screen.findByText("Use lifecycle rules.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "S3 lifecycle" })).toHaveAttribute(
      "href",
      "https://docs.test/s3",
    );
    expect(screen.getByText("Evidence grade A: Full evidence")).toBeInTheDocument();
    expect(screen.getByText("Total: 10.00 USD")).toBeInTheDocument();
    expect(screen.getByText("2 AI calls in 1.5 seconds")).toBeInTheDocument();
  });

  it("keeps the question and explains when the daily limit is reached", async () => {
    renderPanel(() =>
      json({ error: { code: "daily_limit_reached", message: "Today's limit is reached." } }, 429),
    );
    const input = await screen.findByLabelText("Ask about your cloud costs");

    fireEvent.change(input, { target: { value: "How much?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Today's limit is reached.")).toBeInTheDocument();
    expect(input).toHaveValue("How much?");
  });
});
