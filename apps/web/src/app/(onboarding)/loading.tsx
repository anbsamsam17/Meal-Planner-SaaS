// apps/web/src/app/(onboarding)/loading.tsx
// FIX Phase 1 (review 2026-04-12) : loading boundary manquant dans (onboarding) — FIX #7 / L5
// Affiché par Next.js pendant la navigation entre étapes onboarding
// Design warm cohérent avec le funnel d'inscription (palette terracotta/cream)
export default function OnboardingLoading() {
  return (
    <div
      className="flex flex-1 flex-col items-center justify-center px-6 py-12"
      role="status"
      aria-busy="true"
      aria-label="Chargement de l'étape en cours..."
    >
      {/* Spinner warm terracotta */}
      <div className="mb-6 flex h-16 w-16 items-center justify-center">
        <svg
          className="h-10 w-10 animate-spin text-primary-500"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </div>

      {/* Texte Fraunces — ton éditorial warm */}
      <p className="font-serif text-xl font-semibold text-neutral-800">
        Préparation de votre étape...
      </p>
      <p className="mt-2 text-sm text-neutral-500">
        Cela ne prendra qu&apos;un instant.
      </p>

      {/* Texte accessible pour les lecteurs d'écran */}
      <span className="sr-only">Chargement de l&apos;étape d&apos;inscription, veuillez patienter.</span>
    </div>
  );
}
