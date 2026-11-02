"use client";

import { Cloud } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { mainNavigation, settingsNavigation, type NavigationItem } from "@/lib/navigation";

function NavigationLink({ item, isActive }: { item: NavigationItem; isActive: boolean }) {
  const stateClasses = isActive
    ? "bg-linear-to-r from-sidebar-active-from to-sidebar-active-to text-sidebar-active-foreground font-semibold"
    : "text-sidebar-foreground";

  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={`flex items-center gap-3 rounded-control px-4 py-3 ${stateClasses}`}
    >
      <item.icon aria-hidden className="size-5" />
      {item.label}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-sidebar shrink-0 flex-col bg-sidebar p-5 md:flex">
      <div className="mb-8 flex items-center gap-3 px-2 text-sidebar-foreground">
        <Cloud aria-hidden className="size-9" />
        <div>
          <p className="text-xl font-bold">CostPilot</p>
          <p className="text-xs">AI FinOps Assistant</p>
        </div>
      </div>
      <nav aria-label="Main" className="flex flex-1 flex-col gap-2">
        {mainNavigation.map((item) => (
          <NavigationLink key={item.href} item={item} isActive={pathname === item.href} />
        ))}
        <div className="mt-auto">
          <NavigationLink
            item={settingsNavigation}
            isActive={pathname === settingsNavigation.href}
          />
        </div>
      </nav>
    </aside>
  );
}

export function MobileNavigation() {
  const pathname = usePathname();
  const items = [...mainNavigation, settingsNavigation];

  return (
    <nav
      aria-label="Main on small screens"
      className="fixed inset-x-0 bottom-0 z-10 flex justify-around bg-sidebar p-2 md:hidden"
    >
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-label={item.label}
          aria-current={pathname === item.href ? "page" : undefined}
          className={`rounded-control p-2 ${
            pathname === item.href
              ? "bg-sidebar-active-from text-sidebar-active-foreground"
              : "text-sidebar-foreground"
          }`}
        >
          <item.icon aria-hidden className="size-6" />
        </Link>
      ))}
    </nav>
  );
}
