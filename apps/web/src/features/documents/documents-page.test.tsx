import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentsPage } from "./documents-page";

const DOCUMENT = {
  id: "1",
  file_name: "AWS-October.csv",
  size_bytes: 2048,
  status: "failed",
  created_at: "2026-10-31T10:00:00Z",
  error_message: "This file has no data rows.",
  row_count: null,
  processed_at: null,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <DocumentsPage />
    </QueryClientProvider>,
  );
}

function mockApi(handler: (url: string, init?: RequestInit) => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => handler(url, init)),
  );
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

describe("DocumentsPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("explains what to do when there are no documents", async () => {
    mockApi(() => json([]));
    renderPage();

    expect(await screen.findByText("No documents yet")).toBeInTheDocument();
  });

  it("shows a document's status and failure reason", async () => {
    mockApi(() => json([DOCUMENT]));
    renderPage();

    expect(await screen.findByText("AWS-October.csv")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("This file has no data rows.")).toBeInTheDocument();
  });

  it("asks for confirmation before deleting", async () => {
    const fetchCalls: string[] = [];
    mockApi((url, init) => {
      fetchCalls.push(`${init?.method ?? "GET"} ${url}`);
      return init?.method === "DELETE" ? new Response(null, { status: 204 }) : json([DOCUMENT]);
    });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /Details for/ }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(fetchCalls).not.toContain("DELETE /api/documents/1");

    fireEvent.click(screen.getByRole("button", { name: "Yes, delete it" }));
    await vi.waitFor(() => expect(fetchCalls).toContain("DELETE /api/documents/1"));
  });

  it("shows the server's message when an upload is refused", async () => {
    mockApi((_, init) =>
      init?.method === "POST"
        ? json(
            { error: { code: "duplicate_document", message: "You have already uploaded this file." } },
            409,
          )
        : json([]),
    );
    renderPage();

    const file = new File(["a,b"], "bill.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("Choose a billing file"), { target: { files: [file] } });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You have already uploaded this file.",
    );
  });

  it("offers a retry when the list cannot be loaded", async () => {
    mockApi(() => json({}, 500));
    renderPage();

    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
