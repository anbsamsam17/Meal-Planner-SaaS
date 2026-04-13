// apps/web/src/app/(app)/error.tsx
// FIX Phase 1 (review 2026-04-12) : error boundary manquant dans (app) — FIX #7 / L5
// Client Component requis par Next.js pour les error boundaries
// Ton warm et rassurant — données de l'utilisateur toujours sauvegardées
"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface AppErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function AppError({ error, reset }: AppErrorProps) {
  useEffect(() => {
    // TODO Phase 2 : Sentry.captureException(error) + context user/tenant
    console.error("[App] Erreur inattendue:", error);
  }, [error]);

  return (
    <main
      id="main-content"
      className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center"
    >
      {/* Icône warning warm — pas d'icône rouge alarmiste */}
      <div
        className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-warning-100"
        aria-hidden="true"
      >
        <AlertTriangle className="h-8 w-8 text-warning-500" />
      </div>

      {/* Titre Fraunces */}
      <h1 className="font-serif mb-3 text-2xl font-bold text-neutral-900">
        Quelque chose s&apos;est mal passé
      </h1>
      <p className="mb-8 max-w-sm text-sm text-neutral-500">
        Une erreur inattendue s&apos;est produite sur cette page.
        Vos données et votre planning sont en sécurité.
      </p>

      {/* Actions */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={reset}
          className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-primary-500 px-6 py-3 font-semibold text-primary-foreground transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Réessayer
        </button>
        <a
          href="/dashboard"
          className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-6 py-3 font-semibold text-neutral-700 transition-all hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          Retour au tableau de bord
        </a>
      </div>

      {/* Digest visible uniquement en développement */}
      {process.env.NODE_ENV === "development" && error.digest && (
        <p className="mt-6 rounded-lg bg-neutral-100 px-4 py-2 font-mono text-xs text-neutral-400">
          Digest: {error.digest}
        </p>
      )}
    </main>
  );
}
