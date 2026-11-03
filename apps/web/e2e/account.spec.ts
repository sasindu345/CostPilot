import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import { PASSWORD, signUp } from "./helpers";

test("a user can download all their data, then delete their account", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  const email = await signUp(page, request);
  const api = page.request;

  await test.step("add the sample bill", async () => {
    const { id } = await (await api.post("/api/documents/sample")).json();
    await expect
      .poll(async () => (await (await api.get(`/api/documents/${id}`)).json()).status)
      .toBe("processed");
  });

  await test.step("Download my data gives one JSON file with exact money", async () => {
    await page.goto("/settings");
    const downloading = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download my data" }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).toBe("costpilot-export.json");

    const text = await readFile((await download.path())!, "utf8");
    const data = JSON.parse(text);
    expect(data.user.email).toBe(email);
    expect(data.documents).toHaveLength(1);
    expect(data.documents[0]).not.toHaveProperty("storage_key");
    expect(data.cost_records.length).toBeGreaterThan(0);
    expect(data.audit_events.map((event: { action: string }) => event.action)).toContain(
      "account.exported",
    );
  });

  await test.step("a wrong email is refused", async () => {
    const response = await api.delete("/api/account", {
      data: { confirm_email: "someone@example.test" },
    });
    expect(response.status()).toBe(400);
    expect((await response.json()).error.code).toBe("deletion_not_confirmed");
  });

  await test.step("Delete my account ends at the sign-in page", async () => {
    await page.getByLabel("Type your email address to confirm").fill(email);
    await page.getByRole("button", { name: "Delete my account" }).click();
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    expect((await page.request.get("/api/me")).status()).toBe(401);
  });

  await test.step("the login is gone from Keycloak too", async () => {
    await page.locator("#username").fill(email);
    await page.locator("#password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByText(/invalid username or password/i)).toBeVisible();
  });
});
