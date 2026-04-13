// apps/web/src/app/(app)/recipes/[id]/recipe-tabs-client.tsx
// Client Component — Tabs Radix (Ingrédients / Instructions / Nutrition) + RatingModal
// Isoler les interactions dans un Client Component léger, RSC garde le fetch
"use client";

import { useState } from "react";
import * as RadixTabs from "@radix-ui/react-tabs";
import { Star } from "lucide-react";
import { IngredientList } from "@/components/recipe/ingredient-list";
import { InstructionSteps } from "@/components/recipe/instruction-steps";
import { RatingModal } from "@/components/recipe/rating-modal";
import { cn } from "@/lib/utils";
import type { Recipe } from "@/lib/api/types";

interface RecipeTabsClientProps {
  recipe: Recipe;
}

// Labels nutrition
const NUTRITION_ITEMS = [
  { key: "calories" as const, label: "Calories", unit: "kcal", color: "bg-primary-400" },
  { key: "carbs_g" as const, label: "Glucides", unit: "g", color: "bg-amber-400" },
  { key: "proteins_g" as const, label: "Protéines", unit: "g", color: "bg-emerald-500" },
  { key: "fat_g" as const, label: "Lipides", unit: "g", color: "bg-blue-400" },
] as const;

export function RecipeTabsClient({ recipe }: RecipeTabsClientProps) {
  const [isRatingModalOpen, setIsRatingModalOpen] = useState(false);

  return (
    <>
      {/* Bouton notation */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          {recipe.description && (
            <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-400 line-clamp-3">
              {recipe.description}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setIsRatingModalOpen(true)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-neutral-200
            bg-white px-4 py-2 text-sm font-medium text-neutral-700
            transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
            dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
        >
          <Star className="h-4 w-4" aria-hidden="true" />
          Noter
        </button>
      </div>

      {/* Tabs Radix */}
      <RadixTabs.Root defaultValue="ingredients">
        {/* Tab list */}
        <RadixTabs.List
          className="mb-6 flex border-b border-neutral-200 dark:border-neutral-700"
          aria-label="Sections de la recette"
        >
          {[
            { value: "ingredients", label: "Ingrédients" },
            { value: "instructions", label: "Instructions" },
            { value: "nutrition", label: "Nutrition" },
          ].map((tab) => (
            <RadixTabs.Trigger
              key={tab.value}
              value={tab.value}
              className={cn(
                "flex-1 px-2 py-3 text-sm font-medium transition-all duration-fast",
                "border-b-2 border-transparent -mb-px",
                "text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset",
                // Tailwind data-* attribute selector pour l'état actif
                "data-[state=active]:border-primary-500 data-[state=active]:text-primary-700 dark:data-[state=active]:text-primary-400",
              )}
            >
              {tab.label}
            </RadixTabs.Trigger>
          ))}
        </RadixTabs.List>

        {/* Ingrédients */}
        <RadixTabs.Content value="ingredients" className="focus-visible:outline-none">
          <IngredientList
            ingredients={recipe.ingredients}
            servings={recipe.servings}
          />
        </RadixTabs.Content>

        {/* Instructions */}
        <RadixTabs.Content value="instructions" className="focus-visible:outline-none">
          <InstructionSteps instructions={recipe.instructions} />
        </RadixTabs.Content>

        {/* Nutrition */}
        <RadixTabs.Content value="nutrition" className="focus-visible:outline-none">
          {recipe.nutrition ? (
            <div className="space-y-4">
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Valeurs nutritionnelles pour {recipe.servings} portion
                {recipe.servings > 1 ? "s" : ""}
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {NUTRITION_ITEMS.map((item) => {
                  const value = recipe.nutrition?.[item.key];
                  return (
                    <div
                      key={item.key}
                      className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-center dark:border-neutral-700 dark:bg-neutral-800"
                    >
                      <div className="font-mono text-xl font-bold text-neutral-900 dark:text-neutral-100">
                        {value ?? "—"}
                      </div>
                      <div className="text-xs text-neutral-500 dark:text-neutral-400">
                        {item.unit}
                      </div>
                      <div className="mt-1 text-xs font-medium text-neutral-600 dark:text-neutral-300">
                        {item.label}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-neutral-100 bg-neutral-50 p-6 text-center dark:border-neutral-800 dark:bg-neutral-800/50">
              <p className="text-sm font-medium text-neutral-600 dark:text-neutral-300">
                Informations nutritionnelles bientôt disponibles
              </p>
              <p className="mt-1 text-xs text-neutral-400 dark:text-neutral-500">
                Nous travaillons à enrichir nos recettes avec des données nutritionnelles précises.
              </p>
            </div>
          )}
        </RadixTabs.Content>
      </RadixTabs.Root>

      {/* Modal de notation */}
      <RatingModal
        recipeId={recipe.id}
        recipeTitle={recipe.title}
        isOpen={isRatingModalOpen}
        onClose={() => setIsRatingModalOpen(false)}
      />
    </>
  );
}
