import { expect, test } from "@playwright/test";

import { signUp } from "./helpers";

const GOOD_BILL = Buffer.from("Service,EC2($)\n2026-10-01,120.00\n2026-09-01,138.40\n");
const EMPTY_BILL = Buffer.from("Service,EC2($)\n");

function csvFile(name: string, buffer: Buffer) {
  return { name, mimeType: "text/csv", buffer };
}

test("a user can upload, inspect, reprocess and delete a document", async ({ page, request }) => {
  await signUp(page, request);
  await page.goto("/documents");
  await expect(page.getByText("No documents yet")).toBeVisible();
  const chooser = page.getByLabel("Choose a billing file");

  await test.step("a good bill is processed by the worker", async () => {
    await chooser.setInputFiles(csvFile("AWS-October.csv", GOOD_BILL));
    await expect(page.getByText("AWS-October.csv")).toBeVisible();
    await expect(page.getByText("Processed", { exact: true })).toBeVisible();
  });

  await test.step("the same file is refused", async () => {
    await chooser.setInputFiles(csvFile("copy.csv", GOOD_BILL));
    await expect(page.getByText("You have already uploaded this file.")).toBeVisible();
  });

  await test.step("the wrong file type is refused", async () => {
    await chooser.setInputFiles({
      name: "bill.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF"),
    });
    await expect(page.getByText("Please upload a .csv or .csv.gz file.")).toBeVisible();
  });

  await test.step("a bill with no rows fails with a clear reason", async () => {
    await chooser.setInputFiles(csvFile("empty.csv", EMPTY_BILL));
    await expect(page.getByText("This file has no data rows.")).toBeVisible();
  });

  const row = page.getByRole("listitem").filter({ hasText: "AWS-October.csv" });

  await test.step("details show the row count", async () => {
    await row.getByRole("button", { name: "Details for AWS-October.csv" }).click();
    await expect(row.getByRole("term").first()).toHaveText("Rows");
    await expect(row.getByRole("definition").first()).toHaveText("2");
  });

  await test.step("a document can be reprocessed", async () => {
    await row.getByRole("button", { name: "Reprocess" }).click();
    await expect(row.getByRole("definition").first()).toHaveText("2");
    await expect(row.getByRole("button", { name: "Reprocess" })).toBeEnabled();
  });

  await test.step("a document can be deleted after confirming", async () => {
    await row.getByRole("button", { name: "Delete" }).click();
    await row.getByRole("button", { name: "Yes, delete it" }).click();
    await expect(page.getByText("AWS-October.csv")).toBeHidden();
  });
});

test("documents are private to each user", async ({ browser, page, request }) => {
  await signUp(page, request);
  await page.goto("/documents");
  await page
    .getByLabel("Choose a billing file")
    .setInputFiles(csvFile("private.csv", GOOD_BILL));
  await expect(page.getByText("private.csv")).toBeVisible();
  const { id } = (await (await page.request.get("/api/documents")).json())[0];

  const otherContext = await browser.newContext({ baseURL: process.env.E2E_BASE_URL });
  const otherPage = await otherContext.newPage();
  await signUp(otherPage, request);
  await otherPage.goto("/documents");

  await expect(otherPage.getByText("No documents yet")).toBeVisible();
  expect((await otherPage.request.get(`/api/documents/${id}`)).status()).toBe(404);
  expect((await otherPage.request.delete(`/api/documents/${id}`)).status()).toBe(404);
  await otherContext.close();
});
