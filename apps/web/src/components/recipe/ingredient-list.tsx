// apps/web/src/components/recipe/ingredient-list.tsx
// Liste d'ingrédients groupée par catégorie avec checkbox "j'ai déjà"
// Référence : 04-components-catalog.md #20 ShoppingListItem (même pattern)
"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Ingredient, IngredientCategory } from "@/lib/api/types";

interface IngredientListProps {
  ingredients: Ingredient[];
  servings: number;
  servingsOverride?: number;
}

// Labels FR des catégories d'ingrédients
const CATEGORY_LABELS: Record<IngredientCategory, string> = {
  vegetables: "🥦 Légumes",
  fruits: "🍎 Fruits",
  meat: "🥩 Viandes",
  fish: "🐟 Poissons",
  dairy: "🥛 Produits laitiers",
  grains: "🌾 Féculents & céréales",
  legumes: "🫘 Légumineuses",
  condiments: "🧂 Condiments",
  herbs: "🌿 Herbes & épices",
  other: "🛒 Autre",
};

const CATEGORY_ORDER: IngredientCategory[] = [
  "vegetables", "fruits", "meat", "fish", "dairy", "grains",
  "legumes", "condiments", "herbs", "other",
];

export function IngredientList({ ingredients, servings, servingsOverride }: IngredientListProps) {
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  // Ratio d'ajustement des quantités selon le nombre de portions
  const ratio = servingsOverride ? servingsOverride / servings : 1;

  // Grouper par catégorie
  const byCategory = new Map<IngredientCategory, Ingredient[]>();
  for (const ingredient of ingredients) {
    const group = byCategory.get(ingredient.category) ?? [];
    group.push(ingredient);
    byCategory.set(ingredient.category, group);
  }

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

  return (
    <div className="space-y-6">
      {CATEGORY_ORDER.map((category) => {
        const items = byCategory.get(category);
        if (!items?.length) return null;

        return (
          <div key={category}>
            {/* En-tête de catégorie */}
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              {CATEGORY_LABELS[category]}
            </h3>

            {/* Liste d'ingrédients */}
            <ul className="space-y-2">
              {items.map((ingredient) => {
                const isChecked = checkedIds.has(ingredient.id);
                const adjustedQuantity =
                  ratio !== 1
                    ? Math.round(ingredient.quantity * ratio * 10) / 10
                    : ingredient.quantity;

                return (
                  <li key={ingredient.id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg p-2 transition-colors",
                        "hover:bg-neutral-50 dark:hover:bg-neutral-800",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleIngredient(ingredient.id)}
                        className="mt-0.5 h-4 w-4 rounded border-neutral-300 accent-primary-500
                          focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                        aria-label={`${ingredient.name} — ${adjustedQuantity} ${ingredient.unit}`}
                      />
                      <div className="flex flex-1 items-start justify-between gap-2">
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
                            "shrink-0 text-sm text-neutral-500 dark:text-neutral-400",
                            isChecked && "text-neutral-300 line-through dark:text-neutral-600",
                          )}
                        >
                          {adjustedQuantity} {ingredient.unit}
                        </span>
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
