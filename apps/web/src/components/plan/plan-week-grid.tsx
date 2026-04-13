// apps/web/src/components/plan/plan-week-grid.tsx
// Grille semaine compacte — 1 col mobile, 2 tablette, 5 desktop (1 par jour)
// Cards reduites : image aspect-[4/3], titre text-xs, badge temps overlay
// Reference : 04-components-catalog.md #04 PlanWeekGrid
// Stagger animation 80ms entre cards a l'apparition
// FIX BLOQUANT 4 (2026-04-12) : day_of_week int (1-7 ISO) au lieu de strings
// FIX BUG 2 (2026-04-12) : cards trop grandes — passage en grille compacte 5 cols
"use client";

import Image from "next/image";
import Link from "next/link";
import { Plus, RefreshCw } from "lucide-react";
import { MotionDiv } from "@/components/motion";
import { cn } from "@/lib/utils";
import type { PlanDetail, PlannedMeal } from "@/lib/api/endpoints";

// Image placeholder pour les recettes sans photo
const PLACEHOLDER =
  "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=800&auto=format&fit=crop";

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
    if (WEEKDAY_NUMBERS.includes(day as 1 | 2 | 3 | 4 | 5)) return true;
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
      {/* Grille compacte : 1 col mobile, 2 tablette, 5 desktop */}
      <div
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5"
        role="grid"
        aria-label="Planning de la semaine"
      >
        {visibleDays.map(({ day, label: dayLabel }, index) => {
          const dayMeals = mealsByDay.get(day) ?? [];
          const meal = dayMeals[0];

          return (
            <MotionDiv
              key={day}
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              className="group relative"
              role="gridcell"
              aria-label={`${dayLabel}${!meal ? " — aucun repas planifie" : ""}`}
            >
              {/* En-tete du jour */}
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-[#857370]">
                {dayLabel}
              </p>

              {meal ? (
                <Link
                  href={`/recipes/${meal.recipe_id}`}
                  className="relative block overflow-hidden rounded-xl bg-white shadow-sm transition-shadow hover:shadow-md"
                >
                  {/* Image compacte — ratio 4:3 */}
                  <div className="relative aspect-[4/3] overflow-hidden">
                    <Image
                      src={meal.recipe_photo_url || PLACEHOLDER}
                      alt={meal.recipe_title ?? "Recette"}
                      fill
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 20vw"
                      className="object-cover transition-transform duration-500 group-hover:scale-105"
                      priority={index < 2}
                    />

                    {/* Badge temps — overlay bas-droite */}
                    {meal.recipe_total_time_min != null && meal.recipe_total_time_min > 0 && (
                      <span className="absolute bottom-1.5 right-1.5 rounded-full bg-[#E2725B]/90 px-2 py-0.5 text-[10px] font-semibold text-white">
                        {meal.recipe_total_time_min} min
                      </span>
                    )}

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
                          "absolute right-1.5 top-1.5",
                          "flex h-7 w-7 items-center justify-center rounded-full",
                          "bg-white/80 text-[#857370] backdrop-blur-sm",
                          "opacity-0 transition-all duration-200 group-hover:opacity-100",
                          "hover:bg-[#E2725B] hover:text-white",
                          "focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]",
                        )}
                        aria-label={`Changer la recette de ${dayLabel}`}
                      >
                        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </div>

                  {/* Titre compact */}
                  <p className="p-2 text-xs font-medium leading-tight text-[#201a19] line-clamp-2">
                    {meal.recipe_title ?? "Recette"}
                  </p>
                </Link>
              ) : (
                <EmptyDaySlot dayLabel={dayLabel} />
              )}
            </MotionDiv>
          );
        })}
      </div>

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

// Slot vide compact — invite a ajouter un repas
function EmptyDaySlot({ dayLabel }: { dayLabel: string }) {
  return (
    <div
      className="flex aspect-[4/3] flex-col items-center justify-center gap-1.5 rounded-xl
        border-2 border-dashed border-neutral-200 bg-neutral-50
        dark:border-neutral-700 dark:bg-neutral-800/50"
      aria-label={`${dayLabel} — aucun repas planifie`}
    >
      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700">
        <Plus className="h-3.5 w-3.5 text-neutral-400" aria-hidden="true" />
      </div>
      <span className="text-center text-[10px] text-neutral-400">Aucun repas</span>
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
