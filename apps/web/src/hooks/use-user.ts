// apps/web/src/hooks/use-user.ts
// Hook TanStack Query — récupère l'utilisateur courant Supabase
// Invalidé automatiquement sur changement d'état auth (onAuthStateChange)
// Usage côté client uniquement — utiliser createServerClient() dans les RSC
"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { User } from "@supabase/supabase-js";
import { createBrowserClient } from "@/lib/supabase/client";

// Clé de requête stable pour le cache TanStack Query
export const USER_QUERY_KEY = ["auth", "user"] as const;

interface UseUserResult {
  user: User | null;
  loading: boolean;
  error: Error | null;
}

export function useUser(): UseUserResult {
  const queryClient = useQueryClient();
  const supabase = createBrowserClient();

  // Écouter les changements d'état auth et invalider le cache automatiquement
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      // Mettre à jour directement le cache plutôt que d'invalider + refetch
      queryClient.setQueryData(USER_QUERY_KEY, session?.user ?? null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase, queryClient]);

  const { data: user, isLoading, error } = useQuery<User | null, Error>({
    queryKey: USER_QUERY_KEY,
    queryFn: async () => {
      // getUser() vérifie le token auprès du serveur Supabase (plus sûr que getSession())
      const { data: { user: currentUser }, error: authError } = await supabase.auth.getUser();

      if (authError) {
        // Utilisateur non authentifié — retourner null (pas une erreur critique)
        if (authError.message.includes("Auth session missing")) {
          return null;
        }
        throw new Error(authError.message);
      }

      return currentUser;
    },
    // Session stable — pas besoin de refetch fréquent
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Pas de retry sur les erreurs auth
  });

  return {
    user: user ?? null,
    loading: isLoading,
    error: error ?? null,
  };
}
