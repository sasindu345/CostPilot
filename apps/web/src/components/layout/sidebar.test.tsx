import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Sidebar } from "@/components/layout/sidebar";

vi.mock("next/navigation", () => ({ usePathname: () => "/documents" }));

describe("Sidebar", () => {
  it("shows every main section", () => {
    render(<Sidebar />);

    for (const name of ["Overview", "Documents", "Analytics", "AI Assistant", "Settings"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("marks only the current page as active", () => {
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "Documents" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
  });
});
