// apps/web/src/app/(app)/recipes/[id]/page.tsx
// Fiche recette — Server Component
// Fetch GET /api/v1/recipes/{id} cote serveur
// Design card-based mobile-first : photo 16:9, max-w-2xl centre
// Tabs Radix : Ingredients / Instructions / Nutrition
// Bouton noter la recette -> RatingModal (Client Component)
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

// Metadonnees dynamiques depuis la recette
export async function generateMetadata({ params }: RecipePageProps): Promise<Metadata> {
  const recipe = await fetchRecipe(params.id);
  if (!recipe) return { title: "Recette introuvable" };

  return {
    title: recipe.title,
    description: recipe.description ?? undefined,
    openGraph: {
      title: recipe.title,
      description: recipe.description ?? undefined,
      images: (recipe.photo_url || recipe.image_url) ? [{ url: (recipe.photo_url || recipe.image_url) as string }] : [],
    },
  };
}

async function fetchRecipe(id: string) {
  const supabase = createServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://meal-planner-saas-production.up.railway.app";

  if (!token) return null;

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

    // Normalisation defensive : mapper les champs API bruts vers les noms frontend
    if (data && data.photo_url !== undefined && data.image_url === undefined) {
      data.image_url = data.photo_url ?? null;
    }

    if (data) {
      // Normaliser les champs de temps (API: *_min -> Frontend: *_minutes)
      data.total_time_minutes = data.total_time_min ?? data.total_time_minutes ?? null;
      data.prep_time_minutes = data.prep_time_min ?? data.prep_time_minutes ?? null;
      data.cook_time_minutes = data.cook_time_min ?? data.cook_time_minutes ?? null;

      // Normaliser cuisine (API: cuisine_type -> Frontend: cuisine)
      data.cuisine = data.cuisine_type ?? data.cuisine ?? null;

      // Normaliser dietary_tags (API: tags -> Frontend: dietary_tags)
      data.dietary_tags = Array.isArray(data.tags) ? data.tags : (Array.isArray(data.dietary_tags) ? data.dietary_tags : []);

      // Normaliser rating (API: quality_score 0-1 -> Frontend: rating_average 1-5)
      if (data.quality_score != null && data.rating_average == null) {
        data.rating_average = Math.min(5, data.quality_score * 5);
      }

      // Garantir que les tableaux sont bien des tableaux (jamais null/undefined)
      data.instructions = Array.isArray(data.instructions) ? data.instructions : [];

      // Nutrition : mapper protein_g (API) -> proteins_g (type frontend)
      if (data.nutrition && typeof data.nutrition === "object" && Object.keys(data.nutrition).length > 0) {
        data.nutrition = {
          calories: data.nutrition.calories ?? 0,
          proteins_g: data.nutrition.protein_g ?? 0,
          carbs_g: data.nutrition.carbs_g ?? 0,
          fat_g: data.nutrition.fat_g ?? 0,
          fiber_g: data.nutrition.fiber_g ?? null,
        };
      } else {
        data.nutrition = null;
      }

      // Normalisation des ingredients : l'API retourne le format brut du catalogue
      // { ingredient_id, canonical_name, quantity, unit, notes, position }
      // alors que le type Ingredient frontend attend
      // { id, name, quantity, unit, note, category }
      const rawIngredients = Array.isArray(data.ingredients) ? data.ingredients : [];
      data.ingredients = rawIngredients.map((ing: Record<string, unknown>) => ({
        id: (ing.ingredient_id as string | undefined) ?? String(ing.position ?? Math.random()),
        name: (ing.canonical_name as string | undefined) ?? "",
        quantity: typeof ing.quantity === "number" ? ing.quantity : 1,
        unit: typeof ing.unit === "string" ? ing.unit : "",
        // Afficher notes en priorite (plus descriptif), sinon canonical_name
        note: (ing.notes as string | undefined) ?? null,
        category: "other" as const,
        open_food_facts_id: null,
      }));
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
  // Alias numeriques — certains endpoints retournent la difficulte en 1-5
  "1": "Tres facile",
  "2": "Facile",
  "3": "Moyen",
  "4": "Difficile",
  "5": "Tres difficile",
};

export default async function RecipePage({ params }: RecipePageProps) {
  let recipe: Awaited<ReturnType<typeof fetchRecipe>>;

  try {
    recipe = await fetchRecipe(params.id);
  } catch {
    // Erreur reseau ou parsing inattendue — afficher un etat gracieux
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

  // Placeholder Unsplash deterministe si pas de photo
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
  const heroImageUrl = recipe.photo_url || recipe.image_url || placeholderUrl;

  // Proteger rating_average — peut etre null ou undefined selon l'endpoint
  const difficultyLabel = recipe.difficulty
    ? (DIFFICULTY_LABELS[recipe.difficulty] ?? "")
    : "";

  // Temps total affiche : fallback sur prep + cook si total absent
  const displayTime =
    (recipe.total_time_minutes != null && recipe.total_time_minutes > 0)
      ? recipe.total_time_minutes
      : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      {/* Bouton retour */}
      <Link
        href="/recipes"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[#857370] transition-colors hover:text-[#E2725B]"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Retour aux recettes
      </Link>

      {/* Photo — ratio 16:9, coins arrondis, taille proportionnelle */}
      <div className="relative aspect-video overflow-hidden rounded-2xl">
        <Image
          src={heroImageUrl}
          alt={recipe.title}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 672px"
          priority
        />
      </div>

      {/* Contenu */}
      <div className="mt-6">
        {/* Badge cuisine */}
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[#E2725B]">
          {recipe.cuisine?.toUpperCase() || "RECETTE"}
        </p>

        {/* Titre */}
        <h1 className="mt-1 font-serif text-2xl font-bold text-[#201a19] md:text-3xl dark:text-neutral-100">
          {recipe.title}
        </h1>

        {/* Metadonnees en ligne */}
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-[#857370] dark:text-neutral-400">
          {displayTime != null && (
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" aria-hidden="true" />
              {displayTime} min
            </span>
          )}

          <span className="flex items-center gap-1.5">
            <Users className="h-4 w-4" aria-hidden="true" />
            {recipe.servings ?? 4} pers.
          </span>

          <span className="flex items-center gap-1.5">
            <Star
              className="h-4 w-4 fill-amber-400 text-amber-400"
              aria-hidden="true"
            />
            {difficultyLabel || "Moyen"}
          </span>
        </div>

        {/* Description */}
        {recipe.description && (
          <p className="mt-4 text-sm leading-relaxed text-[#857370] dark:text-neutral-400">
            {recipe.description}
          </p>
        )}
      </div>

      {/* Tabs : Ingredients / Instructions / Nutrition */}
      <div className="mt-8">
        <RecipeTabsClient recipe={recipe} />
      </div>
    </div>
  );
}
