// apps/web/src/app/(app)/recipes/[id]/recipe-tabs-client.tsx
// Client Component -- Tabs Radix (Ingredients / Instructions / Nutrition) + RatingModal
// Redesign v3 : checkboxes ingredients, numbered instructions terracotta, nutrition badges
// 2026-04-16 : bouton favori (Heart) ajouté à côté de "Noter cette recette"
"use client";

import { useState } from "react";
import * as RadixTabs from "@radix-ui/react-tabs";
import { Heart, Star } from "lucide-react";
import { RatingModal } from "@/components/recipe/rating-modal";
import { useIsFavorite, useToggleFavorite } from "@/hooks/use-favorites";
import { cn } from "@/lib/utils";
import type { Recipe, Ingredient, Instruction } from "@/lib/api/types";

interface RecipeTabsClientProps {
  recipe: Recipe;
}

export function RecipeTabsClient({ recipe }: RecipeTabsClientProps) {
  const [isRatingModalOpen, setIsRatingModalOpen] = useState(false);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  const isFavorite = useIsFavorite(recipe.id);
  const toggleFavoriteMutation = useToggleFavorite();

  function toggleIngredient(id: string) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  // Normaliser les instructions : supporter les deux formats API
  const normalizedInstructions = (recipe.instructions ?? []).map((s: Instruction) => ({
    stepNumber: s.step_number ?? s.step ?? 0,
    description: s.description ?? s.text ?? "",
  }));
  const sortedInstructions = [...normalizedInstructions].sort(
    (a, b) => a.stepNumber - b.stepNumber,
  );

  const safeIngredients: Ingredient[] = Array.isArray(recipe.ingredients)
    ? recipe.ingredients
    : [];

  // Valeurs nutritionnelles -- estimees si pas en DB
  const nutrition = recipe.nutrition;
  const hasNutrition = nutrition != null;

  return (
    <>
      {/* Barre d'actions : noter + mettre en favori */}
      <div className="mb-6 flex items-center gap-4">
        <button
          type="button"
          onClick={() => setIsRatingModalOpen(true)}
          className="flex items-center gap-1.5 text-sm text-[#857370] transition-colors hover:text-[#E2725B] dark:text-neutral-400 dark:hover:text-[#E2725B]"
        >
          <Star className="h-4 w-4" aria-hidden="true" />
          Noter cette recette
        </button>

        {/* Bouton favori — filled si déjà en favori */}
        <button
          type="button"
          disabled={toggleFavoriteMutation.isPending}
          onClick={() =>
            toggleFavoriteMutation.mutate({ recipeId: recipe.id, isFavorite })
          }
          aria-label={isFavorite ? "Retirer des favoris" : "Ajouter aux favoris"}
          aria-pressed={isFavorite}
          className={cn(
            "flex items-center gap-1.5 text-sm transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/40",
            "disabled:opacity-50",
            isFavorite
              ? "text-[#E2725B] hover:text-[#c45e4a] dark:text-[#E2725B]"
              : "text-[#857370] hover:text-[#E2725B] dark:text-neutral-400 dark:hover:text-[#E2725B]",
          )}
        >
          <Heart
            className={cn(
              "h-4 w-4 transition-all",
              isFavorite ? "fill-[#E2725B] text-[#E2725B]" : "fill-none",
            )}
            aria-hidden="true"
          />
          {isFavorite ? "En favori" : "Ajouter aux favoris"}
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
            { value: "ingredients", label: "Ingredients" },
            { value: "instructions", label: "Instructions" },
            { value: "nutrition", label: "Nutrition" },
          ].map((tab) => (
            <RadixTabs.Trigger
              key={tab.value}
              value={tab.value}
              className={cn(
                "flex-1 px-2 py-3 text-sm font-medium transition-all",
                "border-b-2 border-transparent -mb-px",
                "text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-inset",
                "data-[state=active]:border-[#E2725B] data-[state=active]:text-[#E2725B]",
              )}
            >
              {tab.label}
            </RadixTabs.Trigger>
          ))}
        </RadixTabs.List>

        {/* Onglet Ingredients */}
        <RadixTabs.Content value="ingredients" className="focus-visible:outline-none">
          {safeIngredients.length === 0 ? (
            <p className="text-sm text-neutral-400 dark:text-neutral-500">
              Les ingredients ne sont pas disponibles pour cette recette.
            </p>
          ) : (
            <div>
              <p className="mb-4 text-xs text-[#857370] dark:text-neutral-400">
                Pour {recipe.servings ?? 4} personne{(recipe.servings ?? 4) > 1 ? "s" : ""}
              </p>

              <ul className="space-y-1">
                {safeIngredients.map((ingredient) => {
                  const isChecked = checkedIds.has(ingredient.id);
                  return (
                    <li key={ingredient.id}>
                      <label
                        className={cn(
                          "flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2.5 transition-colors",
                          "hover:bg-neutral-50 dark:hover:bg-neutral-800",
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleIngredient(ingredient.id)}
                          className="h-4 w-4 rounded border-neutral-300 accent-[#E2725B]
                            focus:ring-2 focus:ring-[#E2725B] focus:ring-offset-2"
                          aria-label={`${ingredient.name} -- ${ingredient.quantity} ${ingredient.unit}`}
                        />
                        <div className="flex flex-1 items-center justify-between gap-2">
                          <span
                            className={cn(
                              "text-sm text-neutral-800 dark:text-neutral-200",
                              isChecked && "text-neutral-400 line-through dark:text-neutral-500",
                            )}
                          >
                            {ingredient.name}
                            {ingredient.note && (
                              <span className="ml-1 text-xs text-neutral-400 dark:text-neutral-500">
                                ({ingredient.note})
                              </span>
                            )}
                          </span>
                          <span
                            className={cn(
                              "shrink-0 text-sm font-medium text-[#857370] dark:text-neutral-400",
                              isChecked && "text-neutral-300 line-through dark:text-neutral-600",
                            )}
                          >
                            {ingredient.quantity} {ingredient.unit}
                          </span>
                        </div>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </RadixTabs.Content>

        {/* Onglet Instructions */}
        <RadixTabs.Content value="instructions" className="focus-visible:outline-none">
          {sortedInstructions.length === 0 ? (
            <p className="text-sm text-neutral-400 dark:text-neutral-500">
              Les instructions pour cette recette ne sont pas encore disponibles.
            </p>
          ) : (
            <ol className="space-y-6" aria-label="Etapes de preparation">
              {sortedInstructions.map((step) => (
                <li key={step.stepNumber} className="flex gap-4">
                  {/* Cercle numerote terracotta */}
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#E2725B]">
                    <span
                      className="text-sm font-bold text-white"
                      aria-hidden="true"
                    >
                      {step.stepNumber}
                    </span>
                  </div>

                  <div className="flex-1 pt-1">
                    <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
                      {step.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </RadixTabs.Content>

        {/* Onglet Nutrition */}
        <RadixTabs.Content value="nutrition" className="focus-visible:outline-none">
          {hasNutrition ? (
            <div className="space-y-4">
              {/* Calories — badge principal */}
              <div className="rounded-xl border border-[#E2725B]/20 bg-[#fff8f6] p-5 text-center dark:border-[#E2725B]/30 dark:bg-[#E2725B]/10">
                <div className="font-mono text-3xl font-bold text-[#E2725B]">
                  {nutrition.calories} <span className="text-lg font-medium">kcal</span>
                </div>
                <div className="mt-1 text-xs font-medium text-[#857370] dark:text-neutral-400">
                  par portion
                </div>
              </div>

              {/* 3 macros : Proteines / Glucides / Lipides */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center dark:border-emerald-800 dark:bg-emerald-900/20">
                  <div className="font-mono text-xl font-bold text-emerald-700 dark:text-emerald-400">
                    {nutrition.proteins_g}g
                  </div>
                  <div className="mt-1 text-xs font-medium text-emerald-600 dark:text-emerald-500">
                    Proteines
                  </div>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center dark:border-amber-800 dark:bg-amber-900/20">
                  <div className="font-mono text-xl font-bold text-amber-700 dark:text-amber-400">
                    {nutrition.carbs_g}g
                  </div>
                  <div className="mt-1 text-xs font-medium text-amber-600 dark:text-amber-500">
                    Glucides
                  </div>
                </div>

                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-900/20">
                  <div className="font-mono text-xl font-bold text-blue-700 dark:text-blue-400">
                    {nutrition.fat_g}g
                  </div>
                  <div className="mt-1 text-xs font-medium text-blue-600 dark:text-blue-500">
                    Lipides
                  </div>
                </div>
              </div>

              {/* Fibres si disponibles */}
              {nutrition.fiber_g != null && (
                <div className="rounded-xl border border-lime-200 bg-lime-50 p-3 text-center dark:border-lime-800 dark:bg-lime-900/20">
                  <span className="font-mono text-base font-bold text-lime-700 dark:text-lime-400">
                    {nutrition.fiber_g}g
                  </span>
                  <span className="ml-2 text-xs font-medium text-lime-600 dark:text-lime-500">
                    Fibres
                  </span>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-center text-xs text-neutral-400 dark:text-neutral-500">
                Valeurs estimees par portion ({recipe.servings ?? 1} pers.)
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-8 text-center dark:border-neutral-700 dark:bg-neutral-800">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Les donnees nutritionnelles ne sont pas encore disponibles pour cette recette.
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
