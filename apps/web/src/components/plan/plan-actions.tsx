// apps/web/src/components/plan/plan-actions.tsx
// Boutons d'action sur le plan : Valider / Régénérer / Voir la liste de courses
// Client Component — mutations TanStack Query
"use client";

import Link from "next/link";
import { CheckCircle, RefreshCw, ShoppingCart, Loader2 } from "lucide-react";
import { useValidatePlan, useGeneratePlan } from "@/hooks/use-plan";
import { cn } from "@/lib/utils";

// FIX BLOQUANT 3 (2026-04-12) — status backend : "draft" | "validated" | "archived"
interface PlanActionsProps {
  planId: string;
  planStatus: "draft" | "validated" | "archived";
  onStartPolling?: () => void;
  className?: string;
}

export function PlanActions({ planId, planStatus, onStartPolling, className }: PlanActionsProps) {
  const validateMutation = useValidatePlan();
  const generateMutation = useGeneratePlan(onStartPolling);

  const isValidated = planStatus === "validated" || planStatus === "archived";

  return (
    <div className={cn("flex flex-col gap-3 sm:flex-row", className)}>
      {/* Valider le plan */}
      <button
        type="button"
        onClick={() => validateMutation.mutate(planId)}
        disabled={validateMutation.isPending || isValidated}
        aria-busy={validateMutation.isPending}
        className={cn(
          "inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-xl px-4 py-3",
          "text-sm font-semibold transition-all duration-base",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
          isValidated
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
            : "bg-primary-500 text-white hover:bg-primary-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        {validateMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <CheckCircle className="h-4 w-4" aria-hidden="true" />
        )}
        {isValidated ? "Plan validé" : "Valider le plan"}
      </button>

      {/* Voir la liste de courses */}
      <Link
        href={`/shopping-list?plan=${planId}`}
        className="inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-xl
          border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold text-neutral-700
          transition-all hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2
          dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200"
      >
        <ShoppingCart className="h-4 w-4" aria-hidden="true" />
        Voir mes courses
      </Link>

      {/* Régénérer le plan */}
      <button
        type="button"
        onClick={() => generateMutation.mutate()}
        disabled={generateMutation.isPending}
        aria-busy={generateMutation.isPending}
        className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl px-4 py-3
          text-sm font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2
          disabled:opacity-50 dark:text-neutral-400 dark:hover:bg-neutral-700"
      >
        {generateMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
        )}
        Régénérer
      </button>
    </div>
  );
}
