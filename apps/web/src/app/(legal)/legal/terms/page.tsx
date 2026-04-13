// apps/web/src/app/(legal)/legal/terms/page.tsx
// Conditions d'utilisation -- stub minimal Phase 1
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conditions d'utilisation — Presto",
  description: "Conditions generales d'utilisation du service Presto.",
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="font-serif text-3xl font-bold text-neutral-900">
        Conditions d&apos;utilisation
      </h1>
      <p className="mt-4 text-[#857370]">
        Page en cours de redaction. Contactez-nous pour toute question relative
        aux conditions d&apos;utilisation du service Presto.
      </p>
    </div>
  );
}
