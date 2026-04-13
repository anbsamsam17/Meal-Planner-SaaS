// apps/web/src/app/(app)/recipes/[id]/error.tsx
// Error Boundary Next.js 14 App Router pour la page recette
// Capte les erreurs React non rattrapées (ex: crash dans RecipeTabsClient)
"use client";

import Link from "next/link";
import { useEffect } from "react";

interface RecipeErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function RecipeError({ error, reset }: RecipeErrorProps) {
  useEffect(() => {
    // Logguer l'erreur côté client pour Sentry / Datadog
    // En production, remplacer par captureException(error)
    console.error("[RecipePage] Erreur non rattrapée :", error);
  }, [error]);

  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 p-8 text-center">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-200">
          Impossible de charger cette recette
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Une erreur inattendue s&apos;est produite. Réessaye ou reviens au planning.
        </p>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium
            text-neutral-700 transition-colors hover:border-primary-300 hover:bg-primary-50
            hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2
            focus-visible:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-800
            dark:text-neutral-300"
        >
          Réessayer
        </button>
        <Link
          href="/dashboard"
          className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white
            transition-colors hover:bg-primary-700 focus-visible:outline-none
            focus-visible:ring-2 focus-visible:ring-primary-500"
        >
          Retour au planning
        </Link>
      </div>
    </div>
  );
}
