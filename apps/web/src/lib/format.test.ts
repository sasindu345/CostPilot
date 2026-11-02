import { describe, expect, it } from "vitest";

import { formatFileSize } from "@/lib/format";

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
