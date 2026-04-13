// apps/web/src/app/loading.tsx
// État de chargement global — affiché par Next.js pendant les suspense boundaries
// Design warm avec shimmer animation (voir globals.css .skeleton-shimmer)
export default function LoadingPage() {
  return (
    <div
      className="flex min-h-dvh flex-col bg-neutral-50 px-4 py-6"
      role="status"
      aria-busy="true"
      aria-label="Chargement en cours..."
    >
      {/* Skeleton header */}
      <div className="mb-6 flex items-center gap-4">
        <div className="skeleton-shimmer h-10 w-48 rounded-xl" aria-hidden="true" />
        <div className="skeleton-shimmer h-6 w-32 rounded-full" aria-hidden="true" />
      </div>

      {/* Skeleton grille de cards recettes */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="overflow-hidden rounded-2xl border border-neutral-200"
            aria-hidden="true"
          >
            {/* Image placeholder */}
            <div className="skeleton-shimmer aspect-video w-full" />
            {/* Texte placeholder */}
            <div className="p-4">
              <div className="skeleton-shimmer mb-2 h-5 w-3/4 rounded-lg" />
              <div className="skeleton-shimmer h-4 w-1/2 rounded-lg" />
            </div>
          </div>
        ))}
      </div>

      {/* Texte accessible caché visuellement */}
      <span className="sr-only">Chargement du contenu en cours, veuillez patienter.</span>
    </div>
  );
}
