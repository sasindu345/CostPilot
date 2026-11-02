import {
  BarChart3,
  FileText,
  Home,
  MessageSquare,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type NavigationItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export const mainNavigation: NavigationItem[] = [
  { label: "Overview", href: "/", icon: Home },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "AI Assistant", href: "/assistant", icon: MessageSquare },
];

export const settingsNavigation: NavigationItem = {
  label: "Settings",
  href: "/settings",
  icon: Settings,
};
