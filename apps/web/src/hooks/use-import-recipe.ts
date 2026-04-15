// apps/web/src/hooks/use-import-recipe.ts
// Hook TanStack Query pour l'import de recette depuis URL
// POST /api/v1/recipes/import-url → polling résultat
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { importRecipeFromUrl } from "@/lib/api/endpoints";
import type { ImportUrlResponse } from "@/lib/api/types";
import { toast } from "sonner";

export function useImportRecipe() {
  const queryClient = useQueryClient();

  return useMutation<ImportUrlResponse, Error, string>({
    mutationFn: (url: string) => importRecipeFromUrl(url),
    onSuccess: () => {
      // Invalider le cache des recettes pour que la nouvelle apparaisse
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
      toast.success("Recette importée avec succès !", {
        description: "Elle sera disponible dans quelques secondes.",
        duration: 5000,
      });
    },
    onError: (err: Error) => {
      const message = err.message.includes("429")
        ? "Limite atteinte — max 10 imports par heure."
        : err.message.includes("422")
          ? "URL invalide. Vérifiez le lien et réessayez."
          : "Impossible d'importer cette recette. Vérifiez l'URL.";
      toast.error("Échec de l'import", { description: message });
    },
  });
}
