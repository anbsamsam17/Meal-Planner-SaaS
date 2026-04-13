// apps/web/src/hooks/use-plan.ts
// Hooks TanStack Query pour les plans hebdomadaires
// Couvre : plan courant, plan par ID, generation, swap recette, ajout repas, suggestions
// FIX BLOQUANT 2 (2026-04-12) : polling conditionnel apres generation asynchrone (Celery)
// Refonte dashboard (2026-04-12) : filtres generation, suggestions, ajout repas samedi/dimanche
"use client";

import { useState } from "react";
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

// Hook — Plan courant (GET /api/v1/plans/me/current)
// La generation est SYNCHRONE (200 OK) — pas besoin de polling.
// Apres generate, on fait un simple refetch pour recuperer le nouveau plan.
export function useCurrentPlan() {
  const [isGenerating, setIsGenerating] = useState(false);

  const query = useQuery<PlanDetail | null, Error>({
    queryKey: PLAN_QUERY_KEYS.current,
    queryFn: async () => {
      try {
        return await getCurrentPlan();
      } catch (err) {
        if (err instanceof Error && err.message.includes("404")) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 2 * 60 * 1000,
    retry: (failureCount, err) => {
      if (err.message.includes("401") || err.message.includes("403")) return false;
      return failureCount < 2;
    },
  });

  return { ...query, isGenerating, setIsGenerating };
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
// La generation backend est SYNCHRONE (200 OK) — pas de Celery.
// Apres succes, on vide le cache et refetch pour afficher le nouveau plan.
export function useGeneratePlan(setIsGenerating?: (v: boolean) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params?: GeneratePlanParams) => generatePlan(params),
    onMutate: () => {
      setIsGenerating?.(true);
    },
    onSuccess: async () => {
      // Le backend a cree le nouveau plan (synchrone, 200 OK).
      // invalidateQueries force un refetch reseau et met a jour le cache
      // sans creer de fenetre ou planDetail serait null (evite le fallback SSR).
      await queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      setIsGenerating?.(false);
      toast.success("Votre planning est pret !");
    },
    onError: (err: Error) => {
      setIsGenerating?.(false);
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
