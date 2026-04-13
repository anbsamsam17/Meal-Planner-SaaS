// apps/web/src/components/recipe/recipe-card.tsx
// Carte recette premium — design food editorial portrait 4:5
// Photo portrait grande, badge temps terracotta overlay haut-droite,
// rating étoile dorée overlay bas-gauche, titre Noto Serif, catégorie small caps
// Refonte 2026-04-12 : badge coût estimé + temps préparation sous le titre
"use client";

import Image from "next/image";
import Link from "next/link";
import { Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Recipe } from "@/lib/api/types";

// --- Images Unsplash placeholder pour les recettes sans photo ---
const PLACEHOLDER_IMAGES = [
  "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1473093226795-af9932fe5856?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800&auto=format&fit=crop",
] as const;

// Déterministe : même recette → même image placeholder (évite le flash au SSR)
function getPlaceholderImage(id: string): string {
  const index = id.charCodeAt(0) % PLACEHOLDER_IMAGES.length;
  return PLACEHOLDER_IMAGES[index] ?? PLACEHOLDER_IMAGES[0];
}

// Calcule le badge coût estimé basé sur dietary_tags/tags et difficulty
// Supporte les deux formats : normalisé (dietary_tags) et API brut (tags)
function getCostBadge(recipe: Recipe): string {
  const tags: string[] = recipe.dietary_tags ?? recipe.tags ?? [];
  if (tags.includes("vegetarian") || tags.includes("végétarien") || tags.includes("vegetarien") || tags.includes("économique")) {
    return "\u20AC";
  }
  // Gérer difficulty en string OU en number (API retourne int 1-5)
  const diff = recipe.difficulty;
  if (diff === "hard" || (typeof diff === "number" && diff >= 4)) {
    return "\u20AC\u20AC\u20AC";
  }
  return "\u20AC\u20AC";
}

// Temps d'affichage priorité : total_time_minutes > total_time_min > prep + cook > null
// Supporte les deux formats : normalisé et API brut
function getDisplayTime(recipe: Recipe): number | null {
  const totalTime = recipe.total_time_minutes ?? recipe.total_time_min ?? null;
  if (totalTime != null && totalTime > 0) {
    return totalTime;
  }
  const prep = recipe.prep_time_minutes ?? recipe.prep_time_min ?? 0;
  const cook = recipe.cook_time_minutes ?? recipe.cook_time_min ?? 0;
  const combined = prep + cook;
  return combined > 0 ? combined : null;
}

interface RecipeCardProps {
  recipe: Recipe;
  mealLabel?: string; // Ex: "Lundi", "Mardi" — affiché en overlay haut-gauche
  priority?: boolean; // next/image priority pour les 2-3 premières cards
  onSwap?: () => void;
  className?: string;
  // variant conservé pour compatibilité descendante (PlanWeekGrid)
  variant?: "sm" | "md" | "lg";
}

export function RecipeCard({
  recipe,
  mealLabel,
  priority = false,
  onSwap,
  className,
}: RecipeCardProps) {
  const imageUrl = recipe.photo_url || recipe.image_url || getPlaceholderImage(recipe.id);
  const displayTime = getDisplayTime(recipe);
  const costBadge = getCostBadge(recipe);
  // rating_average est 1.0–5.0, on l'affiche directement avec .toFixed(1)
  const rating = recipe.rating_average != null ? Number(recipe.rating_average).toFixed(1) : null;

  return (
    <Link href={`/recipes/${recipe.id}`} className={cn("group block", className)}>
      {/* Image container — ratio portrait 4:5 */}
      <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-[#857370]/10">
        <Image
          src={imageUrl}
          alt={recipe.title}
          fill
          sizes="(max-width: 768px) 50vw, 33vw"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
          priority={priority}
        />

        {/* Badge jour meal-plan — overlay haut-gauche (quand utilisé dans le planning) */}
        {mealLabel && (
          <span className="absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-[#201a19] backdrop-blur-sm shadow-sm">
            {mealLabel}
          </span>
        )}

        {/* Badge temps — overlay haut-droite, fond terracotta */}
        {displayTime != null && displayTime > 0 && (
          <span className="absolute right-3 top-3 rounded-full bg-[#E2725B]/90 px-3 py-1.5 text-xs font-semibold text-white shadow-sm">
            {displayTime} MIN
          </span>
        )}

        {/* Rating — overlay bas-gauche, fond semi-transparent avec blur */}
        {rating != null && (
          <div className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-black/40 px-2.5 py-1 backdrop-blur-sm">
            <span className="text-amber-400 text-xs leading-none" aria-hidden="true">
              ★
            </span>
            <span className="text-xs font-semibold text-white">{rating}</span>
            {(recipe.rating_count ?? 0) > 0 && (
              <span className="text-xs text-white/70">
                (
                {(recipe.rating_count ?? 0) >= 1000
                  ? `${((recipe.rating_count ?? 0) / 1000).toFixed(1)}k`
                  : recipe.rating_count}
                )
              </span>
            )}
          </div>
        )}
      </div>

      {/* Catégorie — small caps uppercase terracotta outline */}
      {/* Supporte les deux formats : normalisé (cuisine) et API brut (cuisine_type) */}
      {(recipe.cuisine || recipe.cuisine_type) && (
        <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-[#857370]">
          {recipe.cuisine || recipe.cuisine_type}
        </p>
      )}

      {/* Titre — Noto Serif bold, 2 lignes max, hover terracotta */}
      <h3 className="mt-1 font-serif text-base font-bold leading-snug text-[#201a19] line-clamp-2 group-hover:text-[#E2725B] transition-colors duration-200">
        {recipe.title}
      </h3>

      {/* Temps de préparation + coût estimé — sous le titre */}
      <div className="mt-2 flex items-center gap-3 text-xs text-[#857370]">
        {displayTime != null && (
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            {displayTime} min
          </span>
        )}
        <span className="font-medium text-[#E2725B]">{costBadge}</span>
      </div>

      {/* Bouton swap — visible uniquement dans le planning */}
      {onSwap && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            onSwap();
          }}
          className="mt-3 w-full rounded-xl border border-[#857370]/30 py-2 text-xs font-medium
            text-[#857370] transition-all duration-300 hover:border-[#E2725B]/40 hover:bg-[#E2725B]/5
            hover:text-[#E2725B] focus-visible:outline-none focus-visible:ring-2
            focus-visible:ring-[#E2725B]/40"
        >
          Remplacer cette recette
        </button>
      )}
    </Link>
  );
}
