// apps/web/src/components/navigation/app-bottom-nav.tsx
// Bottom Nav mobile — 6 items Phase 2, 64px de hauteur
// Référence : 04-components-catalog.md #17 BottomNav
// Référence : 07-responsive-breakpoints.md
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ShoppingCart, User, Refrigerator, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

// BUG 1 FIX : "Planning" remplacé par "Accueil" avec icône Home — même route /dashboard
//   mais label cohérent avec la sidebar. CalendarDays supprimé (import inutile).
// BUG 4 FIX : max 5 items, tous les href vérifiés contre les routes existantes
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
    label: "Frigo",
    icon: Refrigerator,
    matchPaths: ["/fridge"],
  },
  {
    href: "/shopping-list",
    label: "Courses",
    icon: ShoppingCart,
    matchPaths: ["/shopping-list"],
    // Badge count — sera connecté à l'état de la liste en Phase 2 (Supabase Realtime)
    badgeCount: 0,
  },
  {
    href: "/account",
    label: "Profil",
    icon: User,
    matchPaths: ["/account", "/settings"],
  },
] as const;

export function AppBottomNav() {
  const pathname = usePathname();

  return (
    <div className="flex h-16 items-stretch px-2">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = item.matchPaths.some((path) => pathname.startsWith(path));
        const badgeCount = "badgeCount" in item ? item.badgeCount : 0;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "relative flex flex-1 flex-col items-center justify-center gap-0.5",
              "min-h-[44px] min-w-[44px] rounded-lg transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
              isActive
                ? "text-primary-600"
                : "text-neutral-400 hover:text-neutral-700",
            )}
            aria-current={isActive ? "page" : undefined}
            aria-label={item.label}
          >
            {/* Badge count */}
            {badgeCount > 0 && (
              <span
                className="absolute right-2 top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-neutral-900 px-1 text-2xs font-semibold text-neutral-50"
                aria-label={`${badgeCount} articles dans la liste`}
              >
                {badgeCount > 99 ? "99+" : badgeCount}
              </span>
            )}

            <Icon
              className={cn("h-6 w-6", isActive ? "text-primary-600" : "text-neutral-400")}
              strokeWidth={1.5}
              aria-hidden="true"
            />

            {/* Label visible uniquement sur l'item actif */}
            {isActive && (
              <span className="text-2xs font-semibold text-primary-600">
                {item.label}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}
