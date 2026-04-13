// apps/web/src/app/(legal)/legal/privacy/page.tsx
// Politique de confidentialite -- stub minimal Phase 1
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de confidentialite — Presto",
  description: "Politique de confidentialite et protection des donnees personnelles de Presto.",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="font-serif text-3xl font-bold text-neutral-900">
        Politique de confidentialite
      </h1>
      <p className="mt-4 text-[#857370]">
        Page en cours de redaction. Nous prenons la protection de vos donnees
        personnelles tres au serieux. Contactez-nous pour toute question
        relative a la confidentialite.
      </p>
    </div>
  );
}
