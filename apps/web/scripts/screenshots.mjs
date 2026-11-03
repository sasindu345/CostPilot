// Takes the README screenshots from the running app. Run with `make screenshots`.
// Uses a signed-in test user with the made-up sample bill, never real data.
import { chromium } from "@playwright/test";

const [base, cookieName, cookie, outDir, grafanaUrl] = process.argv.slice(2);
const VIEWPORT = { width: 1440, height: 900 };
const QUESTION = "How did October compare with September?";

const browser = await chromium.launch({ channel: process.env.E2E_BROWSER_CHANNEL || "chrome" });

async function shoot(page, name) {
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `${outDir}/${name}.png` });
  console.log(`Saved ${name}.png`);
}

// The Keycloak sign-in page, as a visitor sees it.
const visitor = await browser.newPage({ viewport: VIEWPORT });
await visitor.goto(base);
await visitor.getByRole("heading", { name: /sign in/i }).waitFor();
await shoot(visitor, "sign-in");
await visitor.close();

const context = await browser.newContext({ viewport: VIEWPORT });
await context.addCookies([{ name: cookieName, value: cookie, url: base }]);
const page = await context.newPage();

await page.goto(base);
await page.getByText("$1,245.60").first().waitFor({ timeout: 30_000 });
await shoot(page, "overview");

await page.goto(`${base}/documents`);
await page.getByText("Processed").first().waitFor();
await shoot(page, "documents");

await page.goto(`${base}/analytics`);
await page.waitForTimeout(1500);
await shoot(page, "analytics");

await page.goto(`${base}/assistant`);
await page.getByLabel("Ask about your cloud costs").fill(QUESTION);
await page.getByRole("button", { name: "Send" }).click();
await page.getByText(/Evidence grade [A-D]/).waitFor({ timeout: 90_000 });
await page.getByText("How was this answer made?").last().click();
await shoot(page, "assistant");

await page.goto(`${base}/settings`);
await shoot(page, "settings");

if (grafanaUrl) {
  const grafana = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await grafana.goto(grafanaUrl);
  await grafana.waitForTimeout(12000);
  await shoot(grafana, "grafana");
}

await browser.close();
