// apps/web/src/app/(auth)/layout.tsx
// Layout auth — centré, fond cream warm, logo Presto, aucune navigation
// Référence : phase-0/design-system/02-design-tokens.md — cream-50 = hsl(38, 60%, 97%)
import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/brand/logo";

export const metadata: Metadata = {
  title: {
    default: "Connexion",
    template: "%s — Presto",
  },
};

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    // Fond cream warm — couleur signature du design system
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[hsl(38,60%,97%)] px-4 py-12">
      {/* Logo Presto centré — identité visuelle forte */}
      <Link
        href="/"
        className="mb-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-4"
        aria-label="Retour à l'accueil Presto"
      >
        <Logo size="lg" />
      </Link>

      {/* Carte auth — bg blanc sur fond cream */}
      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm">
        {children}
      </div>

      {/* Footer minimaliste */}
      <p className="mt-6 text-center text-xs text-neutral-400">
        En continuant, vous acceptez nos{" "}
        <Link href="/legal/terms" className="underline hover:text-neutral-600">
          Conditions d&apos;utilisation
        </Link>{" "}
        et notre{" "}
        <Link href="/legal/privacy" className="underline hover:text-neutral-600">
          Politique de confidentialité
        </Link>
        .
      </p>
    </div>
  );
}
