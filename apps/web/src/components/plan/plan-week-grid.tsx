// apps/web/src/components/plan/plan-week-grid.tsx
// Grille semaine — mobile : feed vertical | desktop : bento grid 3 cols
// Reference : 04-components-catalog.md #04 PlanWeekGrid
// Stagger animation 80ms entre cards a l'apparition
// FIX BLOQUANT 4 (2026-04-12) : day_of_week int (1-7 ISO) au lieu de strings
"use client";

import { Plus } from "lucide-react";
import { MotionUl, MotionLi } from "@/components/motion";
import { RecipeCard } from "@/components/recipe/recipe-card";
import type { PlanDetail, PlannedMeal } from "@/lib/api/endpoints";
import type { Recipe } from "@/lib/api/types";

// FIX BLOQUANT 4 : mapping int ISO (1=lundi) vers labels FR
const DAYS_FR: { day: number; label: string; short: string }[] = [
  { day: 1, label: "Lundi", short: "Lun" },
  { day: 2, label: "Mardi", short: "Mar" },
  { day: 3, label: "Mercredi", short: "Mer" },
  { day: 4, label: "Jeudi", short: "Jeu" },
  { day: 5, label: "Vendredi", short: "Ven" },
  { day: 6, label: "Samedi", short: "Sam" },
  { day: 7, label: "Dimanche", short: "Dim" },
];

// Reconstruit un objet Recipe minimal depuis les champs denormalises de PlannedMeal
// Le backend ne retourne pas un tableau `recipes[]` separe, mais des champs recipe_* sur chaque meal
function buildRecipeFromMeal(meal: PlannedMeal): Recipe {
  return {
    id: meal.recipe_id,
    title: meal.recipe_title ?? "Recette",
    photo_url: meal.recipe_photo_url ?? null,
    image_url: meal.recipe_photo_url ?? null,
    total_time_min: meal.recipe_total_time_min ?? null,
    total_time_minutes: meal.recipe_total_time_min ?? null,
    difficulty: meal.recipe_difficulty ?? null,
    cuisine_type: meal.recipe_cuisine_type ?? null,
    cuisine: meal.recipe_cuisine_type ?? null,
  };
}

interface PlanWeekGridProps {
  planDetail: PlanDetail;
  onSwapMeal?: (mealId: string) => void;
}

export function PlanWeekGrid({ planDetail, onSwapMeal }: PlanWeekGridProps) {
  const { meals } = planDetail;

  // FIX BLOQUANT 4 : grouper les meals par day_of_week (int 1-7)
  const mealsByDay = new Map<number, PlannedMeal[]>();
  for (const { day } of DAYS_FR) {
    mealsByDay.set(day, []);
  }
  for (const meal of meals) {
    const dayMeals = mealsByDay.get(meal.day_of_week);
    if (dayMeals) dayMeals.push(meal);
  }

  // Animation stagger — 80ms entre cards (motion-principles.md)
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.08 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: "spring" as const, stiffness: 300, damping: 30 },
    },
  };

  return (
    <MotionUl
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      role="grid"
      aria-label="Planning de la semaine"
    >
      {DAYS_FR.map(({ day, label: dayLabel }, index) => {
        const dayMeals = mealsByDay.get(day) ?? [];

        return (
          <MotionLi
            key={day}
            variants={itemVariants}
            className="flex flex-col gap-3"
            role="gridcell"
            aria-label={`${dayLabel}${dayMeals.length === 0 ? " — aucun repas planifie" : ""}`}
          >
            {/* En-tete du jour */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
                {dayLabel}
              </span>
              {dayMeals.length === 0 && (
                <span className="text-xs text-neutral-400">Pas de repas</span>
              )}
            </div>

            {/* Recettes du jour */}
            {dayMeals.length > 0 ? (
              dayMeals.map((meal) => {
                // FIX BLOQUANT 4 : construire Recipe depuis les champs enrichis du meal
                const recipe = buildRecipeFromMeal(meal);

                return (
                  <RecipeCard
                    key={meal.id}
                    recipe={recipe}
                    mealLabel={dayLabel}
                    variant="md"
                    priority={index < 2}
                    onSwap={onSwapMeal ? () => onSwapMeal(meal.id) : undefined}
                  />
                );
              })
            ) : (
              // Slot vide
              <EmptyDaySlot dayLabel={dayLabel} />
            )}
          </MotionLi>
        );
      })}
    </MotionUl>
  );
}

// Slot vide — invite à ajouter un repas
function EmptyDaySlot({ dayLabel }: { dayLabel: string }) {
  return (
    <div
      className="flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-2xl
        border-2 border-dashed border-neutral-200 bg-neutral-50 p-4
        dark:border-neutral-700 dark:bg-neutral-800/50"
      aria-label={`${dayLabel} — aucun repas planifié`}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700">
        <Plus className="h-4 w-4 text-neutral-400" aria-hidden="true" />
      </div>
      <span className="text-center text-xs text-neutral-400">Aucun repas planifié</span>
    </div>
  );
}
