// apps/web/src/app/(auth)/error.tsx
// Error Boundary pour le groupe (auth) — Next.js App Router
// "use client" est obligatoire pour les error boundaries
"use client";

import Link from "next/link";
import { useEffect } from "react";

interface AuthErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function AuthError({ error, reset }: AuthErrorProps) {
  useEffect(() => {
    // Log structuré pour Sentry/Datadog — ne jamais logger les données sensibles
    console.error("[auth-error]", {
      message: error.message,
      digest: error.digest,
    });
  }, [error]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[hsl(38,60%,97%)] px-4 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm text-center">
        {/* Icône d'erreur */}
        <div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-50"
          aria-hidden="true"
        >
          <svg
            className="h-8 w-8 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>

        <h1 className="font-serif mb-2 text-2xl font-bold text-neutral-900">
          Une erreur est survenue
        </h1>
        <p className="mb-6 text-sm text-neutral-500">
          Impossible de charger cette page. Cela peut être temporaire — réessayez dans quelques
          instants.
        </p>

        {/* Détail technique optionnel — uniquement en dev */}
        {process.env.NODE_ENV === "development" && error.message && (
          <p className="mb-6 rounded-lg bg-neutral-50 px-3 py-2 text-left font-mono text-xs text-neutral-400 break-words">
            {error.message}
          </p>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={reset}
            className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
              bg-primary-500 px-6 py-3 text-base font-semibold text-white
              transition-all duration-base
              hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500 focus-visible:ring-offset-2
              active:scale-[0.98]"
          >
            Réessayer
          </button>

          <Link
            href="/"
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl
              border border-neutral-200 bg-white px-6 py-2.5 text-sm font-medium text-neutral-700
              transition-all duration-base
              hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500 focus-visible:ring-offset-2
              active:scale-[0.98]"
          >
            Retour à l&apos;accueil
          </Link>
        </div>
      </div>
    </div>
  );
}
