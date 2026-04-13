"use client";
// apps/web/src/app/(app)/recipes/recipes-explorer.tsx
// Explorer de recettes avec filtres avancés — Client Component
// Phase 2 — barre de recherche, filtres latéraux, grid, pagination infinie

import { useState, useCallback, useEffect } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Search, SlidersHorizontal } from "lucide-react";
import { useDebounce } from "@/hooks/use-debounce";
import { searchRecipesAdvanced } from "@/lib/api/endpoints";
import type { RecipeFilters, PaginatedResponse } from "@/lib/api/types";
import type { Recipe } from "@/lib/api/types";
import { RecipeCard } from "@/components/recipe/recipe-card";
import { RecipeFiltersPanel } from "@/components/recipe/recipe-filters";

const DEFAULT_FILTERS: RecipeFilters = { max_time: 60, per_page: 12 };

export function RecipesExplorer() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<RecipeFilters>(DEFAULT_FILTERS);

  const debouncedQuery = useDebounce(searchQuery, 350);

  // Merge de la recherche textuelle dans les filtres
  const activeFilters: RecipeFilters = {
    ...filters,
    q: debouncedQuery || undefined,
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

  // Utilise `data` — champ défini dans PaginatedResponse<T> (cf. types.ts)
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

  return (
    <div className="mx-auto max-w-6xl bg-[#fff8f6] px-4 py-8">
      {/* En-tête — Noto Serif */}
      <h1 className="mb-6 font-serif text-2xl font-bold text-[#201a19]">Explorer les recettes</h1>

      {/* Barre de recherche premium — rounded-xl, border warm outline/30, focus terracotta */}
      <div className="mb-6 relative">
        <label htmlFor="recipe-search" className="sr-only">
          Rechercher une recette
        </label>
        <Search
          className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#857370]"
          aria-hidden
        />
        <input
          id="recipe-search"
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Rechercher une recette, un ingrédient..."
          className="w-full rounded-xl border border-[#857370]/30 bg-white py-3 pl-11 pr-4 text-sm text-[#201a19] placeholder:text-[#857370] shadow-sm focus:border-[#E2725B] focus:outline-none focus:ring-2 focus:ring-[#E2725B]/20 transition-all duration-300"
        />
      </div>

      {/* Layout filtres + résultats */}
      <div className="flex gap-6">
        {/* Filtres — sidebar desktop / sheet mobile */}
        <RecipeFiltersPanel
          filters={filters}
          onChange={handleFiltersChange}
          resultCount={totalCount}
        />

        {/* Résultats */}
        <div className="flex-1 min-w-0">
          {/* Compteur */}
          <div className="mb-4 flex items-center justify-between gap-4">
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
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="aspect-[16/10] animate-pulse rounded-2xl bg-[#857370]/10"
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
              <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" role="list">
                {allRecipes.map((recipe) => (
                  <li key={recipe.id}>
                    <RecipeCard recipe={recipe} variant="md" />
                  </li>
                ))}
              </ul>

              {/* Trigger infinite scroll */}
              <div ref={loadMoreRef} className="mt-6 flex justify-center">
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
