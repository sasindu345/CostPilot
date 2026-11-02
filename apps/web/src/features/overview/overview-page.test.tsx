import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OverviewPage } from "./overview-page";

const OVERVIEW = {
  currency: "USD",
  currencies: ["USD"],
  providers: ["aws"],
  total: "1245.60",
  latest_month: "2026-10-01",
  latest_cost: "248.60",
  latest_is_partial: false,
  days_covered: null,
  previous_cost: "270.40",
  change: { percent: "-8.1", compared_days: null, previous_cost: "270.40" },
  trend: [
    { month: "2026-09-01", cost: "270.40" },
    { month: "2026-10-01", cost: "248.60" },
  ],
  top_services: [
    { name: "EC2", cost: "120.00", share_percent: "48.3" },
    { name: "Other", cost: "128.60", share_percent: "51.7" },
  ],
};

function renderWith(overview: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body = url.includes("/analytics/overview") ? overview : [];
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <OverviewPage />
    </QueryClientProvider>,
  );
}

describe("OverviewPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the corrected figures from the design", async () => {
    renderWith(OVERVIEW);

    expect(await screen.findByText("$1,245.60")).toBeInTheDocument();
    expect(screen.getAllByText("$248.60").length).toBeGreaterThan(0);
    expect(screen.getByText("8.1% lower")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("labels a month that is not finished", async () => {
    renderWith({
      ...OVERVIEW,
      latest_is_partial: true,
      days_covered: 10,
      change: { percent: "20.0", compared_days: 10, previous_cost: "100.00" },
    });

    expect(await screen.findByText("Oct 2026 so far")).toBeInTheDocument();
    expect(screen.getByText("Compared with the first 10 days of last month")).toBeInTheDocument();
    expect(screen.getByText("20.0% higher")).toBeInTheDocument();
  });

  it("never shows a percentage it cannot prove", async () => {
    renderWith({
      ...OVERVIEW,
      latest_is_partial: true,
      change: { percent: null, compared_days: null, previous_cost: "100.00" },
    });

    expect(await screen.findByText("Not available")).toBeInTheDocument();
  });

  it("invites a new user to try sample data", async () => {
    renderWith(null);

    expect(await screen.findByRole("button", { name: "Try sample data" })).toBeInTheDocument();
  });
});
