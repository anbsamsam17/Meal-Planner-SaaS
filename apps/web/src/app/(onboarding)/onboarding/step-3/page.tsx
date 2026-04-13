// apps/web/src/app/(onboarding)/onboarding/step-3/page.tsx
// Étape 3 — "Votre contexte" — déclenche submit() du store onboarding
// Référence : onboarding-protocol.md — Étape 3 (30 secondes cible)
// Données : temps de cuisine + enseigne drive → submit() → écran generating
"use client";

import { useRouter } from "next/navigation";
import { Check } from "lucide-react";
import { useOnboardingStore } from "@/stores/onboarding-store";
import type { CookingTimeMax, DriveProvider } from "@/stores/onboarding-store";
import { ProgressDots } from "@/components/onboarding/progress-dots";
import { StepNavigator } from "@/components/onboarding/step-navigator";
import { MotionDiv } from "@/components/motion";

interface CookingTimeOption {
  value: CookingTimeMax;
  label: string;
  sublabel: string;
  emoji: string;
}

interface DriveOption {
  value: DriveProvider;
  label: string;
}

const COOKING_TIME_OPTIONS: CookingTimeOption[] = [
  { value: 20, label: "< 20 min", sublabel: "Rapide", emoji: "⚡" },
  { value: 40, label: "20–40 min", sublabel: "Normal", emoji: "🍳" },
  { value: 60, label: "+ 40 min", sublabel: "Je prends mon temps", emoji: "👨‍🍳" },
];

const DRIVE_OPTIONS: DriveOption[] = [
  { value: "leclerc", label: "Leclerc Drive" },
  { value: "auchan", label: "Auchan Drive" },
  { value: "carrefour", label: "Carrefour Drive" },
  { value: "intermarche", label: "Intermarché Drive" },
  { value: "none", label: "Je ne commande pas en drive" },
];

export default function OnboardingStep3Page() {
  const router = useRouter();

  const cookingTimeMax = useOnboardingStore((s) => s.cookingTimeMax);
  const driveProvider = useOnboardingStore((s) => s.driveProvider);
  const setStep3Data = useOnboardingStore((s) => s.setStep3Data);
  const setCurrentStep = useOnboardingStore((s) => s.setCurrentStep);
  const submit = useOnboardingStore((s) => s.submit);
  const currentStep = useOnboardingStore((s) => s.currentStep);

  const isLoading = currentStep === "generating";

  function handleBack() {
    setCurrentStep(2);
    router.push("/onboarding/step-2");
  }

  async function handleSubmit() {
    try {
      await submit();
      // submit() met currentStep à "done" quand prêt
      router.push("/generating");
    } catch {
      // L'erreur est déjà gérée dans submit() avec un toast
      // Le store a rollbacké à currentStep = 3
    }
  }

  function handleTimeSelect(value: CookingTimeMax) {
    setStep3Data({ cookingTimeMax: value });
  }

  function handleDriveSelect(value: DriveProvider) {
    setStep3Data({ driveProvider: driveProvider === value ? "none" : value });
  }

  return (
    <MotionDiv
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 35, mass: 1.0 }}
      className="flex flex-1 flex-col items-center justify-start px-6 py-8"
    >
      <div className="w-full max-w-sm">
        <ProgressDots currentStep={3} className="mb-6" />

        <h1 className="font-serif mb-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">
          Votre contexte
        </h1>
        <p className="mb-8 text-base text-neutral-500 dark:text-neutral-400">
          En semaine, combien de temps avez-vous pour cuisiner le soir ?
        </p>

        {/* Sélection du temps de cuisine — 3 cards visuelles */}
        <div className="mb-8">
          <fieldset>
            <legend className="sr-only">Temps de cuisine disponible en semaine</legend>
            <div className="grid grid-cols-3 gap-3">
              {COOKING_TIME_OPTIONS.map((option) => {
                const isSelected = cookingTimeMax === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleTimeSelect(option.value)}
                    aria-pressed={isSelected}
                    className={`flex min-h-[88px] flex-col items-center justify-center gap-1 rounded-xl border-2 px-3 py-4
                      transition-all duration-fast
                      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                      ${
                        isSelected
                          ? "border-primary-400 bg-primary-50 dark:bg-primary-950"
                          : "border-neutral-200 bg-white hover:border-neutral-300 dark:border-neutral-700 dark:bg-neutral-800"
                      }`}
                  >
                    <span className="text-2xl" aria-hidden="true">
                      {option.emoji}
                    </span>
                    <span
                      className={`text-sm font-bold ${
                        isSelected
                          ? "text-primary-700 dark:text-primary-300"
                          : "text-neutral-900 dark:text-neutral-100"
                      }`}
                    >
                      {option.label}
                    </span>
                    <span
                      className={`text-center text-xs ${
                        isSelected
                          ? "text-primary-600 dark:text-primary-400"
                          : "text-neutral-500 dark:text-neutral-400"
                      }`}
                    >
                      {option.sublabel}
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>

        {/* Sélection drive — optionnel, ne bloque pas le submit */}
        <div className="mb-8">
          <h2 className="mb-3 text-base font-medium text-neutral-900 dark:text-neutral-100">
            Quel drive utilisez-vous ?{" "}
            <span className="font-normal text-neutral-400">(optionnel)</span>
          </h2>
          <fieldset>
            <legend className="sr-only">Enseigne drive préférée</legend>
            <div className="flex flex-col gap-2">
              {DRIVE_OPTIONS.map((option) => {
                const isSelected = driveProvider === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleDriveSelect(option.value)}
                    aria-pressed={isSelected}
                    className={`flex min-h-[44px] items-center justify-between rounded-xl border px-4 py-3
                      text-left text-sm transition-all duration-fast
                      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                      ${
                        isSelected
                          ? "border-primary-400 bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
                          : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
                      }`}
                  >
                    <span className={isSelected ? "font-medium" : ""}>{option.label}</span>
                    {isSelected && (
                      <Check className="h-4 w-4 text-primary-600 dark:text-primary-400" aria-hidden="true" />
                    )}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>

        {/* Navigation — "Terminer" déclenche submit() */}
        <StepNavigator
          onBack={handleBack}
          onContinue={handleSubmit}
          continueLabel="Générer mon premier plan ✨"
          isLoading={isLoading}
          showBack
        />

        <p className="mt-3 text-center text-xs text-neutral-400">
          Vous pourrez modifier ces préférences à tout moment
        </p>
      </div>
    </MotionDiv>
  );
}
