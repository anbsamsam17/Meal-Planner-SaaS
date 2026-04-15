// apps/web/src/app/(legal)/about/page.tsx
// Page "À propos de Presto" — présentation professionnelle du service.
// Server Component — pas de "use client".
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "À propos",
  description:
    "Découvrez Presto, votre assistant intelligent de planification de repas pour les familles françaises.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      {/* Titre principal */}
      <h1 className="font-serif text-4xl font-bold text-neutral-900">
        À propos de Presto
      </h1>
      <p className="mt-4 text-lg leading-relaxed text-neutral-600">
        Presto est un assistant intelligent de planification de repas, conçu pour les familles françaises
        qui veulent mieux manger sans y passer des heures.
      </p>

      {/* Mission */}
      <section className="mt-10" aria-labelledby="mission-title">
        <h2 id="mission-title" className="font-serif text-2xl font-semibold text-neutral-900">
          Notre mission
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Nous croyons que cuisiner en famille est l&apos;un des meilleurs moments de la semaine — encore
          faut-il savoir quoi préparer. Presto prend en charge la planification pour que vous puissiez
          vous concentrer sur le plaisir de cuisiner.
        </p>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          En 90 secondes, Presto génère un plan de repas personnalisé pour la semaine, adapté aux goûts
          de chaque membre de votre famille, à vos contraintes alimentaires et au temps dont vous disposez.
        </p>
      </section>

      {/* Ce que Presto fait */}
      <section className="mt-10" aria-labelledby="what-title">
        <h2 id="what-title" className="font-serif text-2xl font-semibold text-neutral-900">
          Ce que Presto fait pour vous
        </h2>
        <ul className="mt-4 space-y-3">
          {[
            "Génération de menus hebdomadaires personnalisés par l'IA",
            "Liste de courses automatique, organisée par rayon",
            "Adaptation aux régimes alimentaires (végétarien, sans gluten, halal…)",
            "Intégration drive (Leclerc, Auchan, Carrefour, Intermarché) — bientôt disponible",
            "Livre PDF hebdomadaire imprimable pour cuisiner sans écran",
            "Mémoire Presto : l'IA apprend les goûts de votre famille semaine après semaine",
          ].map((item) => (
            <li key={item} className="flex items-start gap-3 text-base text-neutral-700">
              <span
                className="mt-1 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-600 text-xs font-bold"
                aria-hidden="true"
              >
                ✓
              </span>
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* L'équipe */}
      <section className="mt-10" aria-labelledby="team-title">
        <h2 id="team-title" className="font-serif text-2xl font-semibold text-neutral-900">
          L&apos;équipe
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Presto est développé en France par une équipe passionnée de cuisine et de technologie.
          Nous sommes convaincus que la planification des repas ne devrait pas être une corvée.
        </p>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Des questions ? Écrivez-nous à{" "}
          <a
            href="mailto:support@hop-presto.fr"
            className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
          >
            support@hop-presto.fr
          </a>
        </p>
      </section>

      {/* CTA */}
      <div className="mt-12">
        <Link
          href="/signup"
          className="inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-primary-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        >
          Essayer Presto gratuitement
        </Link>
      </div>
    </div>
  );
}
