// apps/web/src/app/(app)/shopping-list/page.tsx
// Page liste de courses — groupée par rayon, checkboxes interactives
// Fetch GET /api/v1/plans/me/{plan_id}/shopping-list
// Bouton "Envoyer au drive" : disabled Phase 1, actif Phase 3
"use client";

import { useSearchParams } from "next/navigation";
import { ShoppingCart, Truck, Loader2 } from "lucide-react";
import { useShoppingList, useToggleItem } from "@/hooks/use-shopping-list";
import { useCurrentPlan } from "@/hooks/use-plan";
import { ShoppingListItem } from "@/components/shopping/shopping-list-item";
import type { ShoppingListItem as ShoppingListItemType, IngredientCategory } from "@/lib/api/types";

// Ordre d'affichage des rayons en supermarché français
const RAYON_ORDER: IngredientCategory[] = [
  "vegetables", "fruits", "meat", "fish", "dairy",
  "grains", "legumes", "condiments", "herbs", "other",
];

const RAYON_LABELS: Record<IngredientCategory, string> = {
  vegetables: "🥦 Fruits & Légumes",
  fruits: "🍎 Fruits",
  meat: "🥩 Boucherie",
  fish: "🐟 Poissonnerie",
  dairy: "🥛 Crèmerie",
  grains: "🌾 Épicerie",
  legumes: "🫘 Légumineuses",
  condiments: "🧂 Condiments",
  herbs: "🌿 Herbes & épices",
  other: "🛒 Divers",
};

export default function ShoppingListPage() {
  const searchParams = useSearchParams();
  const planIdFromQuery = searchParams.get("plan");

  // Récupérer l'ID du plan courant si non fourni en query
  const { data: currentPlan } = useCurrentPlan();
  // FIX BLOQUANT 3 : PlanDetail est plat — id directement sur l'objet
  const planId = planIdFromQuery ?? currentPlan?.id ?? null;

  const { data: items = [], isLoading, error } = useShoppingList(planId);
  const toggleMutation = useToggleItem(planId ?? "");

  // Grouper les items par catégorie/rayon
  const byCategory = new Map<IngredientCategory, ShoppingListItemType[]>();
  for (const item of items) {
    const group = byCategory.get(item.category) ?? [];
    group.push(item);
    byCategory.set(item.category, group);
  }

  // Calculer la progression (items cochés)
  const checkedCount = items.filter((item) => item.is_checked).length;
  const totalCount = items.length;
  const progressPercent = totalCount > 0 ? Math.round((checkedCount / totalCount) * 100) : 0;

  function handleToggle(itemId: string, isChecked: boolean) {
    toggleMutation.mutate({ itemId, isChecked });
  }

  if (!planId) {
    return (
      <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
        <ShoppingCart className="mb-4 h-12 w-12 text-neutral-300" aria-hidden="true" />
        <h1 className="font-serif mb-2 text-xl font-bold text-neutral-900 dark:text-neutral-100">
          Aucun planning actif
        </h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Générez un planning hebdomadaire pour voir votre liste de courses.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary-400" aria-hidden="true" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
        <ShoppingCart className="mb-4 h-12 w-12 text-red-300" aria-hidden="true" />
        <h1 className="font-serif mb-2 text-xl font-bold text-neutral-900 dark:text-neutral-100">
          Erreur de chargement
        </h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Impossible de charger la liste de courses. Réessayez plus tard.
        </p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
        <ShoppingCart className="mb-4 h-12 w-12 text-neutral-300" aria-hidden="true" />
        <h1 className="font-serif mb-2 text-xl font-bold text-neutral-900 dark:text-neutral-100">
          Liste vide
        </h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Votre liste de courses apparaîtra ici une fois votre planning validé.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-full pb-32">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-neutral-200 bg-white px-4 py-4 dark:border-neutral-700 dark:bg-neutral-900">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-serif text-2xl font-bold text-neutral-900 dark:text-neutral-100">
              Ma liste de courses
            </h1>
            <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">
              {checkedCount} / {totalCount} articles
            </p>
          </div>

          {/* Progression visuelle */}
          <div className="flex h-12 w-12 items-center justify-center">
            <svg viewBox="0 0 44 44" className="h-12 w-12 -rotate-90" aria-hidden="true">
              <circle
                cx="22"
                cy="22"
                r="18"
                stroke="hsl(38,20%,89%)"
                strokeWidth="4"
                fill="none"
              />
              <circle
                cx="22"
                cy="22"
                r="18"
                stroke="hsl(14,75%,55%)"
                strokeWidth="4"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 18}`}
                strokeDashoffset={`${2 * Math.PI * 18 * (1 - progressPercent / 100)}`}
                strokeLinecap="round"
                className="transition-all duration-slow"
              />
            </svg>
          </div>
        </div>

        {/* Barre de progression */}
        <div
          className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-700"
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${progressPercent}% des articles cochés`}
        >
          <div
            className="h-full rounded-full bg-primary-500 transition-all duration-slow"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Liste groupée par rayon */}
      <div className="divide-y divide-neutral-100 dark:divide-neutral-700/50">
        {RAYON_ORDER.map((category) => {
          const categoryItems = byCategory.get(category);
          if (!categoryItems?.length) return null;

          const allChecked = categoryItems.every((item) => item.is_checked);

          return (
            <section key={category}>
              {/* En-tête de rayon sticky */}
              <div className="sticky top-[105px] z-[5] border-b border-neutral-100 bg-neutral-50 px-4 py-2 dark:border-neutral-700/50 dark:bg-neutral-900/80">
                <h2
                  className={`text-xs font-semibold uppercase tracking-wide ${
                    allChecked ? "text-neutral-400" : "text-neutral-600 dark:text-neutral-400"
                  }`}
                >
                  {RAYON_LABELS[category]}
                  <span className="ml-1 font-normal text-neutral-400">
                    ({categoryItems.filter((i) => i.is_checked).length}/{categoryItems.length})
                  </span>
                </h2>
              </div>

              {/* Items du rayon */}
              <ul>
                {categoryItems.map((item) => (
                  <li
                    key={item.id}
                    className="border-b border-neutral-100 dark:border-neutral-700/30"
                  >
                    <ShoppingListItem
                      item={item}
                      onToggle={handleToggle}
                    />
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>

      {/* Bouton flottant "Envoyer au drive" */}
      <div className="fixed bottom-20 left-1/2 -translate-x-1/2 px-4 lg:bottom-6">
        <button
          type="button"
          disabled // Phase 1 — actif en Phase 3 avec intégration drive
          aria-disabled="true"
          className="inline-flex min-h-[52px] items-center gap-2 rounded-2xl bg-neutral-300
            px-6 py-3 font-semibold text-neutral-500 shadow-lg
            cursor-not-allowed dark:bg-neutral-700 dark:text-neutral-400"
          title="Disponible en Phase 3 — intégration drive"
        >
          <Truck className="h-5 w-5" aria-hidden="true" />
          Envoyer au drive
          <span className="ml-1 rounded-full bg-neutral-200 px-2 py-0.5 text-xs dark:bg-neutral-600">
            Bientôt
          </span>
        </button>
      </div>
    </div>
  );
}
