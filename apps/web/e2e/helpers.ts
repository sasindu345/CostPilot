import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const MAILPIT_URL = process.env.MAILPIT_URL;
export const PASSWORD = `Test-${crypto.randomUUID()}`;

export async function emailCount(request: APIRequestContext, email: string): Promise<number> {
  const response = await request.get(`${MAILPIT_URL}/api/v1/search?query=to:${email}`);
  return (await response.json()).messages_count;
}

async function verificationLink(request: APIRequestContext, email: string): Promise<string> {
  await expect.poll(() => emailCount(request, email)).toBeGreaterThan(0);
  const search = await request.get(`${MAILPIT_URL}/api/v1/search?query=to:${email}`);
  const { messages } = await search.json();
  const message = await request.get(`${MAILPIT_URL}/api/v1/message/${messages[0].ID}`);
  const { Text: body } = await message.json();
  const link = body.match(/https?:\/\/\S+action-token\S+/)?.[0];
  expect(link).toBeTruthy();
  return link;
}

/** Registers a brand new user and leaves them signed in on the Overview page. */
export async function signUp(page: Page, request: APIRequestContext): Promise<string> {
  const email = `user-${crypto.randomUUID()}@example.test`;
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await page.getByRole("link", { name: "Register" }).click();
  await page.locator("#email").fill(email);
  await page.locator("#firstName").fill("Ann");
  await page.locator("#lastName").fill("Lee");
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByText(/verify your email/i).first()).toBeVisible();

  await page.goto(await verificationLink(request, email));
  await page.locator("#password-new").fill(PASSWORD);
  await page.locator("#password-confirm").fill(PASSWORD);
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("heading", { name: "Welcome to CostPilot" })).toBeVisible();
  return email;
}
