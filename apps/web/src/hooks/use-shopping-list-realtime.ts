// apps/web/src/hooks/use-shopping-list-realtime.ts
// Subscribe au channel Supabase Realtime pour les changements shopping list
// Invalide le cache TanStack Query sur UPDATE pour synchro multi-device
"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase/client";
import { SHOPPING_QUERY_KEYS } from "@/hooks/use-shopping-list";

/**
 * Subscribe aux changements realtime de la shopping list d'un plan.
 * Sur chaque UPDATE de la table shopping_lists, invalide le cache TanStack Query
 * pour declencher un refetch.
 *
 * Cleanup propre sur unmount (removeChannel).
 *
 * @param planId - UUID du plan (null = pas d'abonnement)
 */
export function useShoppingListRealtime(planId: string | null) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!planId) return;

    const supabase = createBrowserClient();

    const channel = supabase
      .channel(`shopping-list:${planId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "shopping_lists",
          filter: `plan_id=eq.${planId}`,
        },
        () => {
          // Invalider le cache pour déclencher un refetch
          void queryClient.invalidateQueries({
            queryKey: SHOPPING_QUERY_KEYS.byPlan(planId),
          });
        },
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [planId, queryClient]);
}
