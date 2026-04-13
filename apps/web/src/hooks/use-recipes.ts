// apps/web/src/hooks/use-recipes.ts
// Hooks TanStack Query pour les recettes
// Couvre : recette par ID, recherche, notation
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRecipe, searchRecipes, createFeedback } from "@/lib/api/endpoints";
import type { RecipeSearchParams, FeedbackCreate } from "@/lib/api/endpoints";
import type { Recipe } from "@/lib/api/types";
import { toast } from "sonner";

export const RECIPE_QUERY_KEYS = {
  byId: (id: string) => ["recipes", id] as const,
  search: (params: RecipeSearchParams) => ["recipes", "search", params] as const,
};

// Hook — Recette par ID (GET /api/v1/recipes/{id})
export function useRecipe(id: string | null) {
  return useQuery<Recipe, Error>({
    queryKey: RECIPE_QUERY_KEYS.byId(id ?? ""),
    queryFn: () => {
      if (!id) throw new Error("Recipe ID requis");
      return getRecipe(id);
    },
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutes — les recettes changent rarement
  });
}

// Hook — Recherche de recettes (GET /api/v1/recipes/search)
export function useRecipeSearch(params: RecipeSearchParams) {
  return useQuery<Recipe[], Error>({
    queryKey: RECIPE_QUERY_KEYS.search(params),
    queryFn: () => searchRecipes(params),
    // Activer seulement si au moins un paramètre de recherche est défini
    enabled: Object.values(params).some((v) => v !== undefined && v !== ""),
    staleTime: 5 * 60 * 1000, // 5 minutes
    placeholderData: [],
  });
}

// Mutation — Noter une recette (POST /api/v1/feedbacks)
export function useRateRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FeedbackCreate) => createFeedback(data),
    onSuccess: (_result, variables) => {
      // Invalider le cache de la recette pour mettre à jour le rating affiché
      void queryClient.invalidateQueries({
        queryKey: RECIPE_QUERY_KEYS.byId(variables.recipe_id),
      });
      toast.success("Merci pour votre retour !", {
        description: "Votre note améliore vos prochaines recettes.",
        duration: 5000,
      });
    },
    onError: (err: Error) => {
      toast.error("Impossible d'enregistrer la note", { description: err.message });
    },
  });
}
