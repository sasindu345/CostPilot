import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { signUp } from "./helpers";

const AZURE_BILL = path.join(__dirname, "../../api/tests/fixtures/billing/azure-ea.csv");

async function expectNoAccessibilityProblems(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations.map((item) => item.id)).toEqual([]);
}

test("a new user sees correct figures from sample data", async ({ page, request }) => {
  // Two bills are uploaded and processed, so this test needs more than the default time.
  test.setTimeout(120_000);
  await signUp(page, request);

  await test.step("an empty account explains what to do", async () => {
    await expect(page.getByText("No spending to show yet")).toBeVisible();
    await expectNoAccessibilityProblems(page);
  });

  await test.step("sample data fills the Overview with the right numbers", async () => {
    await page.getByRole("button", { name: "Try sample data" }).click();
    await expect(page.getByText("$1,245.60")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("8.1% lower")).toBeVisible();
    await expect(page.getByText("EC2-Instances")).toBeVisible();
    await expect(page.getByText("$120.00")).toBeVisible();
    await expect(page.getByText("Other", { exact: true })).toHaveCount(1);
    await expect(page.getByText("sample-aws-bill.csv")).toBeVisible();
    await expect(page.getByText("Review S3 storage lifecycle rules")).toBeVisible();
    await expect(page.getByText("Saving: needs usage data").first()).toBeVisible();
    await expectNoAccessibilityProblems(page);
  });

  await test.step("a bill from another cloud adds a cloud filter", async () => {
    await page.goto("/documents");
    await page.getByLabel("Choose a billing file").setInputFiles(AZURE_BILL);
    const azureRow = page.getByRole("listitem").filter({ hasText: "azure-ea.csv" });
    await expect(azureRow.getByText("Processed", { exact: true })).toBeVisible();
    await page.goto("/");
    await page.getByRole("combobox", { name: "Cloud" }).selectOption("azure");
    await expect(page.getByText("€324.30").first()).toBeVisible();
    await page.getByRole("combobox", { name: "Cloud" }).selectOption("");
    await expect(page.getByText("$1,245.60")).toBeVisible();
  });

  await test.step("the period filter changes the total", async () => {
    await page.getByRole("combobox", { name: "Period" }).selectOption("3");
    await expect(page.getByText("$719.00")).toBeVisible();
  });

  await test.step("the chart has a table view", async () => {
    await page.getByText("View as table").click();
    await expect(page.getByRole("cell", { name: "Oct 2026" })).toBeVisible();
  });

  await test.step("Analytics compares months", async () => {
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Compare Two Months" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "EC2-Instances" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "-$18.40 (13.3%)" })).toBeVisible();
    await expectNoAccessibilityProblems(page);
  });

  await test.step("it works on a phone", async () => {
    await page.setViewportSize({ width: 390, height: 800 });
    await page.getByRole("link", { name: "Documents" }).click();
    await expect(page.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await expectNoAccessibilityProblems(page);
  });
});
