// apps/web/src/hooks/use-household.ts
// Hook TanStack Query — récupère le household de l'utilisateur courant
// Cache 5 minutes — invalidé après modification (onboarding submit, préférences)
// Endpoint : GET /api/v1/households/me
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { Household } from "@/lib/api/types";

// Types API étendus pour aligner avec les contrats backend Phase 1
export interface HouseholdResponse {
  household: Household;
  members: HouseholdMember[];
  preferences: HouseholdPreferences | null;
}

export interface HouseholdMember {
  id: string;
  display_name: string;
  is_child: boolean;
  birth_date: string | null;
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
}

export interface HouseholdPreferences {
  cooking_time_max: number;
  // BUG 5/6 FIX (2026-04-12) : aligné sur l'enum FR du backend (Mismatch C)
  // Référence : endpoints.ts HouseholdPreferencesAPI.budget_pref
  budget_pref: "économique" | "moyen" | "premium" | null;
  drive_provider: string | null;
}

// Clé de requête pour le cache
export const HOUSEHOLD_QUERY_KEY = ["household", "me"] as const;

interface UseHouseholdResult {
  household: HouseholdResponse | null;
  loading: boolean;
  error: Error | null;
  hasHousehold: boolean;
}

export function useHousehold(): UseHouseholdResult {
  const { data, isLoading, error } = useQuery<HouseholdResponse | null, Error>({
    queryKey: HOUSEHOLD_QUERY_KEY,
    queryFn: async () => {
      try {
        return await apiClient.get<HouseholdResponse>("/api/v1/households/me");
      } catch (err) {
        // 404 = pas de household → retourner null (état valide pour onboarding)
        if (err instanceof Error && err.message.includes("404")) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, err) => {
      // Ne pas retenter sur les 4xx (erreurs client)
      if (err.message.includes("401") || err.message.includes("403")) return false;
      return failureCount < 2;
    },
  });

  return {
    household: data ?? null,
    loading: isLoading,
    error: error ?? null,
    hasHousehold: data !== null && data !== undefined,
  };
}
