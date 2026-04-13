// apps/web/src/app/(onboarding)/onboarding/page.tsx
// Page d'entrée onboarding — redirige vers la première étape
import { redirect } from "next/navigation";

// Redirection immédiate vers l'étape 1
// Ce pattern évite d'avoir un écran intermédiaire vide
export default function OnboardingEntryPage() {
  redirect("/onboarding/step-1");
}
