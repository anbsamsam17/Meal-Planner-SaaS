// apps/web/src/app/(legal)/layout.tsx
// Layout partagé pour les pages légales et institutionnelles (about, contact, CGU, confidentialité).
// Server Component — pas de "use client".
// Design cohérent avec la landing : fond #fff8f6, header minimal avec logo, footer.
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft } from "lucide-react";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#fff8f6]">
      {/* Header minimal */}
      <header className="border-b border-[#857370]/20 bg-[#fff8f6]/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-neutral-500 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Retour à l'accueil Presto"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Accueil
          </Link>

          <Link href="/" aria-label="Presto — accueil">
            <Image
              src="/logo_maj.png"
              alt="Presto"
              width={100}
              height={32}
              className="mix-blend-multiply object-contain"
            />
          </Link>
        </div>
      </header>

      {/* Contenu principal */}
      <main id="main-content">{children}</main>

      {/* Footer minimal */}
      <footer className="mt-20 border-t border-neutral-200 bg-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <nav
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-neutral-500"
            aria-label="Liens légaux"
          >
            <Link href="/about" className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
              À propos
            </Link>
            <Link href="/legal/terms" className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
              CGU
            </Link>
            <Link href="/legal/privacy" className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
              Confidentialité
            </Link>
            <Link href="/contact" className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
              Contact
            </Link>
          </nav>
          <p className="mt-4 text-center text-xs text-neutral-400">
            © 2026 Presto. Tous droits réservés.
          </p>
        </div>
      </footer>
    </div>
  );
}
