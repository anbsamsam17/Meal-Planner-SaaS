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
    description: recipe.description ?? undefined,
    openGraph: {
      title: recipe.title,
      description: recipe.description ?? undefined,
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

    const data = await response.json();

    // Normalisation défensive : certains endpoints retournent photo_url au lieu de image_url
    // On unifie ici pour que le reste du composant ne voie que image_url
    if (data && data.photo_url !== undefined && data.image_url === undefined) {
      data.image_url = data.photo_url ?? null;
    }

    // Garantir que les tableaux sont bien des tableaux (jamais null/undefined)
    if (data) {
      data.ingredients = Array.isArray(data.ingredients) ? data.ingredients : [];
      data.instructions = Array.isArray(data.instructions) ? data.instructions : [];
      data.dietary_tags = Array.isArray(data.dietary_tags) ? data.dietary_tags : [];
    }

    return data;
  } catch {
    return null;
  }
}

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "Facile",
  medium: "Moyen",
  hard: "Difficile",
  // Alias numériques — certains endpoints retournent la difficulté en 1-5
  "1": "Très facile",
  "2": "Facile",
  "3": "Moyen",
  "4": "Difficile",
  "5": "Très difficile",
};

export default async function RecipePage({ params }: RecipePageProps) {
  let recipe: Awaited<ReturnType<typeof fetchRecipe>>;

  try {
    recipe = await fetchRecipe(params.id);
  } catch {
    // Erreur réseau ou parsing inattendue — afficher un état gracieux
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-4 p-8 text-center">
        <p className="text-lg font-semibold text-neutral-700 dark:text-neutral-300">
          Recette introuvable ou erreur de chargement.
        </p>
        <Link
          href="/dashboard"
          className="text-sm text-primary-600 underline hover:text-primary-700"
        >
          Retour au planning
        </Link>
      </div>
    );
  }

  if (!recipe) {
    notFound();
  }

  // Placeholder Unsplash déterministe si pas de photo
  const PLACEHOLDER_IMAGES = [
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1473093226795-af9932fe5856?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200&auto=format&fit=crop",
  ];
  const placeholderUrl =
    PLACEHOLDER_IMAGES[recipe.id.charCodeAt(0) % PLACEHOLDER_IMAGES.length] ??
    PLACEHOLDER_IMAGES[0];
  const heroImageUrl = recipe.image_url ?? placeholderUrl;

  // Protéger rating_average — peut être null ou undefined selon l'endpoint
  const ratingAverage = recipe.rating_average != null ? Number(recipe.rating_average) : null;
  const difficultyLabel = recipe.difficulty
    ? (DIFFICULTY_LABELS[recipe.difficulty] ?? "")
    : "";

  return (
    <div className="min-h-full">
      {/* Hero avec image */}
      <div className="relative h-64 w-full md:h-80 lg:h-96">
        <Image
          src={heroImageUrl}
          alt={recipe.title}
          fill
          sizes="100vw"
          className="object-cover"
          priority // Image hero — toujours prioritaire
        />

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

            {/* Temps — n'afficher que si la valeur est disponible */}
            {recipe.total_time_minutes != null && recipe.total_time_minutes > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" aria-hidden="true" />
                {recipe.total_time_minutes} min
              </span>
            )}

            {/* Portions */}
            {recipe.servings > 0 && (
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" aria-hidden="true" />
                {recipe.servings} pers.
              </span>
            )}

            {/* Difficulté */}
            {difficultyLabel && <span>{difficultyLabel}</span>}

            {/* Rating — protégé : .toFixed(1) sur un number garanti non-null */}
            {ratingAverage != null && (
              <span className="flex items-center gap-1">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" aria-hidden="true" />
                {ratingAverage.toFixed(1)} ({recipe.rating_count ?? 0} avis)
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
