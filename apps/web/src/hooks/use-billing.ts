"use client";
// apps/web/src/hooks/use-billing.ts
// Hooks TanStack Query pour la gestion billing Stripe
// Phase 2 — GET /billing/status, POST /billing/checkout, POST /billing/portal

import { useQuery, useMutation } from "@tanstack/react-query";
import { getBillingStatus, createCheckout, createPortal } from "@/lib/api/endpoints";
import type { BillingStatus } from "@/lib/api/types";
import { toast } from "sonner";

export const BILLING_QUERY_KEYS = {
  status: ["billing", "status"] as const,
};

// Hook — Statut d'abonnement courant (GET /api/v1/billing/status)
export function useBillingStatus() {
  return useQuery<BillingStatus, Error>({
    queryKey: BILLING_QUERY_KEYS.status,
    queryFn: getBillingStatus,
    staleTime: 2 * 60 * 1000, // 2 minutes — le plan change rarement
    retry: 1,
  });
}

// Mutation — Créer une session Stripe Checkout (POST /api/v1/billing/checkout)
// Redirige automatiquement vers Stripe après succès
export function useCheckout(plan: string) {
  return useMutation({
    mutationFn: () => createCheckout(plan),
    onSuccess: (data) => {
      // Redirection vers Stripe Checkout (mode test configuré côté backend)
      window.location.href = data.checkout_url;
    },
    onError: (err: Error) => {
      toast.error("Impossible d'ouvrir le paiement", {
        description: err.message,
        duration: 6000,
      });
    },
  });
}

// Mutation — Ouvrir le portail Stripe (POST /api/v1/billing/portal)
// Redirige automatiquement vers le Customer Portal Stripe
export function usePortal() {
  return useMutation({
    mutationFn: createPortal,
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
    onError: (err: Error) => {
      toast.error("Impossible d'ouvrir le portail", {
        description: err.message,
        duration: 6000,
      });
    },
  });
}
