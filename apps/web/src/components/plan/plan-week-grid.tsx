// apps/web/src/components/plan/plan-week-grid.tsx
// Grille semaine — mobile : feed vertical | desktop : bento grid 3 cols
// Référence : 04-components-catalog.md #04 PlanWeekGrid
// Stagger animation 80ms entre cards à l'apparition
"use client";

import { Plus } from "lucide-react";
import { MotionUl, MotionLi } from "@/components/motion";
import { RecipeCard } from "@/components/recipe/recipe-card";
import type { PlanDetail, PlannedMeal } from "@/lib/api/endpoints";

// Labels FR des jours de la semaine
const DAY_LABELS: Record<string, string> = {
  monday: "Lundi",
  tuesday: "Mardi",
  wednesday: "Mercredi",
  thursday: "Jeudi",
  friday: "Vendredi",
  saturday: "Samedi",
  sunday: "Dimanche",
};

const DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

interface PlanWeekGridProps {
  planDetail: PlanDetail;
  onSwapMeal?: (mealId: string) => void;
}

export function PlanWeekGrid({ planDetail, onSwapMeal }: PlanWeekGridProps) {
  // FIX Phase 1 mature (review 2026-04-12) — Mismatch D : backend retourne `meals`, pas `planned_meals`
  const { meals, recipes } = planDetail;

  // Indexer les recettes par ID pour accès O(1)
  const recipesById = new Map(recipes.map((r) => [r.id, r]));

  // Grouper les repas par jour dans l'ordre de la semaine
  const mealsByDay = new Map<string, PlannedMeal[]>();
  for (const day of DAY_ORDER) {
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
      {DAY_ORDER.map((day, index) => {
        const dayMeals = mealsByDay.get(day) ?? [];
        const dayLabel = DAY_LABELS[day] ?? day;

        return (
          <MotionLi
            key={day}
            variants={itemVariants}
            className="flex flex-col gap-3"
            role="gridcell"
            aria-label={`${dayLabel}${dayMeals.length === 0 ? " — aucun repas planifié" : ""}`}
          >
            {/* En-tête du jour */}
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
                const recipe = recipesById.get(meal.recipe_id);
                if (!recipe) return null;

                return (
                  <RecipeCard
                    key={meal.id}
                    recipe={recipe}
                    mealLabel={dayLabel}
                    variant="md"
                    priority={index < 2} // Priorité pour les 2 premières cards
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
