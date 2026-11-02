import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthGate } from "@/components/layout/auth-gate";

function renderGate() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AuthGate>
        <p>Private page</p>
      </AuthGate>
    </QueryClientProvider>,
  );
}

function mockApi(status: number, body: unknown = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

describe("AuthGate", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the page to a signed-in user", async () => {
    mockApi(200, { display_name: "Ann" });
    renderGate();

    expect(await screen.findByText("Private page")).toBeInTheDocument();
  });

  it("sends a signed-out user to the login page", async () => {
    mockApi(401);
    const assign = vi.fn();
    vi.stubGlobal("location", { assign });
    renderGate();

    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith("/api/auth/login"));
    expect(screen.queryByText("Private page")).not.toBeInTheDocument();
  });

  it("offers a retry when the server has a problem", async () => {
    mockApi(500);
    renderGate();

    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.queryByText("Private page")).not.toBeInTheDocument();
  });
});
