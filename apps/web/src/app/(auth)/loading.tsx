// apps/web/src/app/(auth)/loading.tsx
// Skeleton de chargement pour le groupe (auth) — remplace le loading.tsx root
// Affiché pendant la navigation vers /login ou /signup
// Design cohérent avec AuthLayout : fond cream, carte blanche centrée
export default function AuthLoading() {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center bg-[hsl(38,60%,97%)] px-4 py-12"
      role="status"
      aria-busy="true"
      aria-label="Chargement de la page de connexion..."
    >
      {/* Logo placeholder */}
      <div className="mb-8 skeleton-shimmer h-10 w-28 rounded-xl" aria-hidden="true" />

      {/* Carte auth — même dimensions que AuthLayout */}
      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm">
        {/* Titre */}
        <div className="skeleton-shimmer mb-2 h-8 w-36 rounded-lg" aria-hidden="true" />
        {/* Sous-titre */}
        <div className="skeleton-shimmer mb-6 h-4 w-56 rounded-lg" aria-hidden="true" />

        {/* Label champ email */}
        <div className="skeleton-shimmer mb-1.5 h-4 w-24 rounded-lg" aria-hidden="true" />
        {/* Champ email */}
        <div className="skeleton-shimmer mb-4 h-11 w-full rounded-xl" aria-hidden="true" />

        {/* Label + lien mot de passe oublié */}
        <div className="mb-1.5 flex items-center justify-between">
          <div className="skeleton-shimmer h-4 w-24 rounded-lg" aria-hidden="true" />
          <div className="skeleton-shimmer h-3 w-28 rounded-lg" aria-hidden="true" />
        </div>
        {/* Champ mot de passe */}
        <div className="skeleton-shimmer mb-4 h-11 w-full rounded-xl" aria-hidden="true" />

        {/* Espacement */}
        <div className="mb-4" />

        {/* Bouton principal */}
        <div className="skeleton-shimmer h-12 w-full rounded-xl" aria-hidden="true" />

        {/* Lien secondaire */}
        <div className="mt-4 flex justify-center">
          <div className="skeleton-shimmer h-4 w-44 rounded-lg" aria-hidden="true" />
        </div>

        {/* Lien inscription */}
        <div className="mt-6 flex items-center justify-center gap-2">
          <div className="skeleton-shimmer h-4 w-32 rounded-lg" aria-hidden="true" />
          <div className="skeleton-shimmer h-4 w-24 rounded-lg" aria-hidden="true" />
        </div>
      </div>

      {/* Footer placeholder */}
      <div className="mt-6 flex items-center justify-center gap-1">
        <div className="skeleton-shimmer h-3 w-48 rounded-lg" aria-hidden="true" />
        <div className="skeleton-shimmer h-3 w-20 rounded-lg" aria-hidden="true" />
      </div>

      <span className="sr-only">Chargement de la page de connexion, veuillez patienter.</span>
    </div>
  );
}
