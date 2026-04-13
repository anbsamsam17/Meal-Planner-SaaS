// apps/web/src/app/(legal)/contact/page.tsx
// Page de contact -- stub minimal Phase 1
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact — Presto",
  description: "Contactez l'equipe Presto pour toute question ou suggestion.",
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="font-serif text-3xl font-bold text-neutral-900">
        Nous contacter
      </h1>
      <p className="mt-4 text-[#857370]">
        Une question, une suggestion ou un probleme ? N&apos;hesitez pas a nous
        ecrire. Nous vous repondrons dans les plus brefs delais.
      </p>
      <p className="mt-4 text-[#857370]">
        Email : <a href="mailto:contact@hop-presto.fr" className="text-[#E2725B] underline hover:text-[#C8674A]">contact@hop-presto.fr</a>
      </p>
    </div>
  );
}
