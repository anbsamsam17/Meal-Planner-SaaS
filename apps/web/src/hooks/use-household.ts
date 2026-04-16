// apps/web/src/hooks/use-household.ts
// Hook TanStack Query — récupère le household de l'utilisateur courant
// Cache 5 minutes — invalidé après modification (onboarding submit, préférences)
// Endpoint : GET /api/v1/households/me
// REC-05 : normalise la réponse API (HouseholdRead) vers HouseholdResponse
//   - extrait les prefs du membre owner vers HouseholdResponse.preferences
//   - aplatit diet_tags/allergies/dislikes sur chaque HouseholdMember
//   - expose household.household.drive_provider depuis households.plan ou null
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

// ---- Types API raw (ce que le backend retourne) ----

interface MemberPreferenceRaw {
  id: string;
  member_id: string;
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
  cooking_time_max: number | null;
  budget_pref: string | null;
  created_at: string;
  updated_at: string;
}

interface MemberRaw {
  id: string;
  household_id: string;
  display_name: string;
  is_child: boolean;
  role: string;
  birth_date: string | null;
  created_at: string;
  preferences: MemberPreferenceRaw | null;
}

interface HouseholdRaw {
  id: string;
  name: string;
  plan: string;
  drive_provider: string | null;
  created_at: string;
  updated_at: string;
  members: MemberRaw[];
}

// ---- Types normalisés exposés aux composants ----

export interface HouseholdMember {
  id: string;
  display_name: string;
  is_child: boolean;
  birth_date: string | null;
  role: string;
  // Aplati depuis member.preferences pour l'accès direct dans settings-content
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
}

export interface HouseholdPreferences {
  cooking_time_max: number;
  budget_pref: "économique" | "moyen" | "premium" | null;
  drive_provider: string | null;
}

export interface HouseholdInfo {
  id: string;
  name: string;
  plan: string;
  drive_provider: string | null;
  created_at: string;
  updated_at: string;
}

export interface HouseholdResponse {
  // Sous-objet info foyer (accédé dans settings via household.household.drive_provider)
  household: HouseholdInfo;
  members: HouseholdMember[];
  // Préférences du membre owner (agrégées depuis members[].preferences)
  preferences: HouseholdPreferences | null;
}

// ---- Normalisation ----

function normalizeHousehold(raw: HouseholdRaw): HouseholdResponse {
  // Trouver le membre owner (premier non-enfant ou premier de la liste)
  const ownerRaw = raw.members.find((m) => m.role === "owner") ?? raw.members[0] ?? null;
  const ownerPrefs = ownerRaw?.preferences ?? null;

  const preferences: HouseholdPreferences | null = ownerPrefs
    ? {
        cooking_time_max: ownerPrefs.cooking_time_max ?? 45,
        budget_pref: (ownerPrefs.budget_pref as HouseholdPreferences["budget_pref"]) ?? null,
        // drive_provider est sur le foyer (raw.drive_provider), pas sur les prefs membre
        drive_provider: raw.drive_provider ?? null,
      }
    : null;

  const members: HouseholdMember[] = raw.members.map((m) => ({
    id: String(m.id),
    display_name: m.display_name,
    is_child: m.is_child,
    birth_date: m.birth_date,
    role: m.role,
    // Aplatir les prefs — fallback sur tableau vide si prefs absentes
    diet_tags: m.preferences?.diet_tags ?? [],
    allergies: m.preferences?.allergies ?? [],
    dislikes: m.preferences?.dislikes ?? [],
  }));

  return {
    household: {
      id: String(raw.id),
      name: raw.name,
      plan: raw.plan,
      drive_provider: raw.drive_provider ?? null,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
    },
    members,
    preferences,
  };
}

// ---- Clé de requête ----

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
        const raw = await apiClient.get<HouseholdRaw>("/api/v1/households/me");
        return normalizeHousehold(raw);
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
