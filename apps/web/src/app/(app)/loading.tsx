// apps/web/src/app/(app)/loading.tsx
// FIX Phase 1 (review 2026-04-12) : loading boundary manquant dans (app) — FIX #7 / L5
// Affiché pendant la navigation entre les pages du dashboard authentifié
// Skeleton adapté à la grille de recettes — cohérent avec le layout app
export default function AppLoading() {
  return (
    <div
      className="flex flex-col px-4 py-6 md:px-6 lg:px-8"
      role="status"
      aria-busy="true"
      aria-label="Chargement du contenu..."
    >
      {/* Skeleton titre de page */}
      <div className="mb-6 flex items-center gap-4">
        <div className="skeleton-shimmer h-8 w-48 rounded-xl" aria-hidden="true" />
        <div className="skeleton-shimmer h-5 w-24 rounded-full" aria-hidden="true" />
      </div>

      {/* Skeleton barre d'actions */}
      <div className="mb-6 flex gap-3" aria-hidden="true">
        <div className="skeleton-shimmer h-10 w-32 rounded-xl" />
        <div className="skeleton-shimmer h-10 w-24 rounded-xl" />
      </div>

      {/* Skeleton grille de cards recettes — 6 placeholders */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="overflow-hidden rounded-2xl border border-neutral-200 bg-white"
            aria-hidden="true"
          >
            {/* Placeholder image */}
            <div className="skeleton-shimmer aspect-video w-full" />
            {/* Placeholder contenu */}
            <div className="p-4">
              <div className="skeleton-shimmer mb-3 h-5 w-3/4 rounded-lg" />
              <div className="skeleton-shimmer mb-2 h-4 w-1/2 rounded-lg" />
              <div className="mt-4 flex gap-2">
                <div className="skeleton-shimmer h-6 w-16 rounded-full" />
                <div className="skeleton-shimmer h-6 w-12 rounded-full" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <span className="sr-only">Chargement du contenu en cours, veuillez patienter.</span>
    </div>
  );
}
