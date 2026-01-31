"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Navigation items configuration
 */
const navItems = [
  {
    href: "/documents",
    label: "Documents",
    icon: FileText,
  },
  {
    href: "/chat",
    label: "Chat",
    icon: MessageSquare,
  },
] as const;

/**
 * Dashboard navigation component
 * Displays main navigation links with icons and active state highlighting
 */
export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-1 items-center space-x-6 text-sm font-medium">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center space-x-2 transition-colors hover:text-foreground",
              isActive ? "text-foreground" : "text-foreground/60"
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
