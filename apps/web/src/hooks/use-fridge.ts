"use client";
// apps/web/src/hooks/use-fridge.ts
// Hooks TanStack Query pour la gestion du frigo
// Phase 2 — GET /fridge, POST /fridge, DELETE /fridge/{id}, POST /fridge/suggest-recipes

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getFridge,
  addFridgeItem,
  removeFridgeItem,
  getFridgeSuggestions,
} from "@/lib/api/endpoints";
import type { FridgeItem, FridgeItemCreate, FridgeSuggestionsResponse } from "@/lib/api/types";
import { toast } from "sonner";

export const FRIDGE_QUERY_KEYS = {
  items: ["fridge", "items"] as const,
  suggestions: ["fridge", "suggestions"] as const,
};

// Hook — Liste des items du frigo (GET /api/v1/fridge)
export function useFridge() {
  return useQuery<FridgeItem[], Error>({
    queryKey: FRIDGE_QUERY_KEYS.items,
    queryFn: getFridge,
    staleTime: 60 * 1000, // 1 minute
  });
}

// Mutation — Ajouter un item au frigo (POST /api/v1/fridge)
export function useAddFridgeItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FridgeItemCreate) => addFridgeItem(data),
    onSuccess: (newItem) => {
      // Mise à jour optimiste du cache
      queryClient.setQueryData<FridgeItem[]>(FRIDGE_QUERY_KEYS.items, (prev = []) => [
        ...prev,
        newItem,
      ]);
      toast.success("Produit ajouté au frigo");
    },
    onError: (err: Error) => {
      toast.error("Impossible d'ajouter le produit", { description: err.message });
    },
  });
}

// Mutation — Supprimer un item du frigo (DELETE /api/v1/fridge/{id})
export function useRemoveFridgeItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => removeFridgeItem(id),
    onMutate: async (id: string) => {
      // Annuler les refetch en cours pour éviter les conflits
      await queryClient.cancelQueries({ queryKey: FRIDGE_QUERY_KEYS.items });

      // Snapshot pour rollback si besoin
      const previousItems = queryClient.getQueryData<FridgeItem[]>(FRIDGE_QUERY_KEYS.items);

      // Mise à jour optimiste — retirer l'item immédiatement
      queryClient.setQueryData<FridgeItem[]>(FRIDGE_QUERY_KEYS.items, (prev = []) =>
        prev.filter((item) => item.id !== id),
      );

      return { previousItems };
    },
    onError: (err: Error, _id, context) => {
      // Rollback en cas d'erreur
      if (context?.previousItems) {
        queryClient.setQueryData(FRIDGE_QUERY_KEYS.items, context.previousItems);
      }
      toast.error("Impossible de supprimer le produit", { description: err.message });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: FRIDGE_QUERY_KEYS.items });
    },
  });
}

// Mutation — Suggestions recettes basées sur le contenu du frigo
// (POST /api/v1/fridge/suggest-recipes)
export function useFridgeSuggestions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: getFridgeSuggestions,
    onSuccess: (data: FridgeSuggestionsResponse) => {
      // Stocker les suggestions dans le cache pour lecture immédiate
      queryClient.setQueryData(FRIDGE_QUERY_KEYS.suggestions, data);
      toast.success(`${data.recipes.length} recette(s) trouvée(s) avec vos ingrédients !`);
    },
    onError: (err: Error) => {
      toast.error("Impossible de générer des suggestions", { description: err.message });
    },
  });
}
