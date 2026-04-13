// apps/web/src/components/onboarding/progress-dots.tsx
// Indicateur visuel 3 points — actif = terracotta, futur = cream
// Animation Framer Motion via wrapper @/components/motion (pas d'import direct)
// Référence : 04-components-catalog.md #16 Stepper Onboarding
"use client";

import { MotionDiv } from "@/components/motion";
import { cn } from "@/lib/utils";

interface ProgressDotsProps {
  currentStep: 1 | 2 | 3;
  totalSteps?: number;
  className?: string;
}

export function ProgressDots({
  currentStep,
  totalSteps = 3,
  className,
}: ProgressDotsProps) {
  return (
    <div
      className={cn("flex items-center justify-center gap-2", className)}
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={totalSteps}
      aria-label={`Étape ${currentStep} sur ${totalSteps}`}
    >
      {Array.from({ length: totalSteps }, (_, i) => {
        const stepNumber = i + 1;
        const isActive = stepNumber === currentStep;
        const isCompleted = stepNumber < currentStep;

        return (
          <MotionDiv
            key={stepNumber}
            // Animation spring sur la taille (actif = plus large)
            initial={false}
            animate={{
              width: isActive ? 24 : 8,
              opacity: isCompleted ? 1 : isActive ? 1 : 0.35,
            }}
            transition={{
              type: "spring",
              stiffness: 400,
              damping: 30,
              mass: 0.8,
            }}
            className={cn(
              "h-2 rounded-full",
              isActive || isCompleted
                ? "bg-primary-500" // terracotta-500
                : "bg-neutral-300", // cream inactive
            )}
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}
