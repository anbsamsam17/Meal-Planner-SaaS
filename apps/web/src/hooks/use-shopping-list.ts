// apps/web/src/hooks/use-shopping-list.ts
// Hooks TanStack Query pour la liste de courses
// Optimistic update sur toggle + persistance localStorage
// Phase 2 : sync via Supabase Realtime pour partage famille en temps reel
"use client";

import { useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getShoppingList } from "@/lib/api/endpoints";
import type { ShoppingListItem } from "@/lib/api/types";

export const SHOPPING_QUERY_KEYS = {
  byPlan: (planId: string) => ["shopping-list", planId] as const,
};

const STORAGE_KEY_PREFIX = "presto-shopping-checked";

function getStorageKey(planId: string): string {
  return `${STORAGE_KEY_PREFIX}-${planId}`;
}

/** Charge les IDs coches depuis localStorage pour un plan donne */
function loadCheckedItems(planId: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const saved = localStorage.getItem(getStorageKey(planId));
    if (saved) {
      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        return new Set(parsed.filter((v): v is string => typeof v === "string"));
      }
    }
  } catch {
    // localStorage corrompu -- repartir de zero
  }
  return new Set();
}

/** Sauvegarde les IDs coches dans localStorage */
function saveCheckedItems(planId: string, checkedIds: string[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getStorageKey(planId), JSON.stringify(checkedIds));
  } catch {
    // Quota localStorage depasse -- pas critique
  }
}

// Hook -- Liste de courses pour un plan donne
// Hydrate les items avec l'etat coche depuis localStorage
export function useShoppingList(planId: string | null) {
  const queryClient = useQueryClient();

  const query = useQuery<ShoppingListItem[], Error>({
    queryKey: SHOPPING_QUERY_KEYS.byPlan(planId ?? ""),
    queryFn: () => {
      if (!planId) throw new Error("Plan ID requis");
      return getShoppingList(planId);
    },
    enabled: !!planId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Apres le fetch initial, hydrater is_checked depuis localStorage
  const hydrateFromStorage = useCallback(() => {
    if (!planId || !query.data) return;
    const checkedSet = loadCheckedItems(planId);
    if (checkedSet.size === 0) return;

    const needsUpdate = query.data.some(
      (item) => checkedSet.has(item.id) !== item.is_checked,
    );
    if (!needsUpdate) return;

    queryClient.setQueryData<ShoppingListItem[]>(
      SHOPPING_QUERY_KEYS.byPlan(planId),
      (old) => {
        if (!old) return old;
        return old.map((item) =>
          checkedSet.has(item.id) ? { ...item, is_checked: true } : item,
        );
      },
    );
  }, [planId, query.data, queryClient]);

  useEffect(() => {
    hydrateFromStorage();
  }, [hydrateFromStorage]);

  return query;
}

// Mutation -- Toggle item coche (optimistic update + persistance localStorage)
// Phase 2 : PATCH /api/v1/plans/{planId}/shopping-list/{itemId}
export function useToggleItem(planId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemId, isChecked }: { itemId: string; isChecked: boolean }) => {
      // Phase 1 -- persistance localStorage uniquement (pas de endpoint API pour le check)
      // Phase 2 : PATCH /api/v1/plans/{planId}/shopping-list/{itemId}
      return { itemId, isChecked };
    },
    // Optimistic update immediat -- pas d'attente serveur
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
    onSuccess: () => {
      // Persister l'etat coche dans localStorage
      const items = queryClient.getQueryData<ShoppingListItem[]>(
        SHOPPING_QUERY_KEYS.byPlan(planId),
      );
      if (items) {
        const checkedIds = items
          .filter((item) => item.is_checked)
          .map((item) => item.id);
        saveCheckedItems(planId, checkedIds);
      }
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
