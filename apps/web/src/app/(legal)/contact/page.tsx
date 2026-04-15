// apps/web/src/app/(legal)/contact/page.tsx
// Page de contact — email support@hop-presto.fr.
// Server Component — pas de "use client".
import type { Metadata } from "next";
import { Mail, Clock, MessageCircle } from "lucide-react";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Contactez l'équipe Presto pour toute question, suggestion ou signalement. Réponse sous 24h.",
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      {/* Titre */}
      <h1 className="font-serif text-4xl font-bold text-neutral-900">
        Nous contacter
      </h1>
      <p className="mt-4 text-lg leading-relaxed text-neutral-600">
        Une question, une suggestion ou un problème ? L&apos;équipe Presto est là pour vous aider.
        Nous vous répondons en général sous 24 heures ouvrées.
      </p>

      {/* Carte email principal */}
      <div className="mt-10 rounded-2xl border border-primary-200 bg-primary-50 p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500">
            <Mail className="h-6 w-6 text-white" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-neutral-700">Support par e-mail</p>
            <a
              href="mailto:support@hop-presto.fr"
              className="text-xl font-bold text-primary-600 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              support@hop-presto.fr
            </a>
          </div>
        </div>
        <p className="mt-4 text-sm text-neutral-600">
          Pour toute question relative à votre compte, votre abonnement, un bug ou une suggestion
          d&apos;amélioration. Merci de préciser votre adresse e-mail Presto dans votre message.
        </p>
      </div>

      {/* Informations pratiques */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-neutral-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <Clock className="h-5 w-5 text-neutral-400" aria-hidden="true" />
            <h2 className="font-serif text-base font-semibold text-neutral-900">
              Délai de réponse
            </h2>
          </div>
          <p className="mt-2 text-sm text-neutral-600">
            Du lundi au vendredi, 9h–18h (heure de Paris). Réponse sous 24 heures ouvrées en général.
          </p>
        </div>

        <div className="rounded-xl border border-neutral-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <MessageCircle className="h-5 w-5 text-neutral-400" aria-hidden="true" />
            <h2 className="font-serif text-base font-semibold text-neutral-900">
              Sujets traités
            </h2>
          </div>
          <p className="mt-2 text-sm text-neutral-600">
            Aide technique, questions d&apos;abonnement, signalement de bugs, suggestions de recettes,
            demandes RGPD.
          </p>
        </div>
      </div>

      {/* FAQ rapide */}
      <section className="mt-10" aria-labelledby="faq-title">
        <h2 id="faq-title" className="font-serif text-2xl font-semibold text-neutral-900">
          Questions fréquentes
        </h2>
        <dl className="mt-4 space-y-4">
          {[
            {
              q: "Comment annuler mon abonnement ?",
              a: "Rendez-vous dans Paramètres → Mon abonnement → Résilier. La résiliation est immédiate et vous conservez l'accès jusqu'à la fin de la période en cours.",
            },
            {
              q: "Comment supprimer mon compte et mes données ?",
              a: "Dans Paramètres → Zone de danger → Supprimer mon compte. Toutes vos données sont supprimées sous 30 jours conformément à notre politique de confidentialité.",
            },
            {
              q: "Puis-je changer l'adresse e-mail de mon compte ?",
              a: "Contactez-nous à support@hop-presto.fr avec votre ancienne et votre nouvelle adresse e-mail.",
            },
          ].map(({ q, a }) => (
            <div key={q} className="rounded-xl border border-neutral-200 bg-white p-5">
              <dt className="text-sm font-semibold text-neutral-900">{q}</dt>
              <dd className="mt-1.5 text-sm text-neutral-600">{a}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
