// apps/web/src/lib/analytics/posthog.ts
// FIX Phase 1 (review 2026-04-12) : helper PostHog avec events normalisés — OPT
// Référence events : phase-0/ux-research/onboarding-protocol.md
//
// Comportement :
// - Si NEXT_PUBLIC_POSTHOG_KEY est défini → envoie les events à PostHog
// - Sinon (dev sans clé) → log structuré en console (niveau "info")
// - TypeScript strict : tous les events sont typés
//
// Usage :
//   import { analytics } from "@/lib/analytics/posthog"
//   analytics.onboardingStarted()
//   analytics.onboardingStepCompleted({ step: 1, stepName: "dietary_profile" })
//   analytics.planGenerated({ duration_ms: 1200, recipes_count: 5 })

// --- Types des payloads d'events ---

interface OnboardingStepCompletedPayload {
  /** Numéro de l'étape (1, 2 ou 3) */
  step: 1 | 2 | 3;
  /** Nom descriptif de l'étape pour le reporting */
  stepName: "dietary_profile" | "household_size" | "preferences";
  /** Durée passée sur l'étape en millisecondes */
  duration_ms?: number;
}

interface PlanGeneratedPayload {
  /** Durée de génération côté serveur en millisecondes */
  duration_ms: number;
  /** Nombre de recettes dans le plan généré */
  recipes_count: number;
  /** Nombre de repas couverts dans le plan */
  meals_count?: number;
}

interface EmailSubmittedPayload {
  /** Source du formulaire (onboarding, landing, modal) */
  source: "onboarding" | "landing" | "modal";
}

interface SubscriptionStartedPayload {
  /** Plan souscrit */
  plan: "starter" | "family" | "pro";
  /** Canal d'acquisition */
  source?: string;
}

// --- Implémentation ---

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const IS_DEV = process.env.NODE_ENV === "development";

/**
 * Log structuré en développement quand PostHog n'est pas configuré.
 * Permet de valider les events sans clé API.
 */
function devLog(eventName: string, properties?: Record<string, unknown>): void {
  if (IS_DEV) {
    console.info("[Analytics]", eventName, properties ?? {});
  }
}

/**
 * Capture un event PostHog si la clé est disponible, sinon log en dev.
 * Lazy-import de posthog-js pour ne pas l'inclure dans le bundle SSR.
 */
async function capture(eventName: string, properties?: Record<string, unknown>): Promise<void> {
  if (!POSTHOG_KEY) {
    devLog(eventName, properties);
    return;
  }

  try {
    // Import dynamique — posthog-js n'est pas dans les dépendances Phase 1
    // À installer en Phase 2 : pnpm add posthog-js
    // @ts-expect-error -- posthog-js sera ajouté en Phase 2
    const posthog = await import("posthog-js");
    posthog.default.capture(eventName, properties);
  } catch {
    // Fail silently — les analytics ne doivent jamais bloquer l'UX
    devLog(eventName, properties);
  }
}

// --- API publique des events normalisés ---

export const analytics = {
  /**
   * Déclenché quand l'utilisateur démarre le funnel d'onboarding.
   * Référence : onboarding-protocol.md - metric "onboarding_completion_rate"
   */
  onboardingStarted(): void {
    void capture("onboarding_started");
  },

  /**
   * Déclenché à chaque étape complétée dans le funnel.
   * Référence : onboarding-protocol.md - metric "step_completion_rate"
   */
  onboardingStepCompleted(payload: OnboardingStepCompletedPayload): void {
    void capture("onboarding_step_completed", payload as unknown as Record<string, unknown>);
  },

  /**
   * Déclenché quand l'onboarding est entièrement terminé.
   */
  onboardingCompleted(): void {
    void capture("onboarding_completed");
  },

  /**
   * Déclenché quand un plan de repas est généré par l'IA.
   * Référence : onboarding-protocol.md - metric "plan_generated"
   */
  planGenerated(payload: PlanGeneratedPayload): void {
    void capture("plan_generated", payload as unknown as Record<string, unknown>);
  },

  /**
   * Déclenché quand l'utilisateur soumet son email.
   */
  emailSubmitted(payload: EmailSubmittedPayload): void {
    void capture("email_submitted", payload as unknown as Record<string, unknown>);
  },

  /**
   * Déclenché lors de la souscription à un abonnement Stripe.
   */
  subscriptionStarted(payload: SubscriptionStartedPayload): void {
    void capture("subscription_started", payload as unknown as Record<string, unknown>);
  },

  /**
   * Déclenché lors d'une annulation d'abonnement (churn signal).
   */
  subscriptionCancelled(): void {
    void capture("subscription_cancelled");
  },

  /**
   * Déclenché quand une recette est ajoutée au planning hebdomadaire.
   */
  recipeAddedToPlanning(recipeId: string): void {
    void capture("recipe_added_to_planning", { recipe_id: recipeId });
  },

  /**
   * Déclenché quand le PDF livre de recettes est téléchargé.
   */
  pdfDownloaded(): void {
    void capture("pdf_downloaded");
  },
} as const;
