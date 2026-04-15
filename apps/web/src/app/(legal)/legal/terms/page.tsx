// apps/web/src/app/(legal)/legal/terms/page.tsx
// Conditions Générales d'Utilisation — contenu professionnel RGPD-compatible.
// Server Component — pas de "use client".
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conditions d'utilisation",
  description: "Conditions Générales d'Utilisation du service Presto de planification de repas.",
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-serif text-4xl font-bold text-neutral-900">
        Conditions Générales d&apos;Utilisation
      </h1>
      <p className="mt-2 text-sm text-neutral-500">
        Dernière mise à jour : avril 2026
      </p>

      <p className="mt-6 text-base leading-relaxed text-neutral-600">
        Les présentes Conditions Générales d&apos;Utilisation (ci-après « CGU ») régissent l&apos;accès et
        l&apos;utilisation du service Presto, accessible à l&apos;adresse{" "}
        <span className="font-medium text-neutral-800">hop-presto.fr</span> (ci-après « le Service »),
        édité par la société Presto (ci-après « nous »).
      </p>

      {/* Article 1 */}
      <section className="mt-10" aria-labelledby="article-1">
        <h2 id="article-1" className="font-serif text-xl font-semibold text-neutral-900">
          1. Acceptation des conditions
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          En créant un compte ou en utilisant le Service, vous acceptez sans réserve les présentes CGU.
          Si vous n&apos;acceptez pas ces conditions, vous ne pouvez pas utiliser le Service.
        </p>
      </section>

      {/* Article 2 */}
      <section className="mt-8" aria-labelledby="article-2">
        <h2 id="article-2" className="font-serif text-xl font-semibold text-neutral-900">
          2. Description du Service
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Presto est un service de planification de repas par intelligence artificielle. Le Service permet
          aux utilisateurs de générer des plans de repas hebdomadaires personnalisés, des listes de courses
          et d&apos;accéder à une bibliothèque de recettes.
        </p>
      </section>

      {/* Article 3 */}
      <section className="mt-8" aria-labelledby="article-3">
        <h2 id="article-3" className="font-serif text-xl font-semibold text-neutral-900">
          3. Inscription et compte utilisateur
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          L&apos;accès au Service nécessite la création d&apos;un compte. Vous vous engagez à fournir des
          informations exactes et à maintenir la confidentialité de vos identifiants de connexion. Vous
          êtes responsable de toute activité effectuée depuis votre compte.
        </p>
      </section>

      {/* Article 4 */}
      <section className="mt-8" aria-labelledby="article-4">
        <h2 id="article-4" className="font-serif text-xl font-semibold text-neutral-900">
          4. Abonnements et facturation
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Presto propose un plan gratuit (Starter) et un plan payant (Famille). Les paiements sont traités
          par Stripe, prestataire de services de paiement certifié PCI-DSS. L&apos;abonnement est renouvelé
          automatiquement chaque mois sauf résiliation. Vous pouvez résilier à tout moment depuis votre
          espace client.
        </p>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          La période d&apos;essai gratuite de 14 jours ne nécessite pas de carte bancaire. À l&apos;issue
          de la période d&apos;essai, le passage en plan payant requiert l&apos;enregistrement d&apos;un moyen
          de paiement.
        </p>
      </section>

      {/* Article 5 */}
      <section className="mt-8" aria-labelledby="article-5">
        <h2 id="article-5" className="font-serif text-xl font-semibold text-neutral-900">
          5. Propriété intellectuelle
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          L&apos;ensemble des contenus du Service (recettes, textes, images, logiciels) sont la propriété
          exclusive de Presto ou de ses partenaires et sont protégés par le droit de la propriété
          intellectuelle. Toute reproduction ou utilisation non autorisée est interdite.
        </p>
      </section>

      {/* Article 6 */}
      <section className="mt-8" aria-labelledby="article-6">
        <h2 id="article-6" className="font-serif text-xl font-semibold text-neutral-900">
          6. Limitation de responsabilité
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Les plans de repas générés par Presto sont fournis à titre indicatif. Presto ne saurait être
          tenu responsable des conséquences découlant de l&apos;utilisation des recettes ou des listes de
          courses (allergies, intolérances, disponibilité des produits en magasin, etc.).
        </p>
      </section>

      {/* Article 7 */}
      <section className="mt-8" aria-labelledby="article-7">
        <h2 id="article-7" className="font-serif text-xl font-semibold text-neutral-900">
          7. Droit applicable
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Les présentes CGU sont soumises au droit français. En cas de litige, les parties s&apos;engagent
          à rechercher une solution amiable avant tout recours judiciaire. À défaut, les tribunaux
          français seront seuls compétents.
        </p>
      </section>

      {/* Contact */}
      <section className="mt-10 rounded-xl border border-neutral-200 bg-white p-6" aria-labelledby="contact-cgu">
        <h2 id="contact-cgu" className="font-serif text-lg font-semibold text-neutral-900">
          Nous contacter
        </h2>
        <p className="mt-2 text-sm text-neutral-600">
          Pour toute question relative aux présentes CGU, contactez-nous à{" "}
          <a
            href="mailto:support@hop-presto.fr"
            className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
          >
            support@hop-presto.fr
          </a>
        </p>
      </section>
    </div>
  );
}
