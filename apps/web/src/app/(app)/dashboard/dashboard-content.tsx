// apps/web/src/app/(app)/dashboard/dashboard-content.tsx
// Client Component — gere les interactions : swap, generate, validate, add day
// Recoit les donnees initiales du Server Component parent (hydration)
// FIX BLOQUANT 2 (2026-04-12) : polling apres generation + structure PlanDetail plate
// Refonte dashboard (2026-04-12) :
//   - Modal "4 questions" avant generation / regeneration
//   - Panel swap suggestions pour remplacer un repas
//   - Panel ajout samedi/dimanche
//   - Mode lecture seule apres validation
"use client";

import { useCallback, useRef, useState } from "react";
import { CalendarDays, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  useCurrentPlan,
  useGeneratePlan,
  useSwapMeal,
  useAddMeal,
} from "@/hooks/use-plan";
import { PlanWeekGrid } from "@/components/plan/plan-week-grid";
import { PlanActions } from "@/components/plan/plan-actions";
import { GeneratePlanModal } from "@/components/plan/generate-plan-modal";
import { SwapSuggestionsPanel } from "@/components/plan/swap-suggestions-panel";
import type { GenerateFilters } from "@/components/plan/generate-plan-modal";
import type { PlanDetail } from "@/lib/api/endpoints";

interface DashboardContentProps {
  // Donnees initiales du Server Component (hydration SSR -> client)
  initialPlanData: PlanDetail | null;
}

export function DashboardContent({ initialPlanData }: DashboardContentProps) {
  // TanStack Query prend le relais cote client, initialPlanData sert de placeholder
  const { data: planDetail, isLoading, isGenerating, startPolling } = useCurrentPlan();
  // FIX BLOQUANT 2 : passer startPolling pour declencher le polling apres le 202
  const generateMutation = useGeneratePlan(startPolling);

  // Utiliser les donnees client si disponibles, sinon les donnees server
  const currentPlan = planDetail ?? initialPlanData;

  // --- Modal generation ---
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  // --- Panel swap ---
  const [swapState, setSwapState] = useState<{
    open: boolean;
    mealId: string | null;
  }>({ open: false, mealId: null });

  // --- Panel ajout jour ---
  const [addDayState, setAddDayState] = useState<{
    open: boolean;
    dayOfWeek: number | null;
  }>({ open: false, dayOfWeek: null });

  // Mutations swap et add
  const swapMealMutation = useSwapMeal(currentPlan?.id ?? "");
  const addMealMutation = useAddMeal(currentPlan?.id ?? "");

  // Ref pour eviter les retries multiples simultanes
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Handlers ---

  // Ouvrir le modal de generation (premiere generation OU regeneration)
  const openGenerateModal = useCallback(() => {
    setShowGenerateModal(true);
  }, []);

  // Generer avec filtres depuis le modal
  const handleGenerateWithFilters = useCallback(
    (filters: GenerateFilters) => {
      // Annuler un retry en attente
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }

      setShowGenerateModal(false);

      generateMutation.mutate(
        {
          max_time: filters.max_time ?? undefined,
          budget: filters.budget ?? undefined,
          style: filters.style ?? undefined,
        },
        {
          onError: (error: Error) => {
            if (error instanceof TypeError && error.message === "Failed to fetch") {
              toast.error("Connexion au serveur impossible.", {
                description: "Verifiez votre connexion. Nouvelle tentative dans 3 secondes...",
              });
              retryTimerRef.current = setTimeout(() => {
                retryTimerRef.current = null;
                generateMutation.mutate({
                  max_time: filters.max_time ?? undefined,
                  budget: filters.budget ?? undefined,
                  style: filters.style ?? undefined,
                });
              }, 3000);
            } else if (error.message.includes("401") || error.message.includes("403")) {
              toast.error("Session expiree.", {
                description: "Reconnectez-vous pour generer votre planning.",
              });
            } else if (!error.message.includes("Erreur API")) {
              toast.error("Une erreur est survenue.", {
                description: "Reessayez dans quelques instants.",
              });
            }
          },
        },
      );
    },
    [generateMutation],
  );

  // Ouvrir le panel de swap pour un repas
  const handleSwapMeal = useCallback((mealId: string) => {
    setSwapState({ open: true, mealId });
  }, []);

  // Selectioner une recette dans le panel de swap
  const handleSwapSelect = useCallback(
    (recipeId: string) => {
      if (!swapState.mealId) return;
      swapMealMutation.mutate(
        { mealId: swapState.mealId, recipeId },
        {
          onSuccess: () => {
            setSwapState({ open: false, mealId: null });
          },
        },
      );
    },
    [swapState.mealId, swapMealMutation],
  );

  // Ouvrir le panel pour ajouter samedi/dimanche
  const handleAddDay = useCallback((dayOfWeek: number) => {
    setAddDayState({ open: true, dayOfWeek });
  }, []);

  // Selectionner une recette pour le jour ajoute
  const handleAddDaySelect = useCallback(
    (recipeId: string) => {
      if (addDayState.dayOfWeek == null) return;
      addMealMutation.mutate(
        { dayOfWeek: addDayState.dayOfWeek, recipeId },
        {
          onSuccess: () => {
            setAddDayState({ open: false, dayOfWeek: null });
          },
        },
      );
    },
    [addDayState.dayOfWeek, addMealMutation],
  );

  // Label du jour pour le panel d'ajout
  const addDayLabel =
    addDayState.dayOfWeek === 6
      ? "Ajouter un repas samedi"
      : addDayState.dayOfWeek === 7
        ? "Ajouter un repas dimanche"
        : "Ajouter un repas";

  // --- Render ---

  if (isLoading && !initialPlanData) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-[#E2725B]" aria-hidden="true" />
      </div>
    );
  }

  // Etat "generation en cours" — polling actif, afficher un indicateur
  if (isGenerating && !currentPlan) {
    return <GeneratingState />;
  }

  // Etat vide — pas de plan cette semaine → ouvrir le modal
  if (!currentPlan) {
    return (
      <>
        <EmptyPlanState
          onGenerate={openGenerateModal}
          isGenerating={generateMutation.isPending}
        />
        <GeneratePlanModal
          open={showGenerateModal}
          onClose={() => setShowGenerateModal(false)}
          onGenerate={handleGenerateWithFilters}
          isGenerating={generateMutation.isPending}
        />
      </>
    );
  }

  // FIX BLOQUANT 3 : PlanDetail est plat — id et status sont directement sur l'objet
  return (
    <div className="space-y-6">
      {/* Grille des recettes de la semaine */}
      <PlanWeekGrid
        planDetail={currentPlan}
        onSwapMeal={currentPlan.status === "draft" ? handleSwapMeal : undefined}
        onAddDay={currentPlan.status === "draft" ? handleAddDay : undefined}
      />

      {/* Actions plan — onRegenerate toujours passé pour que le bouton
         "Modifier mon plan" apparaisse aussi en mode validated */}
      <PlanActions
        planId={currentPlan.id}
        planStatus={currentPlan.status}
        onRegenerate={openGenerateModal}
        isRegenerating={generateMutation.isPending}
      />

      {/* Modal de regeneration (meme modal que la premiere generation) */}
      <GeneratePlanModal
        open={showGenerateModal}
        onClose={() => setShowGenerateModal(false)}
        onGenerate={handleGenerateWithFilters}
        isGenerating={generateMutation.isPending}
      />

      {/* Panel swap suggestions */}
      {currentPlan.id && (
        <SwapSuggestionsPanel
          open={swapState.open}
          onClose={() => setSwapState({ open: false, mealId: null })}
          planId={currentPlan.id}
          title="Changer cette recette"
          onSelectRecipe={handleSwapSelect}
          isSubmitting={swapMealMutation.isPending}
        />
      )}

      {/* Panel ajout jour (samedi/dimanche) */}
      {currentPlan.id && (
        <SwapSuggestionsPanel
          open={addDayState.open}
          onClose={() => setAddDayState({ open: false, dayOfWeek: null })}
          planId={currentPlan.id}
          title={addDayLabel}
          onSelectRecipe={handleAddDaySelect}
          isSubmitting={addMealMutation.isPending}
        />
      )}
    </div>
  );
}

// Etat vide — CTA "Generer mon planning" (ouvre le modal)
interface EmptyPlanStateProps {
  onGenerate: () => void;
  isGenerating: boolean;
}

function EmptyPlanState({ onGenerate, isGenerating }: EmptyPlanStateProps) {
  return (
    <div className="mx-auto max-w-sm rounded-2xl border border-[#E2725B]/20 bg-[#fff8f6] p-8 text-center">
      <CalendarDays
        className="mx-auto mb-4 h-12 w-12 text-[#E2725B]/60"
        aria-hidden="true"
      />
      <h2 className="font-serif mb-2 text-xl font-semibold text-[#201a19]">
        Votre semaine vous attend
      </h2>
      <p className="mb-6 text-sm text-[#857370]">
        Laissez Presto generer votre plan de 5 a 7 diners adaptes a votre famille en quelques
        secondes.
      </p>
      <button
        type="button"
        onClick={onGenerate}
        disabled={isGenerating}
        aria-busy={isGenerating}
        className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
          bg-[#E2725B] px-6 py-3 font-semibold text-white
          transition-all hover:bg-[hsl(14,72%,46%)] focus-visible:outline-none
          focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2
          active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isGenerating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Generation en cours...
          </>
        ) : (
          <>
            <CalendarDays className="h-4 w-4" aria-hidden="true" />
            Generer mon planning
          </>
        )}
      </button>
    </div>
  );
}

// FIX BLOQUANT 2 : etat affiche pendant le polling (generation asynchrone Celery)
function GeneratingState() {
  return (
    <div className="mx-auto max-w-sm rounded-2xl border border-[#E2725B]/20 bg-[#fff8f6] p-8 text-center">
      <Loader2
        className="mx-auto mb-4 h-12 w-12 animate-spin text-[#E2725B]/60"
        aria-hidden="true"
      />
      <h2 className="font-serif mb-2 text-xl font-semibold text-[#201a19]">
        Generation en cours...
      </h2>
      <p className="text-sm text-[#857370]">
        Presto compose votre planning sur mesure. Cela prend generalement moins d&apos;une minute.
      </p>
    </div>
  );
}
