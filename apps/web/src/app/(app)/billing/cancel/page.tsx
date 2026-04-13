// apps/web/src/app/(app)/billing/cancel/page.tsx
// Page affichée si l'utilisateur annule le checkout Stripe
// Phase 2 — Server Component, rappel des features manquées, CTA de retour

import type { Metadata } from "next";
import Link from "next/link";
import { XCircle, BookOpen, Refrigerator, Star } from "lucide-react";

export const metadata: Metadata = {
  title: "Paiement annulé — Presto",
};

const MISSED_FEATURES = [
  { icon: BookOpen, label: "Livres PDF hebdomadaires téléchargeables" },
  { icon: Refrigerator, label: "Mode frigo & suggestions intelligentes" },
  { icon: Star, label: "Accès à +500 recettes premium" },
];

export default function BillingCancelPage() {
  return (
    <div className="min-h-screen bg-[#fff8f6] px-4 py-12">
      <div className="mx-auto max-w-lg">
        {/* Icône */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-100">
            <XCircle className="h-10 w-10 text-neutral-400" aria-hidden />
          </div>
        </div>

        {/* Message principal */}
        <h1 className="mb-2 text-center text-2xl font-bold text-neutral-900">
          Pas de souci !
        </h1>
        <p className="mb-8 text-center text-sm text-neutral-500">
          Vous restez sur le plan Starter gratuit. Vous pouvez passer au plan Famille quand vous
          le souhaitez.
        </p>

        {/* Features manquées */}
        <div className="mb-8 rounded-xl border border-neutral-200 bg-white p-5">
          <p className="mb-4 text-sm font-medium text-neutral-700">
            Ce que vous obtiendrez avec le plan Famille :
          </p>
          <ul className="space-y-3">
            {MISSED_FEATURES.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-3 text-sm text-neutral-600">
                <Icon className="h-4 w-4 flex-shrink-0 text-primary-500" aria-hidden />
                {label}
              </li>
            ))}
          </ul>

          <Link
            href="/billing"
            className="mt-5 inline-flex min-h-[44px] w-full items-center justify-center rounded-lg bg-primary-600 px-6 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Voir les plans (9,99 €/mois)
          </Link>
        </div>

        {/* Retour dashboard */}
        <p className="text-center">
          <Link
            href="/dashboard"
            className="text-sm text-neutral-500 underline-offset-2 hover:text-neutral-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            Retourner au tableau de bord
          </Link>
        </p>
      </div>
    </div>
  );
}
