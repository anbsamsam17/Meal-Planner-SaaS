// apps/web/src/app/(legal)/legal/privacy/page.tsx
// Politique de confidentialité — conforme RGPD, mentionne Stripe et Supabase.
// Server Component — pas de "use client".
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de confidentialité",
  description:
    "Politique de confidentialité et protection des données personnelles du service Presto.",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-serif text-4xl font-bold text-neutral-900">
        Politique de confidentialité
      </h1>
      <p className="mt-2 text-sm text-neutral-500">
        Dernière mise à jour : avril 2026
      </p>

      <p className="mt-6 text-base leading-relaxed text-neutral-600">
        Presto accorde une importance primordiale à la protection de vos données personnelles. La
        présente politique décrit quelles données nous collectons, comment nous les utilisons et les
        droits dont vous disposez conformément au Règlement Général sur la Protection des Données (RGPD).
      </p>

      {/* Article 1 */}
      <section className="mt-10" aria-labelledby="priv-1">
        <h2 id="priv-1" className="font-serif text-xl font-semibold text-neutral-900">
          1. Responsable du traitement
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Le responsable du traitement des données personnelles est Presto, joignable à l&apos;adresse
          e-mail{" "}
          <a
            href="mailto:support@hop-presto.fr"
            className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
          >
            support@hop-presto.fr
          </a>
        </p>
      </section>

      {/* Article 2 */}
      <section className="mt-8" aria-labelledby="priv-2">
        <h2 id="priv-2" className="font-serif text-xl font-semibold text-neutral-900">
          2. Données collectées
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Nous collectons les données suivantes :
        </p>
        <ul className="mt-3 space-y-2">
          {[
            "Données d'identification : adresse e-mail, nom (optionnel)",
            "Données de profil : taille du foyer, régimes alimentaires, allergies, préférences culinaires",
            "Données d'utilisation : recettes consultées, notes attribuées, plans générés",
            "Données de paiement : gérées exclusivement par Stripe — nous ne stockons jamais vos coordonnées bancaires",
            "Données techniques : adresse IP, type de navigateur, pages visitées (logs serveur)",
          ].map((item) => (
            <li key={item} className="flex items-start gap-3 text-sm text-neutral-700">
              <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-400" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Article 3 */}
      <section className="mt-8" aria-labelledby="priv-3">
        <h2 id="priv-3" className="font-serif text-xl font-semibold text-neutral-900">
          3. Finalités du traitement
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Vos données sont utilisées pour :
        </p>
        <ul className="mt-3 space-y-2">
          {[
            "Fournir et personnaliser le Service (génération des plans de repas)",
            "Gérer votre abonnement et la facturation via Stripe",
            "Améliorer le Service et entraîner nos modèles de recommandation (données anonymisées)",
            "Vous envoyer des communications liées au Service (uniquement avec votre consentement)",
            "Respecter nos obligations légales",
          ].map((item) => (
            <li key={item} className="flex items-start gap-3 text-sm text-neutral-700">
              <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-400" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Article 4 */}
      <section className="mt-8" aria-labelledby="priv-4">
        <h2 id="priv-4" className="font-serif text-xl font-semibold text-neutral-900">
          4. Sous-traitants et partenaires
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Presto fait appel aux sous-traitants suivants, chacun disposant de garanties RGPD :
        </p>
        <div className="mt-4 space-y-3">
          {[
            {
              name: "Supabase",
              role: "Base de données et authentification",
              detail: "Données hébergées en Europe (EU-West). Conforme RGPD.",
            },
            {
              name: "Stripe",
              role: "Paiement et facturation",
              detail: "Certifié PCI-DSS. Aucune donnée bancaire n'est stockée par Presto.",
            },
            {
              name: "Railway / Vercel",
              role: "Hébergement de l'application",
              detail: "Infrastructures cloud avec certifications de sécurité.",
            },
          ].map(({ name, role, detail }) => (
            <div
              key={name}
              className="rounded-xl border border-neutral-200 bg-white p-4"
            >
              <p className="text-sm font-semibold text-neutral-900">
                {name}{" "}
                <span className="font-normal text-neutral-500">— {role}</span>
              </p>
              <p className="mt-1 text-xs text-neutral-500">{detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Article 5 */}
      <section className="mt-8" aria-labelledby="priv-5">
        <h2 id="priv-5" className="font-serif text-xl font-semibold text-neutral-900">
          5. Conservation des données
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Vos données sont conservées pendant toute la durée de votre compte, puis supprimées dans un
          délai de 30 jours après la clôture de votre compte. Les données de facturation sont conservées
          10 ans conformément aux obligations comptables légales.
        </p>
      </section>

      {/* Article 6 */}
      <section className="mt-8" aria-labelledby="priv-6">
        <h2 id="priv-6" className="font-serif text-xl font-semibold text-neutral-900">
          6. Vos droits
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Conformément au RGPD, vous disposez des droits suivants sur vos données personnelles :
        </p>
        <ul className="mt-3 space-y-2">
          {[
            "Droit d'accès : obtenir une copie de vos données",
            "Droit de rectification : corriger des données inexactes",
            "Droit à l'effacement : supprimer votre compte et vos données",
            "Droit à la portabilité : recevoir vos données dans un format standard",
            "Droit d'opposition : vous opposer à certains traitements",
          ].map((item) => (
            <li key={item} className="flex items-start gap-3 text-sm text-neutral-700">
              <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-400" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-neutral-600">
          Pour exercer vos droits, contactez-nous à{" "}
          <a
            href="mailto:support@hop-presto.fr"
            className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
          >
            support@hop-presto.fr
          </a>
          . Vous pouvez également supprimer votre compte directement depuis les paramètres de l&apos;application.
        </p>
        <p className="mt-3 text-sm text-neutral-600">
          En cas de réclamation non résolue, vous pouvez saisir la CNIL (
          <a
            href="https://www.cnil.fr"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
          >
            www.cnil.fr
          </a>
          ).
        </p>
      </section>

      {/* Article 7 */}
      <section className="mt-8" aria-labelledby="priv-7">
        <h2 id="priv-7" className="font-serif text-xl font-semibold text-neutral-900">
          7. Cookies
        </h2>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Presto utilise uniquement des cookies fonctionnels nécessaires au bon fonctionnement du Service
          (session d&apos;authentification, préférences de thème). Aucun cookie publicitaire ou de tracking
          tiers n&apos;est déposé sans votre consentement explicite.
        </p>
      </section>

      {/* Contact */}
      <section className="mt-10 rounded-xl border border-neutral-200 bg-white p-6" aria-labelledby="priv-contact">
        <h2 id="priv-contact" className="font-serif text-lg font-semibold text-neutral-900">
          Nous contacter
        </h2>
        <p className="mt-2 text-sm text-neutral-600">
          Pour toute question relative à la protection de vos données :{" "}
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
