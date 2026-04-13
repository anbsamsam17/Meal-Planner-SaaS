// apps/web/src/components/onboarding/step-navigator.tsx
// Boutons "Retour" + "Continuer/Terminer" cohérents sur toutes les étapes
// Utilisé dans les pages step-1, step-2, step-3
"use client";

import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepNavigatorProps {
  onBack?: () => void;
  onContinue: () => void;
  continueLabel?: string;
  isLoading?: boolean;
  isDisabled?: boolean;
  showBack?: boolean;
  className?: string;
}

export function StepNavigator({
  onBack,
  onContinue,
  continueLabel = "Continuer",
  isLoading = false,
  isDisabled = false,
  showBack = true,
  className,
}: StepNavigatorProps) {
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Bouton principal — Continuer / Terminer */}
      <button
        type="button"
        onClick={onContinue}
        disabled={isDisabled || isLoading}
        aria-busy={isLoading}
        aria-disabled={isDisabled || isLoading}
        className="inline-flex min-h-[56px] w-full items-center justify-center gap-2
          rounded-xl bg-primary-500 px-8 py-4 text-lg font-semibold text-white
          shadow-sm transition-all duration-base
          hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-primary-500 focus-visible:ring-offset-2
          active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            Création en cours…
          </>
        ) : (
          <>
            {continueLabel}
            <ArrowRight className="h-5 w-5" aria-hidden="true" />
          </>
        )}
      </button>

      {/* Bouton retour — affiché uniquement si showBack et onBack définis */}
      {showBack && onBack && (
        <button
          type="button"
          onClick={onBack}
          disabled={isLoading}
          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2
            rounded-xl px-4 py-2 text-sm font-medium text-neutral-500
            transition-colors duration-fast
            hover:bg-neutral-100 hover:text-neutral-700
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            focus-visible:ring-offset-2 disabled:opacity-50"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Retour
        </button>
      )}
    </div>
  );
}
