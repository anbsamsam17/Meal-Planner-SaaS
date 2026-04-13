// apps/web/src/components/recipe/recipe-card.tsx
// Carte recette premium — design food-editorial
// Image 16:9, badge difficulté overlay, titre Noto Serif, rating étoiles dorées
// Référence : 04-components-catalog.md #03 Card Recipe
"use client";

import Image from "next/image";
import Link from "next/link";
import { Star } from "lucide-react";
import { MotionDiv } from "@/components/motion";
import { cn } from "@/lib/utils";
import type { Recipe } from "@/lib/api/types";

type RecipeCardVariant = "sm" | "md" | "lg";

interface RecipeCardProps {
  recipe: Recipe;
  mealLabel?: string; // Ex: "Lundi", "Mardi"
  variant?: RecipeCardVariant;
  priority?: boolean; // next/image priority pour les 2 premières
  onSwap?: () => void;
  className?: string;
}

// Mapping difficulté → label FR + classes badge warm
const DIFFICULTY_CONFIG = {
  1: { label: "Très facile", color: "bg-emerald-50 text-emerald-700" },
  2: { label: "Facile", color: "bg-emerald-50 text-emerald-700" },
  3: { label: "Moyen", color: "bg-amber-50 text-amber-700" },
  4: { label: "Difficile", color: "bg-orange-50 text-orange-700" },
  5: { label: "Expert", color: "bg-red-50 text-red-700" },
  easy: { label: "Facile", color: "bg-emerald-50 text-emerald-700" },
  medium: { label: "Moyen", color: "bg-amber-50 text-amber-700" },
  hard: { label: "Difficile", color: "bg-orange-50 text-orange-700" },
} as const;

type DifficultyKey = keyof typeof DIFFICULTY_CONFIG;

function getDifficultyConfig(difficulty: string | number) {
  const key = difficulty as DifficultyKey;
  return (
    DIFFICULTY_CONFIG[key] ?? { label: String(difficulty), color: "bg-neutral-50 text-neutral-700" }
  );
}

export function RecipeCard({
  recipe,
  mealLabel,
  variant = "md",
  priority = false,
  onSwap,
  className,
}: RecipeCardProps) {
  const totalMinutes = recipe.total_time_minutes;
  const difficultyConfig = getDifficultyConfig(recipe.difficulty);

  // Hauteur image selon variant — on force aspect-ratio 16/10 via CSS mais on adapte la hauteur min
  const imageContainerClass: Record<RecipeCardVariant, string> = {
    sm: "aspect-[16/10]",
    md: "aspect-[16/10]",
    lg: "aspect-[16/9]",
  };

  return (
    <MotionDiv
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ type: "spring", stiffness: 350, damping: 28, mass: 0.8 }}
      className={cn(
        "group cursor-pointer overflow-hidden rounded-2xl bg-white",
        "shadow-sm transition-shadow duration-300 hover:shadow-md",
        "dark:bg-neutral-800",
        className,
      )}
    >
      {/* Zone image 16:10 — coins arrondis xl via overflow-hidden sur le parent */}
      <Link
        href={`/recipes/${recipe.id}`}
        aria-label={`Voir la recette : ${recipe.title}`}
        className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset"
      >
        <div className={cn("relative w-full overflow-hidden", imageContainerClass[variant])}>
          {recipe.image_url ? (
            <Image
              src={recipe.image_url}
              alt={recipe.title}
              fill
              sizes={
                variant === "lg"
                  ? "(max-width: 768px) 100vw, 50vw"
                  : "(max-width: 768px) 50vw, 33vw"
              }
              className="object-cover transition-transform duration-500 group-hover:scale-105"
              priority={priority}
            />
          ) : (
            // Placeholder gradient warm si pas d'image
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100">
              <span className="text-5xl opacity-40" aria-hidden="true">
                🍽️
              </span>
            </div>
          )}

          {/* Overlay gradient warm subtil */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#201a19]/50 to-transparent" />

          {/* Badge jour (coin haut-gauche) */}
          {mealLabel && (
            <div className="absolute left-3 top-3">
              <span className="rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-[#201a19] backdrop-blur-sm">
                {mealLabel}
              </span>
            </div>
          )}

          {/* Badge difficulté (coin haut-gauche, sous mealLabel si absent) */}
          {!mealLabel && (
            <div className="absolute left-3 top-3">
              <span
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium backdrop-blur-sm",
                  difficultyConfig.color,
                )}
              >
                {difficultyConfig.label}
              </span>
            </div>
          )}

          {/* Badge temps (coin bas-droit) */}
          {totalMinutes && (
            <div className="absolute bottom-3 right-3">
              <span className="rounded-full bg-[#201a19]/70 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                {totalMinutes} MIN
              </span>
            </div>
          )}
        </div>
      </Link>

      {/* Contenu texte */}
      <div className="p-4">
        {/* Catégorie cuisine */}
        {recipe.cuisine && (
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-[#857370]">
            {recipe.cuisine}
          </span>
        )}

        {/* Titre — Noto Serif, 2 lignes max */}
        <Link
          href={`/recipes/${recipe.id}`}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1"
        >
          <h3
            className={cn(
              "font-serif font-bold leading-snug text-[#201a19] line-clamp-2 dark:text-neutral-100",
              variant === "lg" ? "text-xl" : "text-base",
            )}
          >
            {recipe.title}
          </h3>
        </Link>

        {/* Rating — étoiles dorées + note */}
        {recipe.rating_average != null && (
          <div className="mt-2 flex items-center gap-1.5 text-sm">
            <Star
              className="h-3.5 w-3.5 fill-amber-400 text-amber-400"
              aria-hidden="true"
            />
            <span className="font-semibold text-[#201a19]">
              {Number(recipe.rating_average).toFixed(1)}
            </span>
            <span className="text-[#857370]">/5</span>
          </div>
        )}

        {/* Tags régimes alimentaires */}
        {recipe.dietary_tags.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1">
            {recipe.dietary_tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-[#857370]/20 bg-[#fff8f6] px-2 py-0.5 text-xs font-medium text-[#857370]"
              >
                {formatDietTag(tag)}
              </span>
            ))}
          </div>
        )}

        {/* Bouton swap */}
        {onSwap && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              onSwap();
            }}
            className="mt-3 w-full rounded-xl border border-[#857370]/30 py-2 text-xs font-medium
              text-[#857370] transition-all duration-300 hover:border-primary-300 hover:bg-primary-50
              hover:text-primary-600 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500"
          >
            Remplacer cette recette
          </button>
        )}
      </div>
    </MotionDiv>
  );
}

function formatDietTag(tag: string): string {
  const labels: Record<string, string> = {
    vegetarian: "Végétarien",
    vegan: "Végétalien",
    "gluten-free": "Sans gluten",
    gluten_free: "Sans gluten",
    "lactose-free": "Sans lactose",
    lactose_free: "Sans lactose",
    "no-pork": "Sans porc",
    no_pork: "Sans porc",
    "no-seafood": "Sans mer",
    no_seafood: "Sans mer",
    "nut-free": "Sans noix",
    nut_free: "Sans noix",
    halal: "Halal",
  };
  return labels[tag] ?? tag;
}
