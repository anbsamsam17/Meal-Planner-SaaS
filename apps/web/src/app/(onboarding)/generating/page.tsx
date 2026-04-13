// apps/web/src/app/(onboarding)/generating/page.tsx
// Écran transitoire "Je prépare votre semaine..." — affiché pendant la génération IA
// Messages rotatifs, animation spinner Framer Motion, redirect vers /dashboard quand prêt
// Polling sur l'état du store Zustand (task_id mis à jour par submit())
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { MotionDiv, AnimatePresence } from "@/components/motion";

// Messages rotatifs pendant la génération — évocation du fonctionnement IA
const LOADING_MESSAGES = [
  "Analyse de vos goûts…",
  "Sélection des recettes de la semaine…",
  "Équilibrage nutritionnel…",
  "Génération de la liste de courses…",
  "Finalisation de votre plan…",
] as const;

const MESSAGE_INTERVAL_MS = 2200;

export default function GeneratingPage() {
  const router = useRouter();
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const reset = useOnboardingStore((s) => s.reset);
  const [messageIndex, setMessageIndex] = useState(0);

  // Faire tourner les messages à intervalle régulier
  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
    }, MESSAGE_INTERVAL_MS);

    return () => clearInterval(interval);
  }, []);

  // Rediriger quand le plan est prêt
  useEffect(() => {
    if (currentStep === "done") {
      // Nettoyer le store après onboarding réussi
      reset();
      router.push("/dashboard");
    }
    // Si l'état revient en arrière (erreur avec rollback), retourner à step-3
    if (typeof currentStep === "number" && currentStep < 4) {
      router.push(`/onboarding/step-${currentStep}`);
    }
  }, [currentStep, router, reset]);

  const currentMessage = LOADING_MESSAGES[messageIndex] ?? "Préparation en cours…";

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[hsl(38,60%,97%)] px-6">
      {/* Spinner animé Framer Motion — simple et lisible */}
      <MotionDiv
        animate={{ rotate: 360 }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
        className="mb-10 h-16 w-16"
        aria-hidden="true"
      >
        {/* Spinner SVG en terracotta */}
        <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle
            cx="32"
            cy="32"
            r="28"
            stroke="hsl(38,20%,89%)"
            strokeWidth="6"
          />
          <path
            d="M32 4A28 28 0 0 1 60 32"
            stroke="hsl(14,75%,55%)"
            strokeWidth="6"
            strokeLinecap="round"
          />
        </svg>
      </MotionDiv>

      {/* Titre principal */}
      <h1 className="font-serif mb-4 text-center text-3xl font-bold text-neutral-900">
        Je prépare votre semaine…
      </h1>

      {/* Message rotatif avec transition fade */}
      <div className="h-6 overflow-hidden">
        <AnimatePresence mode="wait">
          <MotionDiv
            key={messageIndex}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="text-center text-base text-neutral-500"
            aria-live="polite"
            aria-atomic="true"
          >
            {currentMessage}
          </MotionDiv>
        </AnimatePresence>
      </div>

      {/* Note rassurante */}
      <p className="mt-12 text-center text-xs text-neutral-400">
        La génération prend généralement 5 à 15 secondes.
      </p>
    </div>
  );
}
