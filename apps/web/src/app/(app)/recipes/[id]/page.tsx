// apps/web/src/app/(app)/recipes/[id]/page.tsx
// Fiche recette — Server Component
// Fetch GET /api/v1/recipes/{id} côté serveur
// Tabs Radix : Ingrédients / Instructions / Nutrition
// Bouton noter la recette → RatingModal (Client Component)
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Clock, ChevronLeft, Star, Users } from "lucide-react";
import { createServerClient } from "@/lib/supabase/server";
import { RecipeTabsClient } from "./recipe-tabs-client";

interface RecipePageProps {
  params: { id: string };
}

// Métadonnées dynamiques depuis la recette
export async function generateMetadata({ params }: RecipePageProps): Promise<Metadata> {
  const recipe = await fetchRecipe(params.id);
  if (!recipe) return { title: "Recette introuvable" };

  return {
    title: recipe.title,
    description: recipe.description,
    openGraph: {
      title: recipe.title,
      description: recipe.description,
      images: recipe.image_url ? [{ url: recipe.image_url }] : [],
    },
  };
}

async function fetchRecipe(id: string) {
  const supabase = createServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!token || !apiBaseUrl) return null;

  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/recipes/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      next: { revalidate: 3600 }, // Cache 1h — les recettes changent rarement
    });

    if (response.status === 404) return null;
    if (!response.ok) return null;

    return response.json();
  } catch {
    return null;
  }
}

const DIFFICULTY_LABELS = {
  easy: "Facile",
  medium: "Moyen",
  hard: "Difficile",
} as const;

export default async function RecipePage({ params }: RecipePageProps) {
  const recipe = await fetchRecipe(params.id);

  if (!recipe) {
    notFound();
  }

  return (
    <div className="min-h-full">
      {/* Hero avec image */}
      <div className="relative h-64 w-full md:h-80 lg:h-96">
        {recipe.image_url ? (
          <Image
            src={recipe.image_url}
            alt={recipe.title}
            fill
            sizes="100vw"
            className="object-cover"
            priority // Image hero — toujours prioritaire
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-neutral-100 dark:bg-neutral-800">
            <span className="text-6xl" aria-hidden="true">🍽️</span>
          </div>
        )}

        {/* Overlay gradient bas */}
        <div className="absolute inset-0 bg-gradient-to-t from-neutral-900/80 via-neutral-900/20 to-transparent" />

        {/* Bouton retour */}
        <Link
          href="/dashboard"
          className="absolute left-4 top-4 flex h-10 w-10 items-center justify-center
            rounded-full bg-white/80 text-neutral-700 backdrop-blur-sm
            transition-colors hover:bg-white focus-visible:outline-none
            focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-neutral-800/80 dark:text-neutral-200"
          aria-label="Retour au planning"
        >
          <ChevronLeft className="h-5 w-5" aria-hidden="true" />
        </Link>

        {/* Titre et métadonnées en overlay bas */}
        <div className="absolute bottom-0 left-0 right-0 p-5">
          <h1 className="font-serif mb-2 text-2xl font-bold text-white md:text-3xl">
            {recipe.title}
          </h1>

          <div className="flex flex-wrap items-center gap-3 text-sm text-white/80">
            {/* Cuisine */}
            {recipe.cuisine && (
              <span className="font-medium text-white/60">{recipe.cuisine}</span>
            )}

            {/* Temps */}
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" aria-hidden="true" />
              {recipe.total_time_minutes} min
            </span>

            {/* Portions */}
            <span className="flex items-center gap-1">
              <Users className="h-4 w-4" aria-hidden="true" />
              {recipe.servings} pers.
            </span>

            {/* Difficulté */}
            <span>{DIFFICULTY_LABELS[recipe.difficulty as keyof typeof DIFFICULTY_LABELS]}</span>

            {/* Rating */}
            {recipe.rating_average !== null && (
              <span className="flex items-center gap-1">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" aria-hidden="true" />
                {recipe.rating_average.toFixed(1)} ({recipe.rating_count} avis)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Contenu de la fiche — Tabs client pour les interactions */}
      <div className="mx-auto max-w-2xl px-4 py-6 md:px-6">
        <RecipeTabsClient recipe={recipe} />
      </div>
    </div>
  );
}
