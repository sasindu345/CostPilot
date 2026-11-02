import { Bell } from "lucide-react";

import { UserMenu } from "@/components/layout/user-menu";

export function TopBar() {
  return (
    <header className="flex items-center justify-end gap-4 border-b border-border bg-surface px-8 py-3">
      <button type="button" aria-label="Notifications" className="rounded-control p-2">
        <Bell aria-hidden className="size-6" />
      </button>
      <UserMenu />
    </header>
  );
}
