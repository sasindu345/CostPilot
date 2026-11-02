import { describe, expect, it } from "vitest";

import {
  formatFileSize,
  formatMoney,
  formatMonth,
  formatMonthRange,
  formatPercent,
  providerName,
} from "@/lib/format";

describe("formatFileSize", () => {
  it.each([
    [512, "512 B"],
    [2048, "2.0 KB"],
    [13002342, "12.4 MB"],
    [5368709120, "5.0 GB"],
  ])("shows %d bytes as %s", (bytes, expected) => {
    expect(formatFileSize(bytes)).toBe(expected);
  });
});

describe("formatMonthRange", () => {
  it("shows one month once", () => {
    expect(formatMonthRange("2026-10-01", "2026-10-01")).toBe("Oct 2026");
  });

  it("shows a range of months", () => {
    expect(formatMonthRange("2026-05-01", "2026-10-01")).toBe("May 2026 to Oct 2026");
  });

  it("explains when a file has not been read", () => {
    expect(formatMonthRange(null, null)).toBe("Not read yet");
  });
});

describe("providerName", () => {
  it("uses the full name", () => {
    expect(providerName("aws")).toBe("AWS");
  });

  it("shows an unknown provider as it is", () => {
    expect(providerName("ibm")).toBe("ibm");
  });
});

describe("money and percent", () => {
  it("shows the amount in its own currency", () => {
    expect(formatMoney("1245.60", "USD")).toBe("$1,245.60");
    expect(formatMoney("10", "EUR")).toBe("€10.00");
  });

  it("shows a percent without its sign", () => {
    expect(formatPercent("-8.1")).toBe("8.1%");
  });

  it("shows a month in UTC, so time zones cannot move it", () => {
    expect(formatMonth("2026-10-01")).toBe("Oct 2026");
  });
});
