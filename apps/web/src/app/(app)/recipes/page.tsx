// apps/web/src/app/(app)/recipes/page.tsx
// Page "Explorer les recettes" — Server Component avec Client filtres
// Phase 2 — design food premium : fond cream #fff8f6, header terracotta
import type { Metadata } from "next";
import { RecipesExplorer } from "./recipes-explorer";

export const metadata: Metadata = {
  title: "Explorer les recettes — Presto",
  description: "Découvrez des centaines de recettes filtrées par budget, temps, régime et cuisine.",
};

export default function RecipesPage() {
  return (
    <div className="min-h-screen bg-[#fff8f6]">
      <RecipesExplorer />
    </div>
  );
}
