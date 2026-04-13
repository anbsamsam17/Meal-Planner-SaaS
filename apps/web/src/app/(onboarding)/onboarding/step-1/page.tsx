// apps/web/src/app/(onboarding)/onboarding/step-1/page.tsx
// Étape 1 — "Votre famille" — connectée au store Zustand
// Référence : onboarding-protocol.md — Étape 1 (30 secondes cible)
// KPI : taux d'abandon < 5%, temps < 30s
"use client";

import { useRouter } from "next/navigation";
import { Minus, Plus } from "lucide-react";
import { useOnboardingStore } from "@/stores/onboarding-store";
import type { ChildAgeRange } from "@/stores/onboarding-store";
import { ProgressDots } from "@/components/onboarding/progress-dots";
import { StepNavigator } from "@/components/onboarding/step-navigator";
import { AnimatePresence, MotionDiv } from "@/components/motion";

const CHILD_AGE_OPTIONS: { value: ChildAgeRange; label: string; emoji: string }[] = [
  { value: "0-2", label: "< 3 ans", emoji: "👶" },
  { value: "3-6", label: "3–6 ans", emoji: "🧒" },
  { value: "7-12", label: "7–12 ans", emoji: "👦" },
  { value: "13+", label: "13 ans+", emoji: "🧑" },
];

export default function OnboardingStep1Page() {
  const router = useRouter();

  const adultsCount = useOnboardingStore((s) => s.adultsCount);
  const childrenCount = useOnboardingStore((s) => s.childrenCount);
  const childrenAges = useOnboardingStore((s) => s.childrenAges);
  const setStep1Data = useOnboardingStore((s) => s.setStep1Data);
  const setCurrentStep = useOnboardingStore((s) => s.setCurrentStep);

  function incrementAdults() {
    setStep1Data({ adultsCount: Math.min(adultsCount + 1, 8) });
  }

  function decrementAdults() {
    setStep1Data({ adultsCount: Math.max(adultsCount - 1, 1) });
  }

  function incrementChildren() {
    setStep1Data({ childrenCount: Math.min(childrenCount + 1, 6) });
  }

  function decrementChildren() {
    const newCount = Math.max(childrenCount - 1, 0);
    setStep1Data({
      childrenCount: newCount,
      childrenAges: newCount === 0 ? [] : childrenAges,
    });
  }

  function toggleChildAge(age: ChildAgeRange) {
    const exists = childrenAges.includes(age);
    setStep1Data({
      childrenAges: exists
        ? childrenAges.filter((a) => a !== age)
        : [...childrenAges, age],
    });
  }

  function handleContinue() {
    setCurrentStep(2);
    router.push("/onboarding/step-2");
  }

  const totalMembers = adultsCount + childrenCount;
  // Bloquer si personne (ne doit pas arriver avec adultsCount >= 1)
  const isValid = totalMembers >= 1;

  return (
    <MotionDiv
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 35, mass: 1.0 }}
      className="flex flex-1 flex-col items-center justify-start px-6 py-8"
    >
      <div className="w-full max-w-sm">
        {/* Indicateur de progression dots */}
        <ProgressDots currentStep={1} className="mb-6" />

        {/* Titre de l'étape */}
        <h1 className="font-serif mb-2 text-3xl font-bold text-neutral-900 dark:text-neutral-100">
          Votre famille
        </h1>
        <p className="mb-8 text-base text-neutral-500 dark:text-neutral-400">
          Combien de personnes dînent chez vous ?
        </p>

        {/* Sélecteur adultes */}
        <div className="mb-4 space-y-3">
          <CounterRow
            label="Adultes"
            sublabel="18 ans et plus"
            value={adultsCount}
            onDecrement={decrementAdults}
            onIncrement={incrementAdults}
            min={1}
            max={8}
            decrementLabel="Réduire le nombre d'adultes"
            incrementLabel="Augmenter le nombre d'adultes"
          />

          {/* Sélecteur enfants */}
          <CounterRow
            label="Enfants"
            sublabel="Moins de 18 ans"
            value={childrenCount}
            onDecrement={decrementChildren}
            onIncrement={incrementChildren}
            min={0}
            max={6}
            decrementLabel="Réduire le nombre d'enfants"
            incrementLabel="Augmenter le nombre d'enfants"
          />
        </div>

        {/* Tranches d'âge enfants — révélées si children > 0 */}
        <AnimatePresence>
          {childrenCount > 0 && (
            <MotionDiv
              key="children-ages"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="mb-6 overflow-hidden"
            >
              <p className="mb-3 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                Quelles tranches d&apos;âge ?
              </p>
              <fieldset>
                <legend className="sr-only">Tranches d&apos;âge des enfants</legend>
                <div className="grid grid-cols-2 gap-2">
                  {CHILD_AGE_OPTIONS.map((option) => {
                    const isSelected = childrenAges.includes(option.value);
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => toggleChildAge(option.value)}
                        aria-pressed={isSelected}
                        className={`flex min-h-[44px] items-center gap-2 rounded-xl border px-4 py-3
                          text-sm font-medium transition-all duration-fast
                          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                          ${
                            isSelected
                              ? "border-primary-400 bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
                              : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
                          }`}
                      >
                        <span aria-hidden="true">{option.emoji}</span>
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
            </MotionDiv>
          )}
        </AnimatePresence>

        {/* Navigation */}
        <StepNavigator
          onContinue={handleContinue}
          isDisabled={!isValid}
          showBack={false}
          continueLabel="Continuer"
        />

        <div className="mt-4 text-center">
          <a
            href="/"
            className="text-sm text-neutral-400 hover:text-neutral-600
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Peut-être plus tard
          </a>
        </div>
      </div>
    </MotionDiv>
  );
}

// --- Composant interne CounterRow ---

interface CounterRowProps {
  label: string;
  sublabel: string;
  value: number;
  onDecrement: () => void;
  onIncrement: () => void;
  min: number;
  max: number;
  decrementLabel: string;
  incrementLabel: string;
}

function CounterRow({
  label,
  sublabel,
  value,
  onDecrement,
  onIncrement,
  min,
  max,
  decrementLabel,
  incrementLabel,
}: CounterRowProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-800">
      <div>
        <div className="text-base font-medium text-neutral-900 dark:text-neutral-100">{label}</div>
        <div className="text-sm text-neutral-500 dark:text-neutral-400">{sublabel}</div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onDecrement}
          disabled={value <= min}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-neutral-200
            text-neutral-600 transition-colors hover:bg-neutral-100
            disabled:cursor-not-allowed disabled:opacity-40
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-700"
          aria-label={decrementLabel}
        >
          <Minus className="h-4 w-4" aria-hidden="true" />
        </button>
        <span
          className="w-6 text-center text-xl font-bold text-neutral-900 dark:text-neutral-100"
          aria-live="polite"
          aria-atomic="true"
        >
          {value}
        </span>
        <button
          type="button"
          onClick={onIncrement}
          disabled={value >= max}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-neutral-200
            text-neutral-600 transition-colors hover:bg-neutral-100
            disabled:cursor-not-allowed disabled:opacity-40
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-700"
          aria-label={incrementLabel}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
