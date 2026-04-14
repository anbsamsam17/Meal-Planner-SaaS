"use client";
// apps/web/src/app/(app)/dashboard/dashboard-shell.tsx
// Wrapper Client Component — fournit WeekOffsetContext à WeekNavigator et DashboardContent
// Le Server Component DashboardPage délègue ici pour éviter de passer weekOffset en prop drilling

import { WeekOffsetProvider } from "@/components/dashboard/week-offset-context";
import { WeekNavigator } from "@/components/dashboard/week-navigator";
import { DashboardContent } from "./dashboard-content";
import type { PlanDetail } from "@/lib/api/endpoints";

interface DashboardShellProps {
  firstName: string | null;
  initialPlanData: PlanDetail | null;
}

export function DashboardShell({ firstName, initialPlanData }: DashboardShellProps) {
  return (
    <WeekOffsetProvider>
      <div className="min-h-full bg-[#fff8f6] px-4 py-6 md:px-6 lg:px-10">
        {/* Header de la page */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            {firstName && (
              <p className="mb-0.5 text-sm font-medium text-primary-600">
                Bonjour {firstName} !
              </p>
            )}
            <h1 className="font-serif text-3xl font-bold text-neutral-900 dark:text-neutral-100 md:text-4xl">
              Ma semaine
            </h1>
          </div>

          {/* Navigation semaine — lit et écrit weekOffset via WeekOffsetContext */}
          <WeekNavigator />
        </div>

        {/* Contenu du dashboard — lit weekOffset via WeekOffsetContext pour fetcher le bon plan */}
        <DashboardContent initialPlanData={initialPlanData} />
      </div>
    </WeekOffsetProvider>
  );
}
