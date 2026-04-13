// apps/web/src/hooks/use-plan.ts
// Hooks TanStack Query pour les plans hebdomadaires
// Couvre : plan courant, plan par ID, generation, swap recette, ajout repas, suggestions
// FIX BLOQUANT 2 (2026-04-12) : polling conditionnel apres generation asynchrone (Celery)
// Refonte dashboard (2026-04-12) : filtres generation, suggestions, ajout repas samedi/dimanche
"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCurrentPlan,
  getPlan,
  generatePlan,
  swapMeal,
  validatePlan,
  revertPlanToDraft,
  getRecipeSuggestions,
  addMealToPlan,
} from "@/lib/api/endpoints";
import type { PlanDetail, GeneratePlanParams } from "@/lib/api/endpoints";
import type { Recipe } from "@/lib/api/types";
import { toast } from "sonner";

// Cles de requete stables
export const PLAN_QUERY_KEYS = {
  current: ["plans", "current"] as const,
  byId: (id: string) => ["plans", id] as const,
  suggestions: (planId: string, filters?: { style?: string; max_time?: number }) =>
    ["plans", planId, "suggestions", filters] as const,
};

// Timeout max pour le polling (60 secondes)
const POLLING_INTERVAL_MS = 3_000;
const POLLING_TIMEOUT_MS = 60_000;

// Hook — Plan courant (GET /api/v1/plans/me/current)
// FIX BLOQUANT 2 : polling conditionnel toutes les 3s pendant la generation, timeout 60s
export function useCurrentPlan() {
  const [isGenerating, setIsGenerating] = useState(false);
  const pollingStartRef = useRef<number>(0);
  // Memorise l'ID du plan existant au moment ou startPolling() est appele.
  // Permet de detecter que le polling a bien recupere un NOUVEAU plan
  // et non l'ancien plan encore en cache (bug : polling stoppait immediatement
  // car query.data contenait toujours l'ancien plan draft apres revert-to-draft).
  const previousPlanIdRef = useRef<string | null>(null);

  const query = useQuery<PlanDetail | null, Error>({
    queryKey: PLAN_QUERY_KEYS.current,
    queryFn: async () => {
      try {
        return await getCurrentPlan();
      } catch (err) {
        // 404 = pas de plan pour la semaine → etat valide, retourner null
        if (err instanceof Error && err.message.includes("404")) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    // Polling toutes les 3s UNIQUEMENT pendant la generation
    refetchInterval: isGenerating ? POLLING_INTERVAL_MS : false,
    retry: (failureCount, err) => {
      if (err.message.includes("401") || err.message.includes("403")) return false;
      return failureCount < 2;
    },
  });

  // Arreter le polling quand un NOUVEAU plan est trouve OU timeout depasse.
  // IMPORTANT : on compare l'ID du plan courant avec l'ID memorise avant la generation.
  // Sans cette comparaison, l'ancien plan encore en cache stopperait le polling
  // immediatement, avant que le refetch ne rapporte le nouveau plan.
  useEffect(() => {
    if (!isGenerating) return;

    // Plan trouve ET c'est un plan different de l'ancien → succes
    if (query.data && query.data.id !== previousPlanIdRef.current) {
      setIsGenerating(false);
      toast.success("Votre planning est pret !");
      return;
    }

    // Timeout : arreter le polling apres 60s
    const elapsed = Date.now() - pollingStartRef.current;
    if (elapsed > POLLING_TIMEOUT_MS) {
      setIsGenerating(false);
      toast.error("La generation prend plus de temps que prevu.", {
        description: "Rafraichissez la page dans quelques instants.",
      });
    }
  }, [query.data, isGenerating]);

  // Demarrer le polling (appele depuis useGeneratePlan).
  // Capture l'ID du plan actuel pour que le useEffect puisse distinguer
  // l'ancien plan (cache stale) du nouveau plan (apres refetch).
  const startPolling = (currentPlanId?: string | null) => {
    previousPlanIdRef.current = currentPlanId ?? null;
    pollingStartRef.current = Date.now();
    setIsGenerating(true);
  };

  return { ...query, isGenerating, startPolling };
}

// Hook — Plan par ID (GET /api/v1/plans/{id})
export function usePlan(id: string | null) {
  return useQuery<PlanDetail, Error>({
    queryKey: PLAN_QUERY_KEYS.byId(id ?? ""),
    queryFn: () => {
      if (!id) throw new Error("Plan ID requis");
      return getPlan(id);
    },
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
}

// Mutation — Generer un nouveau plan (POST /api/v1/plans/generate)
// FIX BLOQUANT 2 : apres le 200, on declenche le polling via startPolling()
// Le toast de succes est affiche par useCurrentPlan quand le nouveau plan arrive.
// Refonte : accepte les filtres max_time, budget, style depuis le modal "4 questions"
// FIX (2026-04-13) : startPolling recoit l'ID de l'ancien plan pour eviter
// que le polling stoppe immediatement sur le plan stale encore en cache.
export function useGeneratePlan(startPolling?: (currentPlanId?: string | null) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params?: GeneratePlanParams) => generatePlan(params),
    onSuccess: (_data, _variables, _context) => {
      // Recuperer l'ID du plan actuellement en cache AVANT d'invalider.
      // On passe cet ID a startPolling pour que le useEffect de useCurrentPlan
      // sache qu'il doit attendre un plan DIFFERENT (et non s'arreter sur le stale cache).
      const cachedPlan = queryClient.getQueryData<PlanDetail | null>(PLAN_QUERY_KEYS.current);
      const previousId = cachedPlan?.id ?? null;

      // Invalider le cache pour forcer un refetch au prochain poll
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      // Demarrer le polling conditionnel (toutes les 3s, timeout 60s)
      startPolling?.(previousId);
      toast.info("Generation en cours...", {
        description: "Votre planning sera pret dans quelques secondes.",
      });
    },
    onError: (err: Error) => {
      // Le client API affiche deja un toast pour les erreurs HTTP
      // Afficher seulement les erreurs non-HTTP
      if (!err.message.includes("Erreur API")) {
        toast.error("Generation impossible", {
          description: err.message,
        });
      }
    },
  });
}

// Mutation — Swapper une recette dans le plan (PATCH /api/v1/plans/{id}/meals/{meal_id})
export function useSwapMeal(planId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ mealId, recipeId }: { mealId: string; recipeId: string }) =>
      swapMeal(planId, mealId, recipeId),
    // Optimistic update — mettre à jour le cache localement avant la réponse serveur
    onMutate: async ({ mealId, recipeId }) => {
      await queryClient.cancelQueries({ queryKey: PLAN_QUERY_KEYS.current });
      const previousPlan = queryClient.getQueryData<PlanDetail>(PLAN_QUERY_KEYS.current);

      if (previousPlan) {
        queryClient.setQueryData<PlanDetail>(PLAN_QUERY_KEYS.current, (old) => {
          if (!old) return old;
          // FIX Phase 1 mature (review 2026-04-12) — Mismatch D : champ `meals` aligné sur backend
          return {
            ...old,
            meals: old.meals.map((meal) =>
              meal.id === mealId ? { ...meal, recipe_id: recipeId } : meal,
            ),
          };
        });
      }

      return { previousPlan };
    },
    onError: (err: Error, _variables, context) => {
      // Rollback en cas d'erreur
      if (context?.previousPlan) {
        queryClient.setQueryData(PLAN_QUERY_KEYS.current, context.previousPlan);
      }
      toast.error("Remplacement impossible", { description: err.message });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Recette remplacee !");
    },
  });
}

// Mutation — Ajouter un repas au plan (POST /api/v1/plans/{plan_id}/meals/add)
// Utilise pour ajouter samedi/dimanche
export function useAddMeal(planId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ dayOfWeek, recipeId }: { dayOfWeek: number; recipeId: string }) =>
      addMealToPlan(planId, dayOfWeek, recipeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Repas ajoute !");
    },
    onError: (err: Error) => {
      toast.error("Ajout impossible", { description: err.message });
    },
  });
}

// Query — Suggestions de recettes pour swap/ajout
// GET /api/v1/plans/{plan_id}/suggestions?style=...&max_time=...
export function useRecipeSuggestions(
  planId: string,
  filters?: { style?: string; max_time?: number },
  enabled = true,
) {
  return useQuery<Recipe[], Error>({
    queryKey: PLAN_QUERY_KEYS.suggestions(planId, filters),
    queryFn: () => getRecipeSuggestions(planId, filters),
    enabled: enabled && !!planId,
    staleTime: 30 * 1000, // 30 secondes — suggestions fraiches a chaque ouverture
  });
}

// Mutation — Valider le plan (POST /api/v1/plans/{id}/validate)
export function useValidatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: validatePlan,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Plan valide !", {
        description: "Liste de courses generee.",
      });
    },
    onError: (err: Error) => {
      toast.error("Validation impossible", { description: err.message });
    },
  });
}

// Mutation — Repasser en draft (POST /api/v1/plans/{id}/revert-to-draft)
export function useRevertToDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: revertPlanToDraft,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Plan remis en brouillon.", {
        description: "Vous pouvez maintenant modifier ou regenerer.",
      });
    },
    onError: (err: Error) => {
      toast.error("Impossible de modifier le plan", { description: err.message });
    },
  });
}
