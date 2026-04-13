// apps/web/src/hooks/use-plan.ts
// Hooks TanStack Query pour les plans hebdomadaires
// Couvre : plan courant, plan par ID, generation, swap recette
// FIX BLOQUANT 2 (2026-04-12) : polling conditionnel apres generation asynchrone (Celery)
"use client";

import { useState, useEffect, useRef } from "react";
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

// Cles de requete stables
export const PLAN_QUERY_KEYS = {
  current: ["plans", "current"] as const,
  byId: (id: string) => ["plans", id] as const,
};

// Timeout max pour le polling (60 secondes)
const POLLING_INTERVAL_MS = 3_000;
const POLLING_TIMEOUT_MS = 60_000;

// Hook — Plan courant (GET /api/v1/plans/me/current)
// FIX BLOQUANT 2 : polling conditionnel toutes les 3s pendant la generation, timeout 60s
export function useCurrentPlan() {
  const [isGenerating, setIsGenerating] = useState(false);
  const pollingStartRef = useRef<number>(0);

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

  // Arreter le polling quand un plan est trouve OU timeout depasse
  useEffect(() => {
    if (!isGenerating) return;

    // Plan trouve pendant le polling → succes
    if (query.data) {
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

  // Demarrer le polling (appele depuis useGeneratePlan)
  const startPolling = () => {
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
// FIX BLOQUANT 2 : apres le 202, on declenche le polling via startPolling()
// Le toast de succes est affiche par useCurrentPlan quand le plan arrive.
export function useGeneratePlan(startPolling?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: generatePlan,
    onSuccess: () => {
      // Invalider le cache pour que le prochain poll demarre avec un etat frais
      void queryClient.invalidateQueries({ queryKey: PLAN_QUERY_KEYS.current });
      // Demarrer le polling conditionnel (toutes les 3s, timeout 60s)
      startPolling?.();
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
