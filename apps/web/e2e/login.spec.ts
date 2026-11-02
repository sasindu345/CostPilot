import { expect, test } from "@playwright/test";

import { emailCount, PASSWORD, signUp } from "./helpers";

test("a new user can sign up, verify their email, sign out and sign in again", async ({
  page,
  request,
}) => {
  const email = await test.step("a new user registers, verifies and enters the app", () =>
    signUp(page, request),
  );
  await expect(page.getByRole("button", { name: /Ann Lee/ })).toBeVisible();

  await test.step("Settings shows their account", async () => {
    await page.goto("/settings");
    await expect(page.getByText(email)).toBeVisible();
    await expect(page.getByText("My workspace")).toBeVisible();
  });

  await test.step("the session cookie is hidden from page scripts", async () => {
    const cookies = await page.context().cookies();
    const session = cookies.find((cookie) => cookie.name === "costpilot_session");
    expect(session?.httpOnly).toBe(true);
    expect(session?.sameSite).toBe("Lax");
    expect(await page.evaluate(() => document.cookie)).not.toContain("costpilot_session");
  });

  await test.step("signing out ends the session", async () => {
    await page.getByRole("button", { name: /Ann Lee/ }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    expect((await page.request.get("/api/me")).status()).toBe(401);
  });

  await test.step("they can sign in again", async () => {
    await page.locator("#username").fill(email);
    await page.locator("#password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByRole("heading", { name: "Welcome to CostPilot" })).toBeVisible();
  });

  await test.step("they can ask for a password reset email", async () => {
    await page.getByRole("button", { name: /Ann Lee/ }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await page.getByRole("link", { name: "Forgot Password?" }).click();
    await page.locator("#username").fill(email);
    await page.getByRole("button", { name: "Submit" }).click();
    await expect.poll(() => emailCount(request, email)).toBe(2);
  });
});
