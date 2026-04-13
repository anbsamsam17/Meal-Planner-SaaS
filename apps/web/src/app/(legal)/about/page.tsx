// apps/web/src/app/(legal)/about/page.tsx
// Page "A propos" -- stub minimal Phase 1
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "A propos — Presto",
  description: "Decouvrez Presto, votre assistant de planification de repas.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="font-serif text-3xl font-bold text-neutral-900">
        A propos de Presto
      </h1>
      <p className="mt-4 text-[#857370]">
        Presto est un assistant intelligent de planification de repas pour les
        familles. Notre mission : vous faire gagner du temps chaque semaine en
        generant des menus equilibres adaptes a vos gouts, votre budget et vos
        contraintes alimentaires.
      </p>
      <p className="mt-4 text-[#857370]">
        Page en cours de redaction. Contactez-nous pour toute question.
      </p>
    </div>
  );
}
