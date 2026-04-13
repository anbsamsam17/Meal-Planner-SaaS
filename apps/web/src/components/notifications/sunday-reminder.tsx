"use client";
// apps/web/src/components/notifications/sunday-reminder.tsx
// Banner conditionnelle — affichée le dimanche soir (18h-22h) si pas de plan semaine suivante
// Dismissable via localStorage — ne réapparaît pas si déjà vu ce dimanche
// Phase 2

import { useState, useEffect } from "react";
import Link from "next/link";
import { X, Calendar } from "lucide-react";

const STORAGE_KEY = "sunday_reminder_dismissed_week";

function getCurrentWeekKey(): string {
  const now = new Date();
  // Clé unique par semaine : YYYY-WW
  const startOfYear = new Date(now.getFullYear(), 0, 1);
  const weekNumber = Math.ceil(
    ((now.getTime() - startOfYear.getTime()) / 86400000 + startOfYear.getDay() + 1) / 7,
  );
  return `${now.getFullYear()}-W${weekNumber}`;
}

function isSundayEvening(): boolean {
  const now = new Date();
  const isSunday = now.getDay() === 0; // 0 = dimanche
  const hour = now.getHours();
  return isSunday && hour >= 18 && hour < 22;
}

interface SundayReminderProps {
  // True si le plan de la semaine suivante est déjà généré — ne pas afficher si oui
  hasPlanForNextWeek?: boolean;
}

export function SundayReminder({ hasPlanForNextWeek = false }: SundayReminderProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Ne pas afficher si on n'est pas dimanche soir ou s'il y a déjà un plan
    if (!isSundayEvening() || hasPlanForNextWeek) return;

    // Ne pas afficher si déjà dismissed cette semaine
    try {
      const dismissed = localStorage.getItem(STORAGE_KEY);
      if (dismissed === getCurrentWeekKey()) return;
    } catch {
      // localStorage indisponible (SSR, navigation privée)
    }

    setVisible(true);
  }, [hasPlanForNextWeek]);

  function handleDismiss() {
    try {
      localStorage.setItem(STORAGE_KEY, getCurrentWeekKey());
    } catch {
      // Silencieux si localStorage indisponible
    }
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-between gap-3 rounded-xl border border-primary-200 bg-primary-50 px-4 py-3"
    >
      {/* Icône */}
      <div className="flex-shrink-0">
        <Calendar className="h-5 w-5 text-primary-600" aria-hidden />
      </div>

      {/* Message */}
      <p className="flex-1 text-sm text-primary-800">
        <span className="font-semibold">Votre semaine commence demain !</span>{" "}
        Générez votre plan en 30 secondes.
      </p>

      {/* CTA */}
      <Link
        href="/dashboard"
        className="flex-shrink-0 rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1"
      >
        Générer ma semaine
      </Link>

      {/* Dismiss */}
      <button
        type="button"
        onClick={handleDismiss}
        className="flex-shrink-0 rounded-lg p-1 text-primary-400 transition-colors hover:text-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
        aria-label="Fermer ce rappel"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
