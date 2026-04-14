"use client";
// apps/web/src/components/onboarding/progress-bar.tsx
// Barre de progression onboarding -- Client Component
// Calcule le step courant a partir du pathname pour remplir les barres

import { usePathname } from "next/navigation";

const TOTAL_STEPS = 3;

function getStepFromPathname(pathname: string | null): number {
  if (!pathname) return 0;
  if (pathname.includes("step-3")) return 3;
  if (pathname.includes("step-2")) return 2;
  if (pathname.includes("step-1")) return 1;
  // /generating = apres step-3, afficher 100%
  if (pathname.includes("generating")) return 3;
  return 0;
}

export function OnboardingProgressBar() {
  const pathname = usePathname();
  const currentStep = getStepFromPathname(pathname);

  return (
    <div
      className="px-6 py-4"
      role="progressbar"
      aria-label="Progression de l'inscription"
      aria-valuenow={currentStep}
      aria-valuemin={0}
      aria-valuemax={TOTAL_STEPS}
    >
      <div className="mx-auto flex max-w-sm items-center gap-2">
        {[1, 2, 3].map((step) => {
          const progress = currentStep >= step ? 100 : 0;
          return (
            <div
              key={step}
              className="h-1.5 flex-1 rounded-full bg-neutral-200"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-primary-500 transition-all duration-slow"
                style={{ width: `${progress}%` }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
