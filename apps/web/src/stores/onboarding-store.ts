// apps/web/src/stores/onboarding-store.ts
// Zustand store — état global de l'onboarding 3 étapes
// Persisté en localStorage via zustand/middleware/persist (reprise après refresh)
// Référence : onboarding-protocol.md — cible < 90s pour les 3 étapes
// FIX Phase 1 mature (review 2026-04-12) :
//   BUG #2 — polling corrigé vers /plans/me/current (était sur /plans/{taskId} → 404 systématique)
//   BUG #4 — submit() idempotent avec détection household existant avant création
"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { apiClient, ApiRequestError } from "@/lib/api/client";
import { getCurrentMonday } from "@/lib/api/endpoints";
import { toast } from "sonner";

// --- Types ---

export type ChildAgeRange = "0-2" | "3-6" | "7-12" | "13+";
export type CookingTimeMax = 20 | 40 | 60;
export type DriveProvider =
  | "leclerc"
  | "auchan"
  | "carrefour"
  | "intermarche"
  | "none";

export type OnboardingStep = 1 | 2 | 3 | "generating" | "done";

interface Step1Data {
  adultsCount: number;
  childrenCount: number;
  childrenAges: ChildAgeRange[];
}

interface Step2Data {
  dietTags: string[];
  allergies: string[];
}

interface Step3Data {
  cookingTimeMax: CookingTimeMax;
  driveProvider: DriveProvider;
}

// Réponses API — alignées sur les contrats backend Phase 1
interface HouseholdCreateResponse {
  household: { id: string; name: string };
  members: Array<{ id: string; display_name: string; is_child: boolean }>;
}

interface GeneratePlanResponse {
  task_id: string;
}

// FIX Phase 1 mature (review 2026-04-12) — BUG #2 : status "draft"/"validated" du plan réel
// (pas le status Celery — le polling se fait sur /plans/me/current)
interface PlanCurrentResponse {
  id: string;
  status: "draft" | "validated" | "generating" | "failed";
}

// --- État complet du store ---

interface OnboardingState {
  currentStep: OnboardingStep;
  generatedTaskId: string | null;

  // Step 1 — Famille
  adultsCount: number;
  childrenCount: number;
  childrenAges: ChildAgeRange[];

  // Step 2 — Restrictions
  dietTags: string[];
  allergies: string[];

  // Step 3 — Contexte
  cookingTimeMax: CookingTimeMax;
  driveProvider: DriveProvider;

  // Actions
  setStep1Data: (data: Partial<Step1Data>) => void;
  setStep2Data: (data: Partial<Step2Data>) => void;
  setStep3Data: (data: Partial<Step3Data>) => void;
  setCurrentStep: (step: OnboardingStep) => void;
  reset: () => void;

  // Submit orchestré — crée household + membres + préférences + génère premier plan
  submit: () => Promise<void>;
}

// --- Valeurs initiales ---

const INITIAL_STATE = {
  currentStep: 1 as OnboardingStep,
  generatedTaskId: null,
  adultsCount: 2,
  childrenCount: 0,
  childrenAges: [] as ChildAgeRange[],
  dietTags: [] as string[],
  allergies: [] as string[],
  cookingTimeMax: 40 as CookingTimeMax,
  driveProvider: "none" as DriveProvider,
};

// --- Store ---

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      ...INITIAL_STATE,

      setCurrentStep: (step) => set({ currentStep: step }),

      setStep1Data: (data) =>
        set((state) => ({
          adultsCount: data.adultsCount ?? state.adultsCount,
          childrenCount: data.childrenCount ?? state.childrenCount,
          childrenAges: data.childrenAges ?? state.childrenAges,
        })),

      setStep2Data: (data) =>
        set((state) => ({
          dietTags: data.dietTags ?? state.dietTags,
          allergies: data.allergies ?? state.allergies,
        })),

      setStep3Data: (data) =>
        set((state) => ({
          cookingTimeMax: data.cookingTimeMax ?? state.cookingTimeMax,
          driveProvider: data.driveProvider ?? state.driveProvider,
        })),

      reset: () => set(INITIAL_STATE),

      // Orchestration complète du submit onboarding
      // FIX Phase 1 mature (review 2026-04-12) — BUG #4 : submit idempotent
      // Détecte un household existant avant création pour éviter les données orphelines
      // Un retry après échec partiel reprend depuis la bonne étape sans erreur 409
      submit: async () => {
        const state = get();
        set({ currentStep: "generating" });

        try {
          // Étape 1 — Récupérer le household existant OU en créer un nouveau
          // Idempotence : si le household existe déjà (retry après échec), on le réutilise
          let householdResponse: HouseholdCreateResponse;

          try {
            householdResponse = await apiClient.get<HouseholdCreateResponse>(
              "/api/v1/households/me",
            );
          } catch (getError) {
            // Household n'existe pas encore (404) → on le crée
            // FIX Phase 1 mature (review 2026-04-12) — Mismatch A : `first_member` (pas `member`)
            if (getError instanceof ApiRequestError && getError.statusCode === 404) {
              householdResponse = await apiClient.post<HouseholdCreateResponse>(
                "/api/v1/households",
                {
                  name: "Mon foyer",
                  first_member: {
                    display_name: "Moi",
                    is_child: false,
                  },
                },
              );
            } else {
              throw getError;
            }
          }

          const firstMember = householdResponse.members[0];
          const ownerId = firstMember?.id;

          if (!ownerId) {
            throw new Error("Impossible de récupérer l'identifiant du membre owner");
          }

          // Étape 2 — Ajouter les enfants comme membres séparés
          // Idempotence : n'ajouter que si les membres enfants ne sont pas encore créés
          const existingMembersCount = householdResponse.members.length;
          const expectedTotalMembers = 1 + state.childrenCount;

          if (state.childrenCount > 0 && existingMembersCount < expectedTotalMembers) {
            for (let i = 0; i < state.childrenCount; i++) {
              const ageRange: ChildAgeRange | undefined = state.childrenAges[i];
              await apiClient.post("/api/v1/households/me/members", {
                display_name: `Enfant ${i + 1}`,
                is_child: true,
                birth_date: ageRange !== undefined ? estimateBirthDateFromRange(ageRange) : null,
              });
            }
          }

          // Étape 3 — Appliquer les préférences sur le membre owner (PATCH = idempotent)
          await apiClient.patch(
            `/api/v1/households/me/members/${ownerId}/preferences`,
            {
              diet_tags: state.dietTags,
              allergies: state.allergies,
              dislikes: [],
              cooking_time_max: state.cookingTimeMax,
              budget_pref: null,
            },
          );

          // Étape 4 — Déclencher la génération du premier plan
          // FIX Phase 1 mature (review 2026-04-12) — Mismatch E : body { week_start } obligatoire
          const generateResponse = await apiClient.post<GeneratePlanResponse>(
            "/api/v1/plans/generate",
            { week_start: getCurrentMonday() },
          );

          set({ generatedTaskId: generateResponse.task_id });

          // Étape 5 — Polling jusqu'à ce que le plan soit prêt
          // FIX Phase 1 mature (review 2026-04-12) — BUG #2 : polling via /plans/me/current
          await pollUntilPlanReady();

          set({ currentStep: "done" });
        } catch (error) {
          // Ne PAS reset le store — permettre le retry depuis le bon point
          // Rollback à step 3 pour que l'utilisateur puisse relancer submit()
          set({ currentStep: 3 });

          const message =
            error instanceof Error ? error.message : "Une erreur inattendue est survenue.";

          // Ne pas afficher les erreurs API déjà gérées par le client (toast déjà affiché)
          if (!message.includes("Erreur API")) {
            toast.error("Création du foyer impossible", {
              description: message,
              duration: 6000,
            });
          }

          throw error;
        }
      },
    }),
    {
      name: "mealplanner-onboarding",
      storage: createJSONStorage(() => localStorage),
      // Persister uniquement les données collectées, pas l'état transitionnel
      partialize: (state) => ({
        adultsCount: state.adultsCount,
        childrenCount: state.childrenCount,
        childrenAges: state.childrenAges,
        dietTags: state.dietTags,
        allergies: state.allergies,
        cookingTimeMax: state.cookingTimeMax,
        driveProvider: state.driveProvider,
        // Conserver le step courant pour reprendre après refresh
        currentStep: state.currentStep === "generating" ? 3 : state.currentStep,
      }),
    },
  ),
);

// --- Helpers ---

// FIX Phase 1 mature (review 2026-04-12) — BUG #2
// Polling CORRIGÉ : utilise GET /plans/me/current au lieu de /plans/{taskId}
// Raison : taskId est un UUID Celery — l'endpoint /plans/{id} attend un UUID de plan PostgreSQL
// → retournait 404 systématiquement → 100% des users bloqués à l'onboarding
//
// Nouveau comportement :
// - Poll GET /api/v1/plans/me/current toutes les 2-4s (backoff progressif)
// - Succès si plan.status === "draft" | "validated" (le plan a été créé par le worker)
// - 404 → plan pas encore créé, continuer le polling (comportement normal)
// - Timeout après 30 tentatives (~90s max)
async function pollUntilPlanReady(maxAttempts = 30): Promise<void> {
  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    // Backoff progressif : 2s → 3s → 4s (max) — identique à l'ancien polling
    const waitMs = Math.min(2000 + attempt * 500, 4000);
    await delay(waitMs);

    try {
      const plan = await apiClient.get<PlanCurrentResponse>("/api/v1/plans/me/current");

      // Plan créé et prêt (draft = généré, validated = confirmé par l'user)
      if (plan.status === "draft" || plan.status === "validated") {
        return;
      }

      // Plan en état d'échec côté worker
      if (plan.status === "failed") {
        throw new Error("La génération du plan a échoué. Veuillez réessayer.");
      }

      // Statut "generating" → continuer le polling
    } catch (err) {
      if (err instanceof ApiRequestError && err.statusCode === 404) {
        // 404 = plan pas encore créé par le worker Celery → continuer le polling
        continue;
      }

      // Erreur réseau sur le dernier attempt → propager
      if (attempt === maxAttempts - 1) {
        throw err;
      }
      // Erreur réseau transitoire sur un attempt intermédiaire → continuer
    }
  }

  throw new Error("Timeout : la génération du plan a pris trop de temps. Réessayez.");
}

// Estime une date de naissance approximative depuis la tranche d'âge
// Utilisé pour indiquer l'âge enfant au backend sans demander la date exacte
function estimateBirthDateFromRange(range: ChildAgeRange): string {
  const now = new Date();
  const year = now.getFullYear();

  const yearsByRange: Record<ChildAgeRange, number> = {
    "0-2": year - 1,
    "3-6": year - 4,
    "7-12": year - 9,
    "13+": year - 14,
  };

  const birthYear = yearsByRange[range];
  return `${birthYear}-01-01`;
}
