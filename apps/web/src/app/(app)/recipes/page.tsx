// apps/web/src/app/(app)/recipes/page.tsx
// Page "Explorer les recettes" — Server Component avec Client filtres
// Phase 2 — barre de recherche, filtres avancés, grid de résultats
import type { Metadata } from "next";
import { RecipesExplorer } from "./recipes-explorer";

export const metadata: Metadata = {
  title: "Explorer les recettes — Presto",
  description: "Découvrez des centaines de recettes filtrées par budget, temps, régime et cuisine.",
};

export default function RecipesPage() {
  return (
    <div className="min-h-screen bg-cream-50">
      <RecipesExplorer />
    </div>
  );
}
