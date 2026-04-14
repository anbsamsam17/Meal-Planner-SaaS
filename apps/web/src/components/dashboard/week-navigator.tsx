"use client";
// apps/web/src/components/dashboard/week-navigator.tsx
// Navigation entre semaines -- Client Component
// Lit et met à jour weekOffset via WeekOffsetContext (partagé avec DashboardContent)

import { useWeekOffset } from "./week-offset-context";
import { getMondayWithOffset } from "@/lib/api/endpoints";

// Formate le lundi d'une semaine en label FR lisible
function formatWeekLabel(weekStart: string): string {
  const date = new Date(`${weekStart}T00:00:00Z`);
  return date.toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function WeekNavigator() {
  const { weekOffset, setWeekOffset } = useWeekOffset();

  const weekStart = getMondayWithOffset(weekOffset);
  const weekLabel = formatWeekLabel(weekStart);

  function handlePreviousWeek() {
    setWeekOffset(weekOffset - 1);
  }

  function handleNextWeek() {
    setWeekOffset(weekOffset + 1);
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2" aria-label="Navigation entre semaines">
        <button
          type="button"
          onClick={handlePreviousWeek}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-neutral-200
            text-neutral-600 transition-colors hover:bg-neutral-100
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            dark:border-neutral-700 dark:text-neutral-400"
          aria-label="Semaine précédente"
        >
          &larr;
        </button>
        <button
          type="button"
          onClick={handleNextWeek}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-neutral-200
            text-neutral-600 transition-colors hover:bg-neutral-100
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            dark:border-neutral-700 dark:text-neutral-400"
          aria-label="Semaine suivante"
        >
          &rarr;
        </button>
      </div>
      <p className="text-xs text-neutral-400 dark:text-neutral-500">
        Semaine du {weekLabel}
      </p>
    </div>
  );
}
