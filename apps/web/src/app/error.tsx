// apps/web/src/app/error.tsx
// Error boundary global — doit être un Client Component (Next.js)
// Design warm — pas d'écran d'erreur froid et alarmiste
"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log l'erreur vers Sentry en production
    // TODO Phase 1 : intégrer Sentry.captureException(error)
    console.error("Erreur application:", error);
  }, [error]);

  return (
    <main
      id="main-content"
      className="flex min-h-dvh flex-col items-center justify-center bg-neutral-50 px-6 text-center"
    >
      <div
        className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-warning-100"
        aria-hidden="true"
      >
        <AlertTriangle className="h-8 w-8 text-warning-500" />
      </div>

      <h1 className="font-serif mb-3 text-3xl font-bold text-neutral-900">
        Quelque chose s&apos;est mal passé
      </h1>
      <p className="mb-8 max-w-sm text-base text-neutral-500">
        Une erreur inattendue s&apos;est produite. Ne vous inquiétez pas — vos données sont
        sauvegardées.
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={reset}
          className="inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-primary-500 px-6 py-3 font-semibold text-primary-foreground transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          Réessayer
        </button>
        <a
          href="/"
          className="inline-flex min-h-[48px] items-center gap-2 rounded-xl border border-neutral-200 bg-white px-6 py-3 font-semibold text-neutral-700 transition-all hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          Retour à l&apos;accueil
        </a>
      </div>

      {/* Digest de l'erreur pour le support — visible uniquement en dev */}
      {process.env.NODE_ENV === "development" && error.digest && (
        <p className="mt-6 rounded-lg bg-neutral-100 px-4 py-2 font-mono text-xs text-neutral-500">
          Digest: {error.digest}
        </p>
      )}
    </main>
  );
}
