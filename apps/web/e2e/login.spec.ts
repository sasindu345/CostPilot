import { expect, test, type APIRequestContext } from "@playwright/test";

const MAILPIT_URL = process.env.MAILPIT_URL;
const PASSWORD = `Test-${crypto.randomUUID()}`;

async function verificationLink(request: APIRequestContext, email: string): Promise<string> {
  await expect
    .poll(async () => {
      const response = await request.get(`${MAILPIT_URL}/api/v1/search?query=to:${email}`);
      return (await response.json()).messages_count;
    })
    .toBeGreaterThan(0);
  const search = await request.get(`${MAILPIT_URL}/api/v1/search?query=to:${email}`);
  const { messages } = await search.json();
  const message = await request.get(`${MAILPIT_URL}/api/v1/message/${messages[0].ID}`);
  const { Text: body } = await message.json();
  const link = body.match(/https?:\/\/\S+action-token\S+/)?.[0];
  expect(link).toBeTruthy();
  return link;
}

test("a new user can sign up, verify their email, sign out and sign in again", async ({
  page,
  request,
}) => {
  const email = `user-${crypto.randomUUID()}@example.test`;

  await test.step("the app sends a signed-out visitor to the login page", async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  });

  await test.step("the visitor registers", async () => {
    await page.getByRole("link", { name: "Register" }).click();
    await page.locator("#email").fill(email);
    await page.locator("#firstName").fill("Ann");
    await page.locator("#lastName").fill("Lee");
    await page.getByRole("button", { name: "Register" }).click();
    await expect(page.getByText(/verify your email/i).first()).toBeVisible();
  });

  await test.step("the email link lets them choose a password and enter their workspace", async () => {
    await page.goto(await verificationLink(request, email));
    await page.locator("#password-new").fill(PASSWORD);
    await page.locator("#password-confirm").fill(PASSWORD);
    await page.getByRole("button", { name: "Submit" }).click();
    await expect(page.getByRole("heading", { name: "Welcome to CostPilot" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Ann Lee/ })).toBeVisible();
  });

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
    await expect
      .poll(async () => {
        const response = await request.get(`${MAILPIT_URL}/api/v1/search?query=to:${email}`);
        return (await response.json()).messages_count;
      })
      .toBe(2);
  });
});
