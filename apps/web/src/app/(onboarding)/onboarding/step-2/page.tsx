// apps/web/src/app/(onboarding)/onboarding/step-2/page.tsx
// Étape 2 — "Ce que vous ne mangez pas" — connectée au store Zustand
// Référence : onboarding-protocol.md — Étape 2 (30 secondes cible), abandon < 8%
// "Pas de restriction" en premier et en taille XXL — règle UX critique
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { ProgressDots } from "@/components/onboarding/progress-dots";
import { StepNavigator } from "@/components/onboarding/step-navigator";
import { MotionDiv } from "@/components/motion";

type DietaryRestriction =
  | "no-restriction"
  | "vegetarian"
  | "vegan"
  | "gluten-free"
  | "no-pork"
  | "no-seafood"
  | "nut-allergy"
  | "lactose-free"
  | "halal";

interface RestrictionOption {
  value: DietaryRestriction;
  label: string;
  emoji: string;
  description: string;
}

// "Pas de restriction" en premier — règle UX onboarding-protocol.md Scénario B
const RESTRICTION_OPTIONS: RestrictionOption[] = [
  {
    value: "no-restriction",
    label: "Pas de restriction",
    emoji: "🍽️",
    description: "Tout le monde mange de tout",
  },
  { value: "vegetarian", label: "Végétarien", emoji: "🥦", description: "Sans viande ni poisson" },
  { value: "vegan", label: "Végétalien", emoji: "🌱", description: "Sans produits animaux" },
  { value: "gluten-free", label: "Sans gluten", emoji: "🌾", description: "Maladie cœliaque ou intolérance" },
  { value: "no-pork", label: "Sans porc", emoji: "🐷", description: "Halal ou préférence" },
  { value: "no-seafood", label: "Sans fruits de mer", emoji: "🦐", description: "Allergie ou aversion" },
  { value: "nut-allergy", label: "Allergie noix", emoji: "🥜", description: "Allergie aux fruits à coque" },
  { value: "lactose-free", label: "Sans lactose", emoji: "🥛", description: "Intolérance au lactose" },
  { value: "halal", label: "Halal", emoji: "☪️", description: "Viande halal uniquement" },
];

// Mapper les restrictions UI vers les diet_tags API
const RESTRICTION_TO_DIET_TAG: Partial<Record<DietaryRestriction, string>> = {
  vegetarian: "vegetarian",
  vegan: "vegan",
  "gluten-free": "gluten_free",
  "no-pork": "no_pork",
  "no-seafood": "no_seafood",
  halal: "halal",
};

const RESTRICTION_TO_ALLERGY: Partial<Record<DietaryRestriction, string>> = {
  "nut-allergy": "nuts",
  "lactose-free": "lactose",
};

export default function OnboardingStep2Page() {
  const router = useRouter();

  const dietTags = useOnboardingStore((s) => s.dietTags);
  const allergies = useOnboardingStore((s) => s.allergies);
  const setStep2Data = useOnboardingStore((s) => s.setStep2Data);
  const setCurrentStep = useOnboardingStore((s) => s.setCurrentStep);

  // Reconstruire l'état UI depuis le store
  const getInitialRestrictions = (): Set<DietaryRestriction> => {
    const set = new Set<DietaryRestriction>();
    if (dietTags.length === 0 && allergies.length === 0) {
      set.add("no-restriction");
      return set;
    }
    for (const [restriction, tag] of Object.entries(RESTRICTION_TO_DIET_TAG)) {
      if (dietTags.includes(tag)) set.add(restriction as DietaryRestriction);
    }
    for (const [restriction, allergy] of Object.entries(RESTRICTION_TO_ALLERGY)) {
      if (allergies.includes(allergy)) set.add(restriction as DietaryRestriction);
    }
    if (set.size === 0) set.add("no-restriction");
    return set;
  };

  const [selectedRestrictions, setSelectedRestrictions] = useState<Set<DietaryRestriction>>(
    getInitialRestrictions,
  );

  function toggleRestriction(restriction: DietaryRestriction) {
    setSelectedRestrictions((prev) => {
      const next = new Set(prev);

      if (restriction === "no-restriction") {
        // Sélectionner "pas de restriction" efface tout le reste
        return new Set(["no-restriction" as DietaryRestriction]);
      }

      next.delete("no-restriction");

      if (next.has(restriction)) {
        next.delete(restriction);
        if (next.size === 0) next.add("no-restriction");
      } else {
        next.add(restriction);
      }

      return next;
    });
  }

  function handleBack() {
    setCurrentStep(1);
    router.push("/onboarding/step-1");
  }

  function handleContinue() {
    // Convertir l'état UI vers les structures API
    const newDietTags: string[] = [];
    const newAllergies: string[] = [];

    for (const restriction of selectedRestrictions) {
      if (restriction === "no-restriction") continue;
      const dietTag = RESTRICTION_TO_DIET_TAG[restriction];
      if (dietTag) newDietTags.push(dietTag);
      const allergy = RESTRICTION_TO_ALLERGY[restriction];
      if (allergy) newAllergies.push(allergy);
    }

    setStep2Data({ dietTags: newDietTags, allergies: newAllergies });
    setCurrentStep(3);
    router.push("/onboarding/step-3");
  }

  // Valide si une sélection a été faite (no-restriction compte comme sélection)
  const isValid = selectedRestrictions.size > 0;

  const noRestrictionOption = RESTRICTION_OPTIONS[0]!;
  const otherOptions = RESTRICTION_OPTIONS.slice(1);

  return (
    <MotionDiv
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 35, mass: 1.0 }}
      className="flex flex-1 flex-col items-center justify-start px-6 py-8"
    >
      <div className="w-full max-w-sm">
        <ProgressDots currentStep={2} className="mb-6" />

        <h1 className="font-serif mb-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">
          Ce que vous ne mangez pas
        </h1>
        <p className="mb-6 text-base text-neutral-500 dark:text-neutral-400">
          Y a-t-il des restrictions alimentaires dans votre famille ?
        </p>

        <fieldset>
          <legend className="sr-only">Restrictions alimentaires</legend>

          {/* "Pas de restriction" en taille XL et en premier — règle UX critique */}
          <button
            type="button"
            onClick={() => toggleRestriction(noRestrictionOption.value)}
            aria-pressed={selectedRestrictions.has(noRestrictionOption.value)}
            className={`mb-3 flex min-h-[64px] w-full items-center gap-4 rounded-xl border-2 px-5 py-4
              text-left transition-all duration-fast
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
              ${
                selectedRestrictions.has(noRestrictionOption.value)
                  ? "border-primary-400 bg-primary-50 dark:bg-primary-950"
                  : "border-neutral-200 bg-white hover:border-neutral-300 dark:border-neutral-700 dark:bg-neutral-800"
              }`}
          >
            <span className="text-2xl" aria-hidden="true">
              {noRestrictionOption.emoji}
            </span>
            <div>
              <div
                className={`text-base font-semibold ${
                  selectedRestrictions.has(noRestrictionOption.value)
                    ? "text-primary-700 dark:text-primary-300"
                    : "text-neutral-900 dark:text-neutral-100"
                }`}
              >
                {noRestrictionOption.label}
              </div>
              <div className="text-sm text-neutral-500 dark:text-neutral-400">
                {noRestrictionOption.description}
              </div>
            </div>
          </button>

          {/* Grille chips restrictions */}
          <div className="grid grid-cols-2 gap-2">
            {otherOptions.map((option) => {
              const isSelected = selectedRestrictions.has(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => toggleRestriction(option.value)}
                  aria-pressed={isSelected}
                  className={`flex min-h-[72px] flex-col items-start gap-1 rounded-xl border px-4 py-3
                    text-left transition-all duration-fast
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                    ${
                      isSelected
                        ? "border-primary-400 bg-primary-50 dark:bg-primary-950"
                        : "border-neutral-200 bg-white hover:border-neutral-300 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:hover:bg-neutral-750"
                    }`}
                >
                  <span className="text-xl" aria-hidden="true">
                    {option.emoji}
                  </span>
                  <span
                    className={`text-sm font-medium ${
                      isSelected
                        ? "text-primary-700 dark:text-primary-300"
                        : "text-neutral-800 dark:text-neutral-200"
                    }`}
                  >
                    {option.label}
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>

        {/* Navigation */}
        <StepNavigator
          onBack={handleBack}
          onContinue={handleContinue}
          isDisabled={!isValid}
          showBack
          className="mt-6"
        />
      </div>
    </MotionDiv>
  );
}
