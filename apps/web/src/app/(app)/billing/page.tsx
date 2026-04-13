// apps/web/src/app/(app)/billing/page.tsx
// Page de gestion d'abonnement Stripe
// Phase 2 — affiche le plan courant, CTA upgrade / portail Stripe
import type { Metadata } from "next";
import { BillingContent } from "./billing-content";

export const metadata: Metadata = {
  title: "Mon abonnement — Presto",
  description: "Gérez votre abonnement Presto : plan Starter, Famille ou Coach.",
};

export default function BillingPage() {
  return (
    <div className="min-h-screen bg-cream-50">
      <BillingContent />
    </div>
  );
}
