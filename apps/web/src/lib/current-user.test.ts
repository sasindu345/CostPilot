import { describe, expect, it } from "vitest";

import { initials } from "@/lib/current-user";

describe("initials", () => {
  it("uses the first and last name", () => {
    expect(initials("John Michael Smith")).toBe("JS");
  });

  it("uses the first two letters of a single name", () => {
    expect(initials("john@example.test")).toBe("JO");
  });
});
