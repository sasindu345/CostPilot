import { expect, test } from "@playwright/test";

import { signUp } from "./helpers";

test("the assistant answers with real numbers, and a chat stays private", async ({
  browser,
  page,
  request,
}) => {
  test.setTimeout(150_000);
  await signUp(page, request);
  await page.getByRole("button", { name: "Try sample data" }).click();
  await expect(page.getByText("$1,245.60")).toBeVisible({ timeout: 20_000 });

  await test.step("a free key shows a notice, and the suggestions appear", async () => {
    await page.goto("/assistant");
    await expect(page.getByText(/free Gemini key/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Summarize my cloud spending" })).toBeVisible();
  });

  await test.step("the answer uses the true figure from the bill", async () => {
    await page.getByRole("button", { name: "Summarize my cloud spending" }).click();
    await expect(page.getByText(/248\.60 USD|1,245\.60 USD/).first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByText("{{F")).toHaveCount(0);
  });

  await test.step("the chat is saved", async () => {
    await page.reload();
    await expect(page.getByText("Summarize my cloud spending")).toBeVisible();
    await expect(page.getByText(/248\.60 USD|1,245\.60 USD/).first()).toBeVisible();
  });

  await test.step("another user cannot read it", async () => {
    const [{ id }] = await (await page.request.get("/api/assistant/conversations")).json();
    const other = await browser.newContext({ baseURL: process.env.E2E_BASE_URL });
    const otherPage = await other.newPage();
    await signUp(otherPage, request);
    const response = await otherPage.request.get(`/api/assistant/conversations/${id}/messages`);
    expect(response.status()).toBe(404);
    await other.close();
  });
});
