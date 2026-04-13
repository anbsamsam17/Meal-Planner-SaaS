// apps/web/src/components/navigation/app-sidebar.tsx
// Sidebar desktop — 240px, fixe à gauche
// Référence : 04-components-catalog.md #18 Sidebar
// Référence : 07-responsive-breakpoints.md — visible à partir de lg (1024px)
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  ShoppingCart,
  User,
  Settings,
  BookOpen,
  Refrigerator,
  Library,
  CreditCard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/brand/logo";

// BUG 1 FIX : "Planning" supprimé — doublait "/dashboard" (même route que "Accueil")
// BUG 4 FIX : tous les href vérifiés contre les routes existantes
const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Accueil",
    icon: Home,
    matchPaths: ["/dashboard"],
  },
  {
    href: "/recipes",
    label: "Recettes",
    icon: BookOpen,
    matchPaths: ["/recipes"],
  },
  {
    href: "/fridge",
    label: "Mon frigo",
    icon: Refrigerator,
    matchPaths: ["/fridge"],
  },
  {
    href: "/books",
    label: "Livres PDF",
    icon: Library,
    matchPaths: ["/books"],
  },
  {
    href: "/shopping-list",
    label: "Mes courses",
    icon: ShoppingCart,
    matchPaths: ["/shopping-list"],
  },
  {
    href: "/billing",
    label: "Abonnement",
    icon: CreditCard,
    matchPaths: ["/billing"],
  },
] as const;

const BOTTOM_ITEMS = [
  {
    href: "/account",
    label: "Mon profil",
    icon: User,
    matchPaths: ["/account"],
  },
  {
    href: "/settings",
    label: "Paramètres",
    icon: Settings,
    matchPaths: ["/settings"],
  },
] as const;

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <nav
      className="flex h-full w-60 flex-col border-r border-neutral-200 bg-neutral-50"
      aria-label="Navigation latérale"
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-neutral-200 px-6">
        <Link
          href="/dashboard"
          className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Presto — tableau de bord"
        >
          <Logo size="sm" />
        </Link>
      </div>

      {/* Navigation principale */}
      <div className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.matchPaths.some((path) => pathname.startsWith(path));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                "transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
                isActive
                  ? "border-l-2 border-primary-500 bg-primary-100 text-primary-700 pl-[10px]"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon
                className={cn(
                  "h-5 w-5 flex-shrink-0",
                  isActive ? "text-primary-600" : "text-neutral-400",
                )}
                strokeWidth={1.5}
                aria-hidden="true"
              />
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* Navigation bas — profil et paramètres */}
      <div className="flex flex-col gap-1 border-t border-neutral-200 p-3">
        {BOTTOM_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.matchPaths.some((path) => pathname.startsWith(path));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                "transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
                isActive
                  ? "border-l-2 border-primary-500 bg-primary-100 text-primary-700 pl-[10px]"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon
                className={cn(
                  "h-5 w-5 flex-shrink-0",
                  isActive ? "text-primary-600" : "text-neutral-400",
                )}
                strokeWidth={1.5}
                aria-hidden="true"
              />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
