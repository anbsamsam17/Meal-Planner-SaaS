// apps/web/src/components/providers/query-provider.tsx
// TanStack Query v5 — configuration pour le food content
// staleTime 5 minutes : les recettes ne changent pas fréquemment
// gcTime 10 minutes : garder les données en cache mémoire plus longtemps
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

interface QueryProviderProps {
  children: React.ReactNode;
}

// Créer le QueryClient à l'intérieur du composant pour éviter les fuites de données
// entre les requêtes serveur (important avec SSR/Next.js)
export function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 5 minutes — sensé pour les recettes (données relativement stables)
            staleTime: 5 * 60 * 1000,
            // 10 minutes en mémoire après que le composant soit démonté
            gcTime: 10 * 60 * 1000,
            // Retry 1 fois en cas d'erreur (évite les cascades d'erreurs)
            retry: 1,
            // Ne pas refetch automatiquement au focus de la fenêtre pour le food content
            // (les recettes ne changent pas en temps réel, contrairement aux stocks)
            refetchOnWindowFocus: false,
          },
          mutations: {
            // Retry 0 fois pour les mutations — l'utilisateur doit réessayer explicitement
            retry: 0,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Devtools uniquement en développement */}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
