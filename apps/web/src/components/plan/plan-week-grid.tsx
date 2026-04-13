// apps/web/src/components/plan/plan-week-grid.tsx
// Grille semaine — mobile : feed vertical | desktop : bento grid 3 cols
// Reference : 04-components-catalog.md #04 PlanWeekGrid
// Stagger animation 80ms entre cards a l'apparition
// FIX BLOQUANT 4 (2026-04-12) : day_of_week int (1-7 ISO) au lieu de strings
// Refonte dashboard (2026-04-12) :
//   - Bouton "Changer" overlay au hover sur chaque RecipeCard (status=draft)
//   - Boutons "Ajouter samedi" / "Ajouter dimanche" si absents du plan
//   - Mode lecture seule si status=validated (pas de swap/regenerer)
"use client";

import { Plus, RefreshCw } from "lucide-react";
import { MotionUl, MotionLi } from "@/components/motion";
import { RecipeCard } from "@/components/recipe/recipe-card";
import { cn } from "@/lib/utils";
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

// Jours de la semaine de base (lundi → vendredi)
const WEEKDAY_NUMBERS = [1, 2, 3, 4, 5] as const;
// Jours weekend optionnels
const SATURDAY = 6;
const SUNDAY = 7;

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
  /** Callback swap : ouvre le panel de suggestions pour remplacer un repas */
  onSwapMeal?: (mealId: string) => void;
  /** Callback ajout : ouvre le panel de suggestions pour ajouter un repas le weekend */
  onAddDay?: (dayOfWeek: number) => void;
}

export function PlanWeekGrid({ planDetail, onSwapMeal, onAddDay }: PlanWeekGridProps) {
  const { meals, status } = planDetail;
  const isDraft = status === "draft";

  // FIX BLOQUANT 4 : grouper les meals par day_of_week (int 1-7)
  const mealsByDay = new Map<number, PlannedMeal[]>();
  for (const { day } of DAYS_FR) {
    mealsByDay.set(day, []);
  }
  for (const meal of meals) {
    const dayMeals = mealsByDay.get(meal.day_of_week);
    if (dayMeals) dayMeals.push(meal);
  }

  // Determiner quels jours afficher : lundi-vendredi + samedi/dimanche s'ils ont des repas
  const hasSaturday = (mealsByDay.get(SATURDAY) ?? []).length > 0;
  const hasSunday = (mealsByDay.get(SUNDAY) ?? []).length > 0;

  const visibleDays = DAYS_FR.filter(({ day }) => {
    // Toujours afficher lundi-vendredi
    if (WEEKDAY_NUMBERS.includes(day as 1 | 2 | 3 | 4 | 5)) return true;
    // Afficher samedi/dimanche seulement s'ils ont des repas
    if (day === SATURDAY && hasSaturday) return true;
    if (day === SUNDAY && hasSunday) return true;
    return false;
  });

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
    <div className="space-y-4">
      {/* Grille principale */}
      <MotionUl
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
        role="grid"
        aria-label="Planning de la semaine"
      >
        {visibleDays.map(({ day, label: dayLabel }, index) => {
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
                    <div key={meal.id} className="group/card relative">
                      <RecipeCard
                        recipe={recipe}
                        mealLabel={dayLabel}
                        variant="md"
                        priority={index < 2}
                        // Swap inline pour la RecipeCard (bouton "Remplacer cette recette")
                        onSwap={isDraft && onSwapMeal ? () => onSwapMeal(meal.id) : undefined}
                      />

                      {/* Bouton "Changer" overlay — visible au hover, uniquement en mode draft */}
                      {isDraft && onSwapMeal && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onSwapMeal(meal.id);
                          }}
                          className={cn(
                            "absolute right-3 top-3 z-10",
                            "flex h-8 w-8 items-center justify-center rounded-full",
                            "bg-white/90 text-[#857370] shadow-sm backdrop-blur-sm",
                            "opacity-0 transition-all duration-200 group-hover/card:opacity-100",
                            "hover:bg-[#E2725B] hover:text-white",
                            "focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]",
                          )}
                          aria-label={`Changer la recette de ${dayLabel}`}
                        >
                          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      )}
                    </div>
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

      {/* Boutons "Ajouter samedi" / "Ajouter dimanche" — uniquement en mode draft */}
      {isDraft && onAddDay && (!hasSaturday || !hasSunday) && (
        <div className="flex flex-wrap gap-3">
          {!hasSaturday && (
            <AddDayButton
              label="Ajouter samedi"
              onClick={() => onAddDay(SATURDAY)}
            />
          )}
          {!hasSunday && (
            <AddDayButton
              label="Ajouter dimanche"
              onClick={() => onAddDay(SUNDAY)}
            />
          )}
        </div>
      )}
    </div>
  );
}

// Slot vide — invite a ajouter un repas
function EmptyDaySlot({ dayLabel }: { dayLabel: string }) {
  return (
    <div
      className="flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-2xl
        border-2 border-dashed border-neutral-200 bg-neutral-50 p-4
        dark:border-neutral-700 dark:bg-neutral-800/50"
      aria-label={`${dayLabel} — aucun repas planifie`}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700">
        <Plus className="h-4 w-4 text-neutral-400" aria-hidden="true" />
      </div>
      <span className="text-center text-xs text-neutral-400">Aucun repas planifie</span>
    </div>
  );
}

// Bouton pour ajouter samedi ou dimanche
function AddDayButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-xl px-4 py-3",
        "border-2 border-dashed border-[#E2725B]/30 bg-[#E2725B]/5",
        "text-sm font-medium text-[#E2725B]",
        "transition-all duration-200",
        "hover:border-[#E2725B]/50 hover:bg-[#E2725B]/10",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B] focus-visible:ring-offset-2",
        "min-h-[44px]",
      )}
    >
      <Plus className="h-4 w-4" aria-hidden="true" />
      {label}
    </button>
  );
}
