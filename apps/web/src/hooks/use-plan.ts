// apps/web/src/hooks/use-plan.ts
// Hooks TanStack Query pour les plans hebdomadaires
// Couvre : plan courant, plan par ID, génération, swap recette
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCurrentPlan,
  getPlan,
  generatePlan,
  swapMeal,
  validatePlan,
} from "@/lib/api/endpoints";
import type { PlanDetail } from "@/lib/api/endpoints";
import { toast } from "sonner";

// Clés de requête stables
export const PLAN_QUERY_KEYS = {
  current: ["plans", "current"] as const,
  byId: (id: string) => ["plans", id] as const,
};

// Hook — Plan courant (GET /api/v1/plans/me/current)
export function useCurrentPlan() {
  return useQuery<PlanDetail | null, Error>({
    queryKey: PLAN_QUERY_KEYS.current,
    queryFn: async () => {
      try {
        return await getCurrentPlan();
      } catch (err) {
        // 404 = pas de plan pour la semaine → état valide, retourner null
        if (err instanceof Error && err.message.includes("404")) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: (failureCount, err) => {
      if (err.message.includes("401") || err.message.includes("403")) return false;
      return failureCount < 2;
    },
  });
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

// Mutation — Générer un nouveau plan (POST /api/v1/plans/generate)
export function useGeneratePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: generatePlan,
    onSuccess: () => {
      // Invalider le cache du plan courant pour forcer un re-fetch
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Plan généré !", {
        description: "Votre planning de la semaine est prêt.",
      });
    },
    onError: (err: Error) => {
      // Le client API affiche déjà un toast pour les erreurs HTTP
      // Afficher seulement les erreurs non-HTTP
      if (!err.message.includes("Erreur API")) {
        toast.error("Génération impossible", {
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
      toast.success("Recette remplacée !");
    },
  });
}

// Mutation — Valider le plan (POST /api/v1/plans/{id}/validate)
export function useValidatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: validatePlan,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      toast.success("Plan validé !", {
        description: "Vos courses sont prêtes à être préparées.",
      });
    },
    onError: (err: Error) => {
      toast.error("Validation impossible", { description: err.message });
    },
  });
}
