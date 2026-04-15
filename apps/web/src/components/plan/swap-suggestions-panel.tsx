// apps/web/src/components/plan/swap-suggestions-panel.tsx
// Panel lateral (sheet) pour choisir une recette de remplacement
// Utilise pour le swap individuel d'un diner ET pour ajouter samedi/dimanche
// Affiche : 4 pills filtres + 6 suggestions (cards miniatures)
// Clic sur suggestion → callback parent avec recipe_id
"use client";

import { useState, useEffect, useRef } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Loader2 } from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { useRecipeSuggestions } from "@/hooks/use-plan";
import type { Recipe } from "@/lib/api/types";

// --- Placeholder images (meme liste que recipe-card) ---
const PLACEHOLDER_IMAGES = [
  "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=400&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1473093226795-af9932fe5856?q=80&w=400&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?q=80&w=400&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=400&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?q=80&w=400&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=400&auto=format&fit=crop",
] as const;

function getPlaceholderImage(id: string): string {
  const index = id.charCodeAt(0) % PLACEHOLDER_IMAGES.length;
  return PLACEHOLDER_IMAGES[index] ?? PLACEHOLDER_IMAGES[0];
}

// --- Filter pills ---

interface FilterOption {
  label: string;
  style?: string;
  maxTime?: number;
}

const FILTER_OPTIONS: FilterOption[] = [
  { label: "Rapide", maxTime: 20 },
  { label: "Protéiné", style: "protéiné" },
  { label: "Végétarien", style: "végétarien" },
  { label: "Léger", style: "léger" },
];

// --- Mini recipe card ---

interface MiniRecipeCardProps {
  recipe: Recipe;
  onSelect: () => void;
}

function MiniRecipeCard({ recipe, onSelect }: MiniRecipeCardProps) {
  const imageUrl =
    recipe.photo_url || recipe.image_url || getPlaceholderImage(recipe.id);
  const time = recipe.total_time_minutes ?? recipe.total_time_min ?? null;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group flex gap-3 rounded-xl border border-[#857370]/15 bg-white p-2.5",
        "text-left transition-all duration-200",
        "hover:border-[#E2725B]/40 hover:shadow-sm",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]",
      )}
    >
      {/* Miniature image */}
      <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-[#857370]/10">
        <Image
          src={imageUrl}
          alt={recipe.title}
          fill
          sizes="64px"
          className="object-cover"
        />
      </div>

      {/* Texte */}
      <div className="flex min-w-0 flex-1 flex-col justify-center">
        <h4 className="text-sm font-semibold leading-tight text-[#201a19] line-clamp-2 group-hover:text-[#E2725B] transition-colors">
          {recipe.title}
        </h4>
        {time != null && time > 0 && (
          <span className="mt-0.5 text-xs text-[#857370]">{time} min</span>
        )}
      </div>
    </button>
  );
}

// --- Panel principal ---

interface SwapSuggestionsPanelProps {
  open: boolean;
  onClose: () => void;
  planId: string;
  /** Titre affiche en haut du panel */
  title: string;
  /** Callback quand une recette est selectionnee */
  onSelectRecipe: (recipeId: string) => void;
  /** True pendant la mutation swap/add */
  isSubmitting?: boolean;
}

export function SwapSuggestionsPanel({
  open,
  onClose,
  planId,
  title,
  onSelectRecipe,
  isSubmitting = false,
}: SwapSuggestionsPanelProps) {
  const [activeFilter, setActiveFilter] = useState<FilterOption | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  const { data: suggestions = [], isLoading } = useRecipeSuggestions(
    planId,
    {
      style: activeFilter?.style,
      max_time: activeFilter?.maxTime,
      q: debouncedQuery || undefined,
    },
    open, // enabled seulement quand le panel est ouvert
  );

  return (
    <Dialog.Root open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <Dialog.Portal>
        {/* Overlay */}
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />

        {/* Sheet sliding from right */}
        <Dialog.Content
          className={cn(
            "fixed right-0 top-0 z-50 h-full w-full max-w-md",
            "overflow-y-auto bg-[#fff8f6] shadow-xl",
            "focus:outline-none",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right",
            "data-[state=closed]:duration-300 data-[state=open]:duration-300",
          )}
          aria-describedby="swap-panel-description"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 border-b border-[#857370]/10 bg-[#fff8f6] px-5 py-4">
            <div className="flex items-start justify-between">
              <div>
                <Dialog.Title className="font-serif text-lg font-bold text-[#201a19]">
                  {title}
                </Dialog.Title>
                <p
                  id="swap-panel-description"
                  className="mt-0.5 text-xs text-[#857370]"
                >
                  Choisissez une recette parmi nos suggestions
                </p>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-[#857370] transition-colors hover:bg-[#857370]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]"
                  aria-label="Fermer"
                >
                  <X className="h-4 w-4" />
                </button>
              </Dialog.Close>
            </div>

            {/* Champ de recherche */}
            <div className="mt-3">
              <input
                type="text"
                placeholder="Rechercher une recette ou une cuisine..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-[#E2725B] focus:outline-none focus:ring-1 focus:ring-[#E2725B]"
              />
            </div>

            {/* Filter pills */}
            <div className="mt-2 flex flex-wrap gap-2">
              {FILTER_OPTIONS.map((filter) => {
                const isActive =
                  activeFilter?.label === filter.label;
                return (
                  <button
                    key={filter.label}
                    type="button"
                    onClick={() =>
                      setActiveFilter(isActive ? null : filter)
                    }
                    className={cn(
                      "rounded-full px-3.5 py-1.5 text-xs font-medium transition-all duration-200",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]",
                      isActive
                        ? "bg-[#E2725B] text-white"
                        : "bg-white text-[#857370] border border-[#857370]/20 hover:border-[#E2725B]/30",
                    )}
                    aria-pressed={isActive}
                  >
                    {filter.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Suggestions list */}
          <div className="p-5">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2
                  className="h-6 w-6 animate-spin text-[#E2725B]"
                  aria-hidden="true"
                />
              </div>
            ) : suggestions.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-sm text-[#857370]">
                  Aucune suggestion disponible pour ces filtres.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {suggestions.slice(0, 6).map((recipe) => (
                  <MiniRecipeCard
                    key={recipe.id}
                    recipe={recipe}
                    onSelect={() => {
                      if (!isSubmitting) {
                        onSelectRecipe(recipe.id);
                      }
                    }}
                  />
                ))}
              </div>
            )}

            {/* Indicator de mutation en cours */}
            {isSubmitting && (
              <div className="mt-4 flex items-center justify-center gap-2 text-sm text-[#857370]">
                <Loader2
                  className="h-4 w-4 animate-spin"
                  aria-hidden="true"
                />
                Remplacement en cours...
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
