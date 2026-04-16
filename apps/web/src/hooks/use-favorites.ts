// apps/web/src/hooks/use-favorites.ts
// Hooks TanStack Query pour la gestion des recettes favorites
// - useFavoriteRecipes : GET /api/v1/feedbacks/me/favorites (paginé)
// - useToggleFavorite  : POST /api/v1/feedbacks (feedback_type='favorited')
// - useIsFavorite      : check local depuis le cache des favoris
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getFavoriteRecipes, createFeedback } from "@/lib/api/endpoints";
import type { PaginatedResponse } from "@/lib/api/types";
import type { Recipe } from "@/lib/api/types";
import { toast } from "sonner";

// Clés de cache centralisées — évite les collisions avec les autres hooks
export const FAVORITES_QUERY_KEYS = {
  all: ["favorites"] as const,
  list: (page: number) => ["favorites", "list", page] as const,
};

// ---- Hook : récupérer les recettes favorites (paginées) ----

export function useFavoriteRecipes(page = 1) {
  return useQuery<PaginatedResponse<Recipe>, Error>({
    queryKey: FAVORITES_QUERY_KEYS.list(page),
    queryFn: () => getFavoriteRecipes(page),
    staleTime: 2 * 60 * 1000, // 2 minutes — les favoris changent peu fréquemment
    placeholderData: (previousData) => previousData,
  });
}

// ---- Hook : vérifier si une recette est en favori ----
// Lit depuis le cache de la page 1 (sans refetch réseau supplémentaire)
// Retourne undefined si le cache n'est pas encore chargé

export function useIsFavorite(recipeId: string): boolean {
  const queryClient = useQueryClient();

  // Chercher dans toutes les pages cachées
  const cachedQueries = queryClient.getQueriesData<PaginatedResponse<Recipe>>({
    queryKey: FAVORITES_QUERY_KEYS.all,
  });

  for (const [, data] of cachedQueries) {
    if (data?.data?.some((r) => r.id === recipeId)) {
      return true;
    }
  }

  return false;
}

// ---- Hook : ajouter / retirer un favori ----

export function useToggleFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      recipeId,
      isFavorite,
    }: {
      recipeId: string;
      isFavorite: boolean;
    }) => {
      if (isFavorite) {
        // Le favori existe déjà — on "retire" en envoyant un feedback 'cooked'
        // (pas d'endpoint DELETE — on laisse le statut existant inchangé)
        // NOTE : l'API ne propose pas de suppression de favori en Phase 1.
        // Le toggle visuel est géré côté client uniquement pour l'instant.
        // En Phase 2 : implémenter DELETE /feedbacks/{id} avec audit_log.
        return null;
      }
      // Ajout du favori via POST /feedbacks
      return createFeedback({
        recipe_id: recipeId,
        feedback_type: "favorited",
        rating: 5, // Les favoris ont toujours 5 étoiles implicitement
        notes: null,
      });
    },
    onSuccess: (_result, variables) => {
      if (!variables.isFavorite) {
        // Invalider le cache des favoris pour forcer un rechargement
        void queryClient.invalidateQueries({
          queryKey: FAVORITES_QUERY_KEYS.all,
        });
        toast.success("Recette ajoutée aux favoris", {
          description: "Retrouvez-la dans l'onglet Mes Favoris.",
          duration: 3000,
        });
      } else {
        // Phase 1 : suppression non supportée côté API
        toast.info("Favori retiré visuellement", {
          description: "La suppression définitive sera disponible prochainement.",
          duration: 3000,
        });
      }
    },
    onError: (err: Error) => {
      toast.error("Impossible de modifier les favoris", { description: err.message });
    },
  });
}
