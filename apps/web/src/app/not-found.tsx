// apps/web/src/app/not-found.tsx
// Page 404 — design warm, pas d'écran d'erreur froide
import type { Metadata } from "next";
import Link from "next/link";
import { Home, Search } from "lucide-react";

export const metadata: Metadata = {
  title: "Page introuvable — Presto",
};

export default function NotFoundPage() {
  return (
    <main
      id="main-content"
      className="flex min-h-dvh flex-col items-center justify-center bg-neutral-50 px-6 text-center"
    >
      {/* Illustration émojis culinaires */}
      <div className="mb-6 text-6xl" aria-hidden="true">
        🍽️
      </div>

      <h1 className="font-serif mb-3 text-4xl font-bold text-neutral-900">
        Cette page n&apos;existe pas
      </h1>
      <p className="mb-8 max-w-sm text-base text-neutral-500">
        Il semble que vous cherchiez une recette qui n&apos;est pas dans notre base. Revenez à
        l&apos;accueil pour continuer.
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/"
          className="inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-primary-500 px-6 py-3 font-semibold text-primary-foreground transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          <Home className="h-4 w-4" aria-hidden="true" />
          Retour à l&apos;accueil
        </Link>
        <Link
          href="/dashboard"
          className="inline-flex min-h-[48px] items-center gap-2 rounded-xl border border-neutral-200 bg-white px-6 py-3 font-semibold text-neutral-700 transition-all hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          Mon dashboard
        </Link>
      </div>
    </main>
  );
}
