"use client";
// apps/web/src/components/dashboard/week-navigator.tsx
// Navigation entre semaines -- Client Component avec state weekOffset
// Phase 1 : affiche un toast "Semaine non disponible" si offset != 0
// Phase 2 : refetch plan pour la semaine cible

import { useState } from "react";
import { toast } from "sonner";

export function WeekNavigator() {
  const [weekOffset, setWeekOffset] = useState(0);

  function handlePreviousWeek() {
    const newOffset = weekOffset - 1;
    setWeekOffset(newOffset);
    if (newOffset !== 0) {
      toast.info("Semaine non disponible", {
        description:
          "La navigation entre semaines sera disponible dans une prochaine version.",
      });
    }
  }

  function handleNextWeek() {
    const newOffset = weekOffset + 1;
    setWeekOffset(newOffset);
    if (newOffset !== 0) {
      toast.info("Semaine non disponible", {
        description:
          "La navigation entre semaines sera disponible dans une prochaine version.",
      });
    }
  }

  return (
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
  );
}
