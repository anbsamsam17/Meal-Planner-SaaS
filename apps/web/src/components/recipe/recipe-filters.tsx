"use client";
// apps/web/src/components/recipe/recipe-filters.tsx
// Filtres avancés pour la recherche de recettes
// Phase 2 — budget chips, slider temps, difficulté, régime multi-select, cuisine chips (top 10)
// Refonte 2026-04-12 : filtre budget FR, difficulté 1-5, régime tags FR, cuisine top 10

import { useState, useCallback } from "react";
import { SlidersHorizontal, X, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RecipeFilters, DietaryTag } from "@/lib/api/types";

// --- Constantes des options de filtres ---

const BUDGET_OPTIONS: { value: RecipeFilters["budget"]; label: string }[] = [
  { value: "économique", label: "Économique" },
  { value: "moyen", label: "Moyen" },
  { value: "premium", label: "Premium" },
];

const DIET_OPTIONS: { value: DietaryTag; label: string }[] = [
  { value: "végétarien", label: "Végétarien" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten-free", label: "Sans gluten" },
  { value: "lactose-free", label: "Sans lactose" },
  { value: "no-pork", label: "Sans porc" },
  { value: "no-seafood", label: "Sans fruits de mer" },
  { value: "halal", label: "Halal" },
  { value: "nut-free", label: "Sans fruits à coque" },
];

// Top 10 cuisines uniquement (spéc. correction 2 + 5)
const TOP_CUISINES: { value: string; label: string }[] = [
  { value: "française", label: "Française" },
  { value: "italienne", label: "Italienne" },
  { value: "indienne", label: "Indienne" },
  { value: "japonaise", label: "Japonaise" },
  { value: "mexicaine", label: "Mexicaine" },
  { value: "thaïlandaise", label: "Thaïlandaise" },
  { value: "chinoise", label: "Chinoise" },
  { value: "espagnole", label: "Espagnole" },
  { value: "américaine", label: "Américaine" },
  { value: "britannique", label: "Britannique" },
];

// Difficulté 1-5 → labels FR
const DIFFICULTY_OPTIONS: { value: 1 | 2 | 3 | 4 | 5; label: string }[] = [
  { value: 1, label: "Très facile" },
  { value: 2, label: "Facile" },
  { value: 3, label: "Moyen" },
  { value: 4, label: "Difficile" },
  { value: 5, label: "Très difficile" },
];

// --- Composants utilitaires ---

interface ChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function Chip({ label, active, onClick }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex min-h-[36px] items-center rounded-full px-3 py-1 text-xs font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50 focus-visible:ring-offset-1",
        active
          ? "bg-[#E2725B] text-white border border-[#E2725B]"
          : "border border-neutral-200 bg-white text-neutral-600 hover:border-[#E2725B]/40 hover:bg-[#E2725B]/5",
      )}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}

// --- Props du composant principal ---

interface RecipeFiltersProps {
  filters: RecipeFilters;
  onChange: (filters: RecipeFilters) => void;
  resultCount?: number;
}

const DEFAULT_FILTERS: RecipeFilters = {};

export function RecipeFiltersPanel({ filters, onChange, resultCount }: RecipeFiltersProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const updateFilter = useCallback(
    <K extends keyof RecipeFilters>(key: K, value: RecipeFilters[K]) => {
      onChange({ ...filters, [key]: value });
    },
    [filters, onChange],
  );

  // Régime : multi-select via tableau DietaryTag[]
  function toggleDiet(diet: DietaryTag) {
    const current = Array.isArray(filters.diet)
      ? filters.diet
      : filters.diet
        ? [filters.diet]
        : [];
    const next = current.includes(diet)
      ? current.filter((d) => d !== diet)
      : [...current, diet];
    onChange({ ...filters, diet: next.length > 0 ? (next as DietaryTag[]) : undefined });
  }

  function isDietActive(diet: DietaryTag): boolean {
    if (!filters.diet) return false;
    const current = Array.isArray(filters.diet) ? filters.diet : [filters.diet];
    return current.includes(diet);
  }

  // Difficulté : un seul niveau sélectionnable (max_difficulty implicite)
  function handleDifficulty(level: 1 | 2 | 3 | 4 | 5) {
    updateFilter("difficulty", filters.difficulty === level ? undefined : level);
  }

  function handleReset() {
    onChange(DEFAULT_FILTERS);
  }

  const hasActiveFilters =
    !!filters.budget ||
    !!filters.cuisine ||
    !!filters.difficulty ||
    filters.max_time != null ||
    (Array.isArray(filters.diet) ? filters.diet.length > 0 : !!filters.diet);

  const filtersContent = (
    <div className="space-y-6">
      {/* Budget */}
      <section aria-labelledby="filter-budget">
        <h3
          id="filter-budget"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
        >
          Budget
        </h3>
        <div className="flex flex-wrap gap-2">
          {BUDGET_OPTIONS.map(({ value, label }) => (
            <Chip
              key={label}
              label={label}
              active={filters.budget === value}
              onClick={() => updateFilter("budget", filters.budget === value ? undefined : value)}
            />
          ))}
        </div>
      </section>

      {/* Temps max */}
      <section aria-labelledby="filter-time">
        <h3
          id="filter-time"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
        >
          Temps max :{" "}
          <span className="font-bold text-neutral-800">
            {filters.max_time != null ? `${filters.max_time} min` : "Tous"}
          </span>
        </h3>
        <input
          type="range"
          min={15}
          max={120}
          step={5}
          value={filters.max_time ?? 120}
          onChange={(e) => {
            const val = Number(e.target.value);
            // 120 = pas de filtre (valeur max du slider)
            updateFilter("max_time", val === 120 ? undefined : val);
          }}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-neutral-200 accent-[#E2725B]"
          aria-label={`Temps maximum : ${filters.max_time ?? 120} minutes`}
        />
        <div className="flex justify-between text-xs text-neutral-400">
          <span>15 min</span>
          <span>2 h</span>
        </div>
      </section>

      {/* Difficulté 1-5 */}
      <section aria-labelledby="filter-difficulty">
        <h3
          id="filter-difficulty"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
        >
          Difficulté
        </h3>
        <div className="flex flex-wrap gap-2">
          {DIFFICULTY_OPTIONS.map(({ value, label }) => (
            <Chip
              key={value}
              label={label}
              active={filters.difficulty === value}
              onClick={() => handleDifficulty(value)}
            />
          ))}
        </div>
      </section>

      {/* Régime alimentaire */}
      <section aria-labelledby="filter-diet">
        <h3
          id="filter-diet"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
        >
          Régime
        </h3>
        <div className="flex flex-wrap gap-2">
          {DIET_OPTIONS.map(({ value, label }) => (
            <Chip
              key={value}
              label={label}
              active={isDietActive(value)}
              onClick={() => toggleDiet(value)}
            />
          ))}
        </div>
      </section>

      {/* Cuisine — top 10 uniquement */}
      <section aria-labelledby="filter-cuisine">
        <h3
          id="filter-cuisine"
          className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500"
        >
          Cuisine
        </h3>
        <div className="flex flex-wrap gap-2">
          {TOP_CUISINES.map(({ value, label }) => (
            <Chip
              key={value}
              label={label}
              active={filters.cuisine === value}
              onClick={() =>
                updateFilter("cuisine", filters.cuisine === value ? undefined : value)
              }
            />
          ))}
        </div>
      </section>

      {/* Bouton reset */}
      {hasActiveFilters && (
        <button
          type="button"
          onClick={handleReset}
          className="inline-flex min-h-[36px] items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden />
          Réinitialiser
        </button>
      )}
    </div>
  );

  return (
    <>
      {/* Bouton filtres mobile */}
      <div className="lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className={cn(
            "inline-flex min-h-[44px] items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50",
            hasActiveFilters
              ? "border-[#E2725B]/40 bg-[#E2725B]/5 text-[#E2725B]"
              : "border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50",
          )}
          aria-label="Ouvrir les filtres"
        >
          <SlidersHorizontal className="h-4 w-4" aria-hidden />
          Filtres
          {hasActiveFilters && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#E2725B] text-[10px] font-bold text-white">
              !
            </span>
          )}
          {resultCount != null && (
            <span className="text-xs text-neutral-400">({resultCount})</span>
          )}
        </button>
      </div>

      {/* Sheet mobile */}
      {mobileOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Filtres de recherche"
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 lg:hidden"
          onClick={(e) => e.target === e.currentTarget && setMobileOpen(false)}
        >
          <div
            className="w-full rounded-t-2xl bg-white p-6 shadow-xl"
            style={{ maxHeight: "85dvh", overflowY: "auto" }}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-neutral-900">Filtres</h2>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50"
                aria-label="Fermer les filtres"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>
            {filtersContent}
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="mt-6 inline-flex min-h-[44px] w-full items-center justify-center rounded-lg bg-[#E2725B] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#E2725B]/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50"
            >
              Voir les résultats
              {resultCount != null && ` (${resultCount})`}
            </button>
          </div>
        </div>
      )}

      {/* Sidebar desktop */}
      <aside className="hidden w-64 flex-shrink-0 lg:block" aria-label="Filtres de recherche">
        <div className="rounded-xl border border-neutral-200 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-900">Filtres</h2>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleReset}
                className="rounded-lg p-1 text-neutral-400 hover:text-[#E2725B] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/50"
                aria-label="Réinitialiser les filtres"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden />
              </button>
            )}
          </div>
          {filtersContent}
        </div>
      </aside>
    </>
  );
}
