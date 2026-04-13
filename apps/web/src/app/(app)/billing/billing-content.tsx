"use client";
// apps/web/src/app/(app)/billing/billing-content.tsx
// Contenu interactif de la page billing — Client Component
// Phase 2 — comparaison plans, CTA checkout/portail

import { Check, CreditCard, Zap } from "lucide-react";
import { useBillingStatus, useCheckout, usePortal } from "@/hooks/use-billing";

const STARTER_FEATURES = [
  "1 plan hebdomadaire / semaine",
  "Accès aux recettes de base",
  "Liste de courses automatique",
];

const FAMILLE_FEATURES = [
  "Plans illimités",
  "Mode frigo & suggestions",
  "Livres PDF hebdomadaires",
  "Recettes premium (+500 recettes)",
  "Support prioritaire",
];

function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, string> = {
    starter: "bg-neutral-100 text-neutral-700",
    famille: "bg-primary-100 text-primary-700",
    coach: "bg-olive-100 text-olive-700",
  };
  const labels: Record<string, string> = {
    starter: "Starter",
    famille: "Famille",
    coach: "Coach",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-0.5 text-xs font-semibold ${colors[plan] ?? "bg-neutral-100 text-neutral-700"}`}
    >
      {labels[plan] ?? plan}
    </span>
  );
}

function formatDate(isoDate: string | null): string {
  if (!isoDate) return "—";
  return new Date(isoDate).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function BillingContent() {
  const { data: billing, isLoading } = useBillingStatus();
  const checkoutMutation = useCheckout("famille");
  const portalMutation = usePortal();

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-300 border-t-primary-600" />
      </div>
    );
  }

  const isStarter = !billing || billing.plan === "starter";
  const isPremium = billing && (billing.plan === "famille" || billing.plan === "coach");

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      {/* En-tête */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900">Mon abonnement</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Gérez votre plan et vos informations de facturation.
        </p>
      </div>

      {/* Plan courant */}
      {billing && (
        <div className="mb-6 flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-5 py-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Plan actuel
            </p>
            <div className="mt-1 flex items-center gap-2">
              <PlanBadge plan={billing.plan} />
              {billing.cancel_at_period_end && (
                <span className="text-xs text-amber-600">Annulation prévue</span>
              )}
            </div>
          </div>
          {billing.current_period_end && (
            <div className="text-right">
              <p className="text-xs text-neutral-500">Prochaine facture</p>
              <p className="text-sm font-medium text-neutral-900">
                {formatDate(billing.current_period_end)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* --- Vue Starter : comparaison des plans + CTA upgrade --- */}
      {isStarter && (
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Plan Starter */}
          <div className="rounded-xl border border-neutral-200 bg-white p-5">
            <div className="mb-4">
              <PlanBadge plan="starter" />
              <p className="mt-2 text-2xl font-bold text-neutral-900">
                Gratuit
              </p>
              <p className="text-sm text-neutral-500">Pour découvrir Presto</p>
            </div>
            <ul className="space-y-2">
              {STARTER_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-neutral-700">
                  <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-neutral-400" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
            <div className="mt-5">
              <span className="inline-block w-full rounded-lg border border-neutral-200 py-2 text-center text-sm font-medium text-neutral-500">
                Plan actuel
              </span>
            </div>
          </div>

          {/* Plan Famille */}
          <div className="rounded-xl border-2 border-primary-400 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <PlanBadge plan="famille" />
              <p className="mt-2 text-2xl font-bold text-neutral-900">
                9,99 €
                <span className="text-sm font-normal text-neutral-500"> / mois</span>
              </p>
              <p className="text-sm text-neutral-500">Pour les familles organisées</p>
            </div>
            <ul className="space-y-2">
              {FAMILLE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-neutral-700">
                  <Check
                    className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary-600"
                    aria-hidden
                  />
                  {f}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => checkoutMutation.mutate()}
              disabled={checkoutMutation.isPending}
              className="mt-5 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              <Zap className="h-4 w-4" aria-hidden />
              {checkoutMutation.isPending ? "Redirection..." : "Passer au plan Famille"}
            </button>
          </div>
        </div>
      )}

      {/* --- Vue Premium : statut + accès portail --- */}
      {isPremium && (
        <div className="rounded-xl border border-neutral-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
              <CreditCard className="h-5 w-5 text-primary-600" aria-hidden />
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900">Abonnement actif</p>
              <p className="text-xs text-neutral-500">
                Statut :{" "}
                <span className="font-medium text-green-700">
                  {billing?.status === "active" ? "Actif" : billing?.status}
                </span>
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm text-neutral-600">
            Pour modifier votre moyen de paiement, changer de plan ou annuler votre abonnement,
            accédez au portail Stripe.
          </p>

          <button
            type="button"
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="mt-4 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            <CreditCard className="h-4 w-4" aria-hidden />
            {portalMutation.isPending ? "Redirection..." : "Gérer mon abonnement"}
          </button>
        </div>
      )}
    </div>
  );
}
