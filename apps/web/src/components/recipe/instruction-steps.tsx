// apps/web/src/components/recipe/instruction-steps.tsx
// Étapes de préparation numérotées
// Timer interactif : stub Phase 1, implémenté en Phase 2
"use client";

import { Clock } from "lucide-react";
import type { Instruction } from "@/lib/api/types";

interface InstructionStepsProps {
  instructions: Instruction[];
}

export function InstructionSteps({ instructions = [] }: InstructionStepsProps) {
  if (instructions.length === 0) {
    return (
      <p className="text-sm text-neutral-400 dark:text-neutral-500">
        Les instructions pour cette recette ne sont pas encore disponibles.
      </p>
    );
  }

  // Trier par numéro d'étape
  const sorted = [...instructions].sort((a, b) => a.step_number - b.step_number);

  return (
    <ol className="space-y-6" aria-label="Étapes de préparation">
      {sorted.map((step) => (
        <li key={step.step_number} className="flex gap-4">
          {/* Numéro d'étape */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30">
            <span
              className="text-sm font-bold text-primary-600 dark:text-primary-400"
              aria-hidden="true"
            >
              {step.step_number}
            </span>
          </div>

          <div className="flex-1 pt-1">
            {/* Description de l'étape */}
            <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
              {step.description}
            </p>

            {/* Timer — stub Phase 1 */}
            {step.duration_seconds && step.duration_seconds > 0 && (
              <div className="mt-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200
                    bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-600
                    transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-600
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
                    dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400"
                  aria-label={`Démarrer un minuteur de ${formatDuration(step.duration_seconds)}`}
                  // Phase 2 : déclencher un timer interactif
                  onClick={() => {/* stub */ }}
                >
                  <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                  {formatDuration(step.duration_seconds)}
                </button>
              </div>
            )}

            {/* Image étape — si disponible */}
            {step.image_url && (
              <div className="mt-3 overflow-hidden rounded-xl">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={step.image_url}
                  alt={`Étape ${step.step_number}`}
                  className="w-full object-cover"
                  loading="lazy"
                />
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// Formater une durée en secondes vers "Xmin Ys"
function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes === 0) return `${remainingSeconds}s`;
  if (remainingSeconds === 0) return `${minutes} min`;
  return `${minutes} min ${remainingSeconds}s`;
}
