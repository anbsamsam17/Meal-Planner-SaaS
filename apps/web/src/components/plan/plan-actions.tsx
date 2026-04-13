// apps/web/src/components/plan/plan-actions.tsx
// Boutons d'action sur le plan : Valider / Regenerer / Voir la liste de courses
// Client Component — mutations TanStack Query
// Refonte dashboard (2026-04-12) :
//   - status=draft → Valider + Regenerer (ouvre modal 4 questions)
//   - status=validated → "Plan valide" badge + "Voir ma liste de courses" en vert
//   - swap/regenerer disparaissent apres validation
"use client";

import Link from "next/link";
import { CheckCircle, RefreshCw, ShoppingCart, Loader2 } from "lucide-react";
import { useValidatePlan } from "@/hooks/use-plan";
import { cn } from "@/lib/utils";

// FIX BLOQUANT 3 (2026-04-12) — status backend : "draft" | "validated" | "archived"
interface PlanActionsProps {
  planId: string;
  planStatus: "draft" | "validated" | "archived";
  /** Ouvre le modal de generation avec les 4 questions */
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  className?: string;
}

export function PlanActions({
  planId,
  planStatus,
  onRegenerate,
  isRegenerating = false,
  className,
}: PlanActionsProps) {
  const validateMutation = useValidatePlan();

  const isValidated = planStatus === "validated" || planStatus === "archived";

  return (
    <div className={cn("flex flex-col gap-3 sm:flex-row", className)}>
      {/* Mode draft : bouton Valider + Regenerer */}
      {!isValidated && (
        <>
          {/* Valider le plan */}
          <button
            type="button"
            onClick={() => validateMutation.mutate(planId)}
            disabled={validateMutation.isPending}
            aria-busy={validateMutation.isPending}
            className={cn(
              "inline-flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-xl px-4 py-3",
              "text-sm font-semibold transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2",
              "bg-[#E2725B] text-white hover:bg-[hsl(14,72%,46%)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            {validateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <CheckCircle className="h-4 w-4" aria-hidden="true" />
            )}
            Valider mon plan
          </button>

          {/* Regenerer — ouvre le modal 4 questions */}
          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isRegenerating}
              aria-busy={isRegenerating}
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl px-4 py-3
                text-sm font-medium text-[#857370] transition-colors hover:bg-[#857370]/10 hover:text-[#201a19]
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2
                disabled:opacity-50"
            >
              {isRegenerating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
              )}
              Regenerer
            </button>
          )}
        </>
      )}

      {/* Mode validated : badge + modifier + lien courses */}
      {isValidated && (
        <>
          <div
            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl
              bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700"
          >
            <CheckCircle className="h-4 w-4" aria-hidden="true" />
            Plan validé
          </div>

          {/* Modifier mon plan — remet en draft */}
          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl px-4 py-3
                text-sm font-medium text-[#857370] transition-colors hover:bg-[#857370]/10
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Modifier mon plan
            </button>
          )}

          <Link
            href="/shopping-list"
            className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2
              text-xs font-medium bg-emerald-500 text-white hover:bg-emerald-600 transition-all"
          >
            <ShoppingCart className="h-4 w-4" aria-hidden="true" />
            Voir ma liste de courses
          </Link>
        </>
      )}
    </div>
  );
}
