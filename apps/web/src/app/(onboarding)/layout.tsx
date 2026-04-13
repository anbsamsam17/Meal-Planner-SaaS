// apps/web/src/app/(onboarding)/layout.tsx
// Layout onboarding — progression 3 étapes
// Référence : phase-0/ux-research/onboarding-protocol.md
// Max 90 secondes pour compléter les 3 étapes (benchmark Mealime)
import type { Metadata } from "next";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Logo } from "@/components/brand/logo";

export const metadata: Metadata = {
  title: {
    default: "Bienvenue sur Presto",
    template: "%s — Inscription Presto",
  },
};

interface OnboardingLayoutProps {
  children: React.ReactNode;
}

export default function OnboardingLayout({ children }: OnboardingLayoutProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-neutral-50">
      {/* Header onboarding minimal — logo + bouton retour */}
      <header className="safe-top flex items-center justify-between border-b border-neutral-200 px-6 py-4">
        <Link
          href="/"
          className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          aria-label="Retour à l'accueil"
        >
          <ChevronLeft className="h-5 w-5" aria-hidden="true" />
        </Link>

        {/* Logo Presto */}
        <Logo size="sm" />

        {/* Espace vide pour centrer le logo */}
        <div className="h-11 w-11" aria-hidden="true" />
      </header>

      {/* Barre de progression — 3 étapes */}
      <div className="px-6 py-4" role="progressbar" aria-label="Progression de l'inscription" aria-valuemin={0} aria-valuemax={3}>
        <div className="mx-auto flex max-w-sm items-center gap-2">
          {[1, 2, 3].map((step) => (
            <div
              key={step}
              className="h-1.5 flex-1 rounded-full bg-neutral-200"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-slow"
                style={{ width: "0%" }} // Géré dynamiquement par le composant enfant via le stepper
              />
            </div>
          ))}
        </div>
      </div>

      {/* Contenu de l'étape courante */}
      <main id="main-content" className="flex flex-1 flex-col">
        {children}
      </main>
    </div>
  );
}
