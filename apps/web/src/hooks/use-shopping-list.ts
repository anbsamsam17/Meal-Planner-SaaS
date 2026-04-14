// apps/web/src/hooks/use-shopping-list.ts
// Hooks TanStack Query pour la liste de courses
// Optimistic update sur toggle + persistance backend via PATCH
// REC-04 : items cochés persistés côté serveur (shopping_lists.items[].checked)
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getShoppingList } from "@/lib/api/endpoints";
import { apiClient } from "@/lib/api/client";
import type { ShoppingListItem } from "@/lib/api/types";

export const SHOPPING_QUERY_KEYS = {
  byPlan: (planId: string) => ["shopping-list", planId] as const,
};

// Hook -- Liste de courses pour un plan donne
// L'etat checked est persiste cote serveur — pas de localStorage
// REC-04 : le backend retourne les items avec leur etat checked reel
export function useShoppingList(planId: string | null) {
  const query = useQuery<ShoppingListItem[], Error>({
    queryKey: SHOPPING_QUERY_KEYS.byPlan(planId ?? ""),
    queryFn: () => {
      if (!planId) throw new Error("Plan ID requis");
      return getShoppingList(planId);
    },
    enabled: !!planId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return query;
}

// Mutation -- Toggle item coche (optimistic update + persistance backend)
// REC-04 : PATCH /api/v1/plans/me/{planId}/shopping-list/{ingredientId}
// L'ingredient_id est utilise comme cle naturelle cote backend (champ dans le JSON items[])
export function useToggleItem(planId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, isChecked }: { itemId: string; isChecked: boolean }) => {
      // itemId = ingredient_id (cle naturelle dans shopping_lists.items[].ingredient_id)
      await apiClient.patch(
        `/api/v1/plans/me/${planId}/shopping-list/${itemId}`,
        { checked: isChecked },
      );
      return { itemId, isChecked };
    },
    // Optimistic update immediat -- la reponse serveur confirme l'etat final
    onMutate: async ({ itemId, isChecked }) => {
      const queryKey = SHOPPING_QUERY_KEYS.byPlan(planId);
      await queryClient.cancelQueries({ queryKey });

      const previousItems = queryClient.getQueryData<ShoppingListItem[]>(queryKey);

      queryClient.setQueryData<ShoppingListItem[]>(queryKey, (old) => {
        if (!old) return old;
        return old.map((item) =>
          item.id === itemId ? { ...item, is_checked: isChecked } : item,
        );
      });

      return { previousItems };
    },
    onError: (_err, _variables, context) => {
      // Rollback en cas d'erreur reseau ou serveur
      if (context?.previousItems) {
        queryClient.setQueryData(
          SHOPPING_QUERY_KEYS.byPlan(planId),
          context.previousItems,
        );
      }
    },
  });
}
