"use client";

import { ChevronDown, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { initials, useCurrentUser, useSignOut } from "@/lib/current-user";

export function UserMenu() {
  const { data: user } = useCurrentUser();
  const signOut = useSignOut();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  if (!user) {
    return null;
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-2 rounded-control p-1"
      >
        <span
          aria-hidden
          className="flex size-10 items-center justify-center rounded-full bg-avatar font-semibold text-brand"
        >
          {initials(user.display_name)}
        </span>
        <span className="font-medium">{user.display_name}</span>
        <ChevronDown aria-hidden className="size-4" />
      </button>
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-2 w-56 rounded-control border border-border bg-surface p-2 shadow-card"
        >
          <p className="truncate px-3 py-2 text-sm text-muted">{user.email}</p>
          <Link
            role="menuitem"
            href="/settings"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 rounded-control px-3 py-2 hover:bg-surface-subtle"
          >
            <Settings aria-hidden className="size-4" />
            Settings
          </Link>
          <button
            type="button"
            role="menuitem"
            disabled={signOut.isPending}
            onClick={() => signOut.mutate()}
            className="flex w-full items-center gap-2 rounded-control px-3 py-2 hover:bg-surface-subtle"
          >
            <LogOut aria-hidden className="size-4" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
