"use client";
// apps/web/src/app/(app)/recipes/recipes-explorer.tsx
// Explorer de recettes avec filtres avancés — Client Component
// Phase 2 — barre de recherche arrondie premium, pills filtres, grid portrait 2→3 col
// Refonte 2026-04-12 : pagination numérotée, filtres corrigés, cards enrichies, FR complet

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, SlidersHorizontal, Link2 } from "lucide-react";
import { useDebounce } from "@/hooks/use-debounce";
import { searchRecipesAdvanced } from "@/lib/api/endpoints";
import type { RecipeFilters, PaginatedResponse } from "@/lib/api/types";
import type { Recipe } from "@/lib/api/types";
import { RecipeCard } from "@/components/recipe/recipe-card";
import { RecipeFiltersPanel } from "@/components/recipe/recipe-filters";
import { ImportUrlModal } from "@/components/recipe/import-url-modal";

const PER_PAGE = 24;
const DEFAULT_FILTERS: RecipeFilters = { per_page: PER_PAGE };

// Pills rapides — 4 seulement, pas de cuisines individuelles (spéc. correction 5)
const QUICK_FILTERS = [
  { label: "Rapide (< 15 min)", key: "quick" },
  { label: "Desserts", key: "dessert" },
  { label: "Végétarien", key: "vegetarian" },
  { label: "Facile", key: "easy" },
] as const;

type QuickFilterKey = (typeof QUICK_FILTERS)[number]["key"];

// --- Composant Pagination numérotée ---

interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}

function Pagination({ page, totalPages, onChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  // Construire la liste de numéros avec ellipses (-1)
  const pages: number[] = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - page) <= 1) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== -1) {
      pages.push(-1); // ellipsis
    }
  }

  return (
    <nav
      className="mt-8 flex items-center justify-center gap-2 flex-wrap"
      aria-label="Pagination"
    >
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="rounded-lg border border-[#857370]/20 px-3 py-2 text-sm disabled:opacity-30 hover:bg-[#E2725B]/10 transition-colors"
      >
        ← Précédent
      </button>

      {pages.map((p, i) =>
        p === -1 ? (
          <span key={`e${i}`} className="px-1 text-[#857370]">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            onClick={() => onChange(p)}
            aria-current={p === page ? "page" : undefined}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              p === page
                ? "bg-[#E2725B] text-white"
                : "border border-[#857370]/20 hover:bg-[#E2725B]/10"
            }`}
          >
            {p}
          </button>
        ),
      )}

      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
        className="rounded-lg border border-[#857370]/20 px-3 py-2 text-sm disabled:opacity-30 hover:bg-[#E2725B]/10 transition-colors"
      >
        Suivant →
      </button>
    </nav>
  );
}

// --- Composant principal ---

export function RecipesExplorer() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<RecipeFilters>(DEFAULT_FILTERS);
  const [activeQuickFilter, setActiveQuickFilter] = useState<QuickFilterKey | null>(null);
  const [page, setPage] = useState(1);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const debouncedQuery = useDebounce(searchQuery, 350);

  // Merge recherche textuelle + quick filter dans les filtres actifs.
  // IMP-04 fix : les quick filters s'AJOUTENT aux filtres existants — ils ne remplacent pas `q`
  // ni les autres filtres posés par la sidebar (cuisine, budget, etc.).
  // Pour "dessert" et "végétarien" : on ajoute le tag au tableau diet existant sans l'écraser.
  function buildActiveFilters(): RecipeFilters {
    const base: RecipeFilters = {
      ...filters,
      q: debouncedQuery || undefined,
      per_page: PER_PAGE,
      page,
    };

    if (activeQuickFilter === "quick") {
      // "Rapide" remplace max_time seulement si plus restrictif ou non défini
      base.max_time = base.max_time != null ? Math.min(base.max_time, 15) : 15;
    } else if (activeQuickFilter === "easy") {
      // "Facile" remplace difficulty seulement si non défini ou plus restrictif (max difficulty 2)
      const clamped = base.difficulty != null ? Math.min(base.difficulty as number, 2) : 2;
      base.difficulty = clamped as 1 | 2 | 3 | 4 | 5;
    } else if (activeQuickFilter === "dessert" || activeQuickFilter === "vegetarian") {
      // Ajouter le tag quick dans le tableau diet sans écraser les tags sidebar existants
      const quickTag = activeQuickFilter === "dessert" ? "dessert" : "végétarien";
      const existing = Array.isArray(base.diet)
        ? base.diet
        : base.diet
          ? [base.diet]
          : [];
      const merged = existing.includes(quickTag as any)
        ? existing
        : [...existing, quickTag];
      base.diet = merged.length > 0 ? (merged as typeof base.diet) : undefined;
    }

    return base;
  }

  const activeFilters = buildActiveFilters();

  const { data, isLoading, isError } = useQuery<PaginatedResponse<Recipe>, Error>({
    queryKey: ["recipes", "explore", activeFilters, page],
    queryFn: () => searchRecipesAdvanced(activeFilters),
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  // searchRecipesAdvanced normalise la réponse API (results → data) — lire directement data
  const recipes: Recipe[] = data?.data ?? [];
  const totalCount = data?.total ?? 0;
  const totalPages = Math.ceil(totalCount / PER_PAGE);

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handlePageChange(p: number) {
    setPage(p);
    scrollToTop();
  }

  function handleFiltersChange(newFilters: RecipeFilters) {
    setFilters({ ...newFilters, per_page: PER_PAGE });
    setPage(1); // Remettre à page 1 quand les filtres changent
  }

  function handleQuickFilter(key: QuickFilterKey) {
    setActiveQuickFilter((prev) => (prev === key ? null : key));
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
      {/* =========================================
          HEADER PREMIUM
      ========================================= */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#E2725B]">
            Découvrez de nouvelles saveurs
          </p>
          <h1 className="mt-2 font-serif text-3xl font-bold leading-tight text-[#201a19] md:text-4xl">
            Explorez +50&nbsp;000
            <br />
            recettes de chef
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setImportModalOpen(true)}
          className="mt-2 flex shrink-0 items-center gap-2 rounded-xl border border-[#E2725B]/30
            bg-white px-4 py-2.5 text-sm font-medium text-[#E2725B]
            transition-all hover:bg-[#E2725B]/5 hover:border-[#E2725B]/50
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/30"
        >
          <Link2 className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Importer une recette</span>
          <span className="sm:hidden">Importer</span>
        </button>
      </div>

      {/* =========================================
          BARRE DE RECHERCHE
      ========================================= */}
      <div className="mt-6 relative">
        <label htmlFor="recipe-search" className="sr-only">
          Rechercher une recette
        </label>
        <Search
          className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#857370]"
          aria-hidden
        />
        <input
          id="recipe-search"
          type="search"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(1);
          }}
          placeholder="Rechercher ingrédients, cuisines..."
          className="w-full rounded-full border-0 bg-[#E2725B]/5 py-3.5 pl-12 pr-4 text-sm text-[#201a19] placeholder:text-[#857370]/60 focus:outline-none focus:ring-2 focus:ring-[#E2725B]/30 transition-all duration-200"
        />
      </div>

      {/* =========================================
          PILLS FILTRES RAPIDES — 4 pills + bouton filtres
      ========================================= */}
      <div className="mt-4 flex gap-2 overflow-x-auto hide-scrollbar pb-2">
        <button
          type="button"
          onClick={() => {
            setActiveQuickFilter(null);
            setFilters(DEFAULT_FILTERS);
            setPage(1);
          }}
          className="flex shrink-0 items-center gap-1.5 rounded-full bg-[#E2725B] px-4 py-2 text-xs font-medium text-white whitespace-nowrap transition-opacity duration-200 hover:opacity-90"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          Tous les filtres
        </button>

        {QUICK_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => handleQuickFilter(f.key)}
            className={`shrink-0 rounded-full border px-4 py-2 text-xs font-medium whitespace-nowrap transition-colors duration-200 ${
              activeQuickFilter === f.key
                ? "border-[#E2725B] bg-[#E2725B] text-white"
                : "border-[#857370]/20 bg-white text-[#201a19] hover:border-[#E2725B]/40"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* =========================================
          LAYOUT : filtres sidebar + grille résultats
      ========================================= */}
      <div className="mt-6 flex gap-6">
        {/* Filtres avancés — sidebar desktop / sheet mobile */}
        <RecipeFiltersPanel
          filters={filters}
          onChange={handleFiltersChange}
          resultCount={totalCount}
        />

        {/* Zone résultats */}
        <div className="flex-1 min-w-0">
          {/* Compteur résultats */}
          <div className="mb-4">
            <p className="text-sm text-[#857370]">
              {isLoading ? (
                "Chargement..."
              ) : isError ? (
                "Erreur de chargement"
              ) : (
                <>
                  <span className="font-semibold text-[#201a19]">{totalCount}</span>{" "}
                  recette{totalCount !== 1 ? "s" : ""}
                </>
              )}
            </p>
          </div>

          {/* Grille de recettes */}
          {isLoading ? (
            <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="aspect-[4/5] animate-pulse rounded-2xl bg-[#857370]/10"
                  aria-hidden
                />
              ))}
            </div>
          ) : isError ? (
            <div className="rounded-2xl border border-red-100 bg-red-50 p-8 text-center">
              <p className="text-sm text-red-700">
                Impossible de charger les recettes. Vérifiez votre connexion.
              </p>
            </div>
          ) : recipes.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#857370]/30 bg-white py-16 text-center">
              <SlidersHorizontal
                className="mx-auto mb-4 h-10 w-10 text-[#857370]/40"
                aria-hidden
              />
              <p className="text-sm font-medium text-[#201a19]">
                Aucune recette ne correspond à vos filtres
              </p>
              <p className="mt-1 text-xs text-[#857370]">
                Essayez d&apos;élargir vos critères de recherche
              </p>
            </div>
          ) : (
            <>
              <ul className="grid grid-cols-2 gap-4 xl:grid-cols-3">
                {recipes.map((recipe, index) => (
                  <li key={recipe.id}>
                    <RecipeCard recipe={recipe} priority={index < 4} />
                  </li>
                ))}
              </ul>

              {/* Pagination numérotée */}
              <Pagination
                page={page}
                totalPages={totalPages}
                onChange={handlePageChange}
              />
            </>
          )}
        </div>
      </div>

      {/* Modal import URL */}
      <ImportUrlModal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
      />
    </div>
  );
}
