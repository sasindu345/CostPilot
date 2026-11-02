import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL,
    channel: process.env.E2E_BROWSER_CHANNEL,
    trace: "retain-on-failure",
  },
});
