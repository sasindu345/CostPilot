import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./settings-page";

const assign = vi.fn();

const USER = {
  user_id: "1",
  email: "owner@example.test",
  display_name: "Owner",
  workspace_id: "2",
  workspace_name: "My workspace",
  role: "owner",
  account_url: "/account",
  max_upload_mb: 100,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <SettingsPage />
    </QueryClientProvider>,
  );
}

const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
  if (url === "/api/account" && init?.method === "DELETE") {
    return new Response(null, { status: 204 });
  }
  return new Response(JSON.stringify(USER), { status: 200 });
});

describe("SettingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockClear();
  });

  it("only allows deletion once the email is typed exactly", async () => {
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    const button = await screen.findByRole("button", { name: "Delete my account" });
    expect(button).toBeDisabled();

    const input = screen.getByLabelText("Type your email address to confirm");
    fireEvent.change(input, { target: { value: "someone@else.test" } });
    expect(button).toBeDisabled();

    fireEvent.change(input, { target: { value: "Owner@Example.test" } });
    expect(button).toBeEnabled();
  });

  it("sends the typed email and leaves the app after deleting", async () => {
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("location", { ...window.location, assign });
    renderPage();

    fireEvent.change(await screen.findByLabelText("Type your email address to confirm"), {
      target: { value: USER.email },
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete my account" }));

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/api/auth/login"));
    const [, init] = fetchMock.mock.calls.find(([url]) => url === "/api/account")!;
    expect(JSON.parse(init!.body as string)).toEqual({ confirm_email: USER.email });
  });
});
