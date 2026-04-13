"use client";
// apps/web/src/app/(app)/recipes/recipes-explorer.tsx
// Explorer de recettes avec filtres avancés — Client Component
// Phase 2 — barre de recherche arrondie premium, pills filtres, grid portrait 2→3 col

import { useState, useCallback } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Search, SlidersHorizontal } from "lucide-react";
import { useDebounce } from "@/hooks/use-debounce";
import { searchRecipesAdvanced } from "@/lib/api/endpoints";
import type { RecipeFilters, PaginatedResponse } from "@/lib/api/types";
import type { Recipe } from "@/lib/api/types";
import { RecipeCard } from "@/components/recipe/recipe-card";
import { RecipeFiltersPanel } from "@/components/recipe/recipe-filters";

const DEFAULT_FILTERS: RecipeFilters = { max_time: 60, per_page: 12 };

// Pills de filtres rapides — statiques (enrichissables via feature flag)
const QUICK_FILTERS = [
  { label: "Rapide (< 15 min)", key: "quick" },
  { label: "Végétarien", key: "vegetarian" },
  { label: "Française", key: "french" },
  { label: "Asiatique", key: "asian" },
  { label: "Italien", key: "italian" },
] as const;

type QuickFilterKey = (typeof QUICK_FILTERS)[number]["key"];

export function RecipesExplorer() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<RecipeFilters>(DEFAULT_FILTERS);
  const [activeQuickFilter, setActiveQuickFilter] = useState<QuickFilterKey | null>(null);

  const debouncedQuery = useDebounce(searchQuery, 350);

  // Merge de la recherche textuelle + quick filter dans les filtres
  const activeFilters: RecipeFilters = {
    ...filters,
    q: debouncedQuery || undefined,
    ...(activeQuickFilter === "quick" && { max_time: 15 }),
    ...(activeQuickFilter === "vegetarian" && { diet: "vegetarian" }),
    ...(activeQuickFilter === "french" && { cuisine: "Français" }),
    ...(activeQuickFilter === "asian" && { cuisine: "Asiatique" }),
    ...(activeQuickFilter === "italian" && { cuisine: "Italien" }),
    per_page: 12,
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
  } = useInfiniteQuery<PaginatedResponse<Recipe>, Error>({
    queryKey: ["recipes", "explore", activeFilters],
    queryFn: ({ pageParam = 1 }) =>
      searchRecipesAdvanced({ ...activeFilters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.has_next) return allPages.length + 1;
      return undefined;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  const allRecipes = data?.pages.flatMap((p) => p.data ?? []) ?? [];
  const totalCount = data?.pages[0]?.total ?? 0;

  // Intersection Observer pour infinite scroll
  const loadMoreRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node || !hasNextPage || isFetchingNextPage) return;
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry?.isIntersecting) void fetchNextPage();
        },
        { threshold: 0.1 },
      );
      observer.observe(node);
      return () => observer.disconnect();
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  );

  function handleFiltersChange(newFilters: RecipeFilters) {
    setFilters({ ...newFilters, per_page: 12 });
  }

  function handleQuickFilter(key: QuickFilterKey) {
    setActiveQuickFilter((prev) => (prev === key ? null : key));
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
      {/* =========================================
          HEADER PREMIUM — sous-titre terracotta + titre Noto Serif
      ========================================= */}
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#E2725B]">
        Découvrez de nouvelles saveurs
      </p>
      <h1 className="mt-2 font-serif text-3xl font-bold leading-tight text-[#201a19] md:text-4xl">
        Explorez +50&nbsp;000
        <br />
        recettes de chef
      </h1>

      {/* =========================================
          BARRE DE RECHERCHE — arrondie full, fond cream chaud
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
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Rechercher ingrédients, cuisines..."
          className="w-full rounded-full border-0 bg-[#E2725B]/5 py-3.5 pl-12 pr-4 text-sm text-[#201a19] placeholder:text-[#857370]/60 focus:outline-none focus:ring-2 focus:ring-[#E2725B]/30 transition-all duration-200"
        />
      </div>

      {/* =========================================
          PILLS FILTRES RAPIDES — scrollable horizontal
      ========================================= */}
      <div className="mt-4 flex gap-2 overflow-x-auto hide-scrollbar pb-2">
        {/* Bouton "Tous les filtres" ouvre le panneau latéral via RecipeFiltersPanel */}
        <button
          type="button"
          onClick={() => setActiveQuickFilter(null)}
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
          LAYOUT : filtres avancés (sidebar) + grille résultats
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

          {/* Grille de recettes — 2 colonnes mobile, 3 desktop */}
          {isLoading ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
          ) : allRecipes.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#857370]/30 bg-white py-16 text-center">
              <SlidersHorizontal className="mx-auto mb-4 h-10 w-10 text-[#857370]/40" aria-hidden />
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
                {allRecipes.map((recipe, index) => (
                  <li key={recipe.id}>
                    <RecipeCard recipe={recipe} priority={index < 4} />
                  </li>
                ))}
              </ul>

              {/* Trigger infinite scroll */}
              <div ref={loadMoreRef} className="mt-8 flex justify-center">
                {isFetchingNextPage && (
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#857370]/30 border-t-[#E2725B]" />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
