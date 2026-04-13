// apps/web/src/app/(app)/dashboard/dashboard-content.tsx
// Client Component — gère les interactions : swap, generate, validate
// Reçoit les données initiales du Server Component parent (hydration)
// BUG 3 FIX (2026-04-12) : gestion d'erreur "Failed to fetch" améliorée + retry automatique
"use client";

import { useCallback, useRef } from "react";
import { CalendarDays, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useCurrentPlan, useGeneratePlan } from "@/hooks/use-plan";
import { PlanWeekGrid } from "@/components/plan/plan-week-grid";
import { PlanActions } from "@/components/plan/plan-actions";
import type { PlanDetail } from "@/lib/api/endpoints";

interface DashboardContentProps {
  // Données initiales du Server Component (hydration SSR → client)
  initialPlanData: PlanDetail | null;
}

export function DashboardContent({ initialPlanData }: DashboardContentProps) {
  // TanStack Query prend le relais côté client, initialPlanData sert de placeholder
  const { data: planDetail, isLoading } = useCurrentPlan();
  const generateMutation = useGeneratePlan();

  // Ref pour éviter les retries multiples simultanés
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Utiliser les données client si disponibles, sinon les données server
  const currentPlan = planDetail ?? initialPlanData;

  // BUG 3 FIX : handler avec distinction d'erreur réseau + retry automatique 3s
  const handleGenerate = useCallback(() => {
    // Annuler un retry en attente si l'utilisateur clique à nouveau
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }

    generateMutation.mutate(undefined, {
      onError: (error: Error) => {
        if (error instanceof TypeError && error.message === "Failed to fetch") {
          toast.error("Connexion au serveur impossible.", {
            description: "Vérifiez votre connexion. Nouvelle tentative dans 3 secondes…",
          });
          // Retry automatique après 3 secondes
          retryTimerRef.current = setTimeout(() => {
            retryTimerRef.current = null;
            generateMutation.mutate();
          }, 3000);
        } else if (error.message.includes("401") || error.message.includes("403")) {
          toast.error("Session expirée.", {
            description: "Reconnectez-vous pour générer votre planning.",
          });
        } else if (!error.message.includes("Erreur API")) {
          // Le client API affiche déjà un toast pour les erreurs HTTP connues
          toast.error("Une erreur est survenue.", {
            description: "Réessayez dans quelques instants.",
          });
        }
      },
    });
  }, [generateMutation]);

  if (isLoading && !initialPlanData) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary-400" aria-hidden="true" />
      </div>
    );
  }

  // État vide — pas de plan cette semaine
  if (!currentPlan) {
    return (
      <EmptyPlanState
        onGenerate={handleGenerate}
        isGenerating={generateMutation.isPending}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Grille des recettes de la semaine */}
      <PlanWeekGrid planDetail={currentPlan} />

      {/* Actions plan */}
      <PlanActions
        planId={currentPlan.plan.id}
        planStatus={currentPlan.plan.status}
      />
    </div>
  );
}

// État vide — CTA "Générer mon planning"
interface EmptyPlanStateProps {
  onGenerate: () => void;
  isGenerating: boolean;
}

function EmptyPlanState({ onGenerate, isGenerating }: EmptyPlanStateProps) {
  return (
    <div className="mx-auto max-w-sm rounded-2xl border border-primary-200 bg-primary-50 p-8 text-center dark:border-primary-800 dark:bg-primary-950/30">
      <CalendarDays
        className="mx-auto mb-4 h-12 w-12 text-primary-400"
        aria-hidden="true"
      />
      <h2 className="font-serif mb-2 text-xl font-semibold text-neutral-900 dark:text-neutral-100">
        Votre semaine vous attend
      </h2>
      <p className="mb-6 text-sm text-neutral-600 dark:text-neutral-400">
        Laissez Presto générer votre plan de 5 à 7 dîners adaptés à votre famille en quelques
        secondes.
      </p>
      <button
        type="button"
        onClick={onGenerate}
        disabled={isGenerating}
        aria-busy={isGenerating}
        className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
          bg-primary-500 px-6 py-3 font-semibold text-white
          transition-all hover:bg-primary-600 focus-visible:outline-none
          focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2
          active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isGenerating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Génération en cours…
          </>
        ) : (
          <>
            <CalendarDays className="h-4 w-4" aria-hidden="true" />
            Générer mon planning
          </>
        )}
      </button>
    </div>
  );
}
