"use client";
// apps/web/src/components/billing/upgrade-gate.tsx
// Wrapper pour les features premium — affiche un prompt d'upgrade si le plan est insuffisant
// Phase 2 — gating plan famille/coach

import type { ReactNode } from "react";
import Link from "next/link";
import { Lock } from "lucide-react";
import { useBillingStatus } from "@/hooks/use-billing";
import type { BillingPlan } from "@/lib/api/types";

// Ordre des plans pour la comparaison hiérarchique
const PLAN_HIERARCHY: Record<BillingPlan, number> = {
  starter: 0,
  famille: 1,
  coach: 2,
};

interface UpgradePromptProps {
  requiredPlan: "famille" | "coach";
  featureLabel?: string;
}

function UpgradePrompt({ requiredPlan, featureLabel }: UpgradePromptProps) {
  const planLabel = requiredPlan === "famille" ? "Famille (9,99 €/mois)" : "Coach";

  return (
    <div className="relative flex flex-col items-center justify-center rounded-xl border border-dashed border-primary-300 bg-cream-50 px-6 py-10 text-center">
      {/* Icône cadenas */}
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100">
        <Lock className="h-6 w-6 text-primary-600" aria-hidden="true" />
      </div>

      <h3 className="mb-1 text-base font-semibold text-neutral-900">
        {featureLabel ? `"${featureLabel}"` : "Cette fonctionnalité"} est réservée au plan{" "}
        <span className="text-primary-600">{planLabel}</span>
      </h3>

      <p className="mb-6 max-w-xs text-sm text-neutral-500">
        Passez au plan {requiredPlan === "famille" ? "Famille" : "Coach"} pour débloquer cette
        fonctionnalité et profiter de toutes les options premium.
      </p>

      <Link
        href="/billing"
        className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-primary-600 px-6 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
      >
        Voir les plans
      </Link>
    </div>
  );
}

interface UpgradeGateProps {
  requiredPlan: "famille" | "coach";
  featureLabel?: string;
  // Afficher le contenu flouté au lieu du prompt (effet blur)
  blurChildren?: boolean;
  children: ReactNode;
}

export function UpgradeGate({
  requiredPlan,
  featureLabel,
  blurChildren = false,
  children,
}: UpgradeGateProps) {
  const { data: billing, isLoading } = useBillingStatus();

  // Pendant le chargement, on ne bloque pas le rendu
  if (isLoading) {
    return <>{children}</>;
  }

  const currentPlan = billing?.plan ?? "starter";
  const hasAccess = PLAN_HIERARCHY[currentPlan] >= PLAN_HIERARCHY[requiredPlan];

  if (hasAccess) {
    return <>{children}</>;
  }

  // Mode blur : afficher le contenu flouté + overlay avec CTA
  if (blurChildren) {
    return (
      <div className="relative">
        <div className="pointer-events-none select-none blur-sm" aria-hidden="true">
          {children}
        </div>
        <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-neutral-50/80 backdrop-blur-sm">
          <UpgradePrompt requiredPlan={requiredPlan} featureLabel={featureLabel} />
        </div>
      </div>
    );
  }

  return <UpgradePrompt requiredPlan={requiredPlan} featureLabel={featureLabel} />;
}
