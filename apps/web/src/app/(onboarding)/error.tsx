// apps/web/src/app/(onboarding)/error.tsx
// FIX Phase 1 (review 2026-04-12) : error boundary manquant dans (onboarding) — FIX #7 / L5
// Client Component requis par Next.js pour les error boundaries
// Ton warm et rassurant — l'utilisateur ne doit pas quitter le funnel d'inscription
"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

interface OnboardingErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function OnboardingError({ error, reset }: OnboardingErrorProps) {
  useEffect(() => {
    // TODO Phase 2 : Sentry.captureException(error) + tag "funnel:onboarding"
    console.error("[Onboarding] Erreur inattendue:", error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      {/* Icône warm — warning pas error pour ne pas alarmer */}
      <div
        className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-warning-100"
        aria-hidden="true"
      >
        <AlertTriangle className="h-8 w-8 text-warning-500" />
      </div>

      {/* Titre Fraunces — ton éditorial rassurant */}
      <h1 className="font-serif mb-3 text-2xl font-bold text-neutral-900">
        Un petit problème est survenu
      </h1>
      <p className="mb-8 max-w-sm text-sm text-neutral-500">
        Ne vous inquiétez pas — votre progression est sauvegardée.
        Essayez de continuer ou revenez à l&apos;étape précédente.
      </p>

      {/* Actions */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={reset}
          className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-primary-500 px-6 py-3 font-semibold text-primary-foreground transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
        >
          Réessayer cette étape
        </button>
        <a
          href="/onboarding"
          className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white px-6 py-3 font-semibold text-neutral-700 transition-all hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          Recommencer depuis le début
        </a>
      </div>

      {/* Digest visible uniquement en développement */}
      {process.env.NODE_ENV === "development" && error.digest && (
        <p className="mt-6 rounded-lg bg-neutral-100 px-4 py-2 font-mono text-xs text-neutral-400">
          Digest: {error.digest}
        </p>
      )}
    </div>
  );
}
