// apps/web/src/hooks/use-shopping-list.ts
// Hooks TanStack Query pour la liste de courses
// Optimistic update sur toggle — sans Supabase Realtime (Phase 2)
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getShoppingList } from "@/lib/api/endpoints";
import type { ShoppingListItem } from "@/lib/api/types";

export const SHOPPING_QUERY_KEYS = {
  byPlan: (planId: string) => ["shopping-list", planId] as const,
};

// Hook — Liste de courses pour un plan donné
export function useShoppingList(planId: string | null) {
  return useQuery<ShoppingListItem[], Error>({
    queryKey: SHOPPING_QUERY_KEYS.byPlan(planId ?? ""),
    queryFn: () => {
      if (!planId) throw new Error("Plan ID requis");
      return getShoppingList(planId);
    },
    enabled: !!planId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Mutation — Toggle item checké (optimistic update, state local en Phase 1)
// En Phase 2 : sync via Supabase Realtime pour partage famille en temps réel
export function useToggleItem(planId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, isChecked }: { itemId: string; isChecked: boolean }) => {
      // Phase 1 — mise à jour locale uniquement (pas de endpoint API pour le check)
      // Phase 2 : PATCH /api/v1/plans/{planId}/shopping-list/{itemId}
      // Simuler une réponse succès
      return { itemId, isChecked };
    },
    // Optimistic update immédiat — pas d'attente serveur
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
      // Rollback en cas d'erreur
      if (context?.previousItems) {
        queryClient.setQueryData(
          SHOPPING_QUERY_KEYS.byPlan(planId),
          context.previousItems,
        );
      }
    },
  });
}
