// apps/web/src/app/page.tsx
// Landing page — Server Component (pas de "use client")
// Design éditorial : "comme si Ottolenghi avait designé une app, avec la rigueur UX de Stripe"
// Référence : 01-brand-vision.md — persona Laure, 36 ans, Lyon
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Brain, ShoppingCart, BookOpen, Star, CalendarDays, Clock, Users } from "lucide-react";
import type { Recipe } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Presto — Le livre de recettes de votre famille",
  description:
    "Le livre de recettes de votre famille, réinventé par Presto. Drive intégré, livre PDF hebdomadaire, mode anti-gaspi. Essai gratuit 14 jours.",
};

// --- Section "Recettes du monde" : fetch RSC avec fallback ---

interface RecipesApiResponse {
  results?: Recipe[];
  items?: Recipe[];
}

// --- Données statiques des sections ---

const VALUE_PROPS = [
  {
    icon: Brain,
    title: "Mémoire Presto",
    description:
      "Presto apprend les goûts de chaque membre. Après 4 semaines, il connaît votre famille mieux que vous.",
    color: "text-primary-600",
    bgColor: "bg-primary-50",
    badge: null,
  },
  {
    icon: ShoppingCart,
    title: "Drive en 1 clic",
    description:
      "Leclerc, Auchan, Intermarché, Carrefour. Votre panier se remplit automatiquement.",
    color: "text-secondary-600",
    bgColor: "bg-secondary-50",
    badge: "Bientôt",
  },
  {
    icon: BookOpen,
    title: "Livre PDF du dimanche",
    description:
      "Chaque dimanche, recevez votre livre de recettes personnalisé. Imprimable, partageable.",
    color: "text-accent-700",
    bgColor: "bg-accent-50",
    badge: null,
  },
] as const;

const HOW_IT_WORKS = [
  {
    step: 1,
    icon: CalendarDays,
    title: "Répondez à 3 questions",
    description: "Famille, régimes, temps disponible. 90 secondes, pas plus.",
  },
  {
    step: 2,
    icon: Brain,
    title: "Presto génère votre semaine",
    description: "5 à 7 dîners personnalisés, équilibrés, adaptés à vos goûts.",
  },
  {
    step: 3,
    icon: Star,
    title: "Cuisinez et notez",
    description: "Chaque retour affine Presto. Semaine après semaine, c'est de mieux en mieux.",
  },
] as const;

// Recettes fallback statiques si l'API n'est pas joignable
// Images Unsplash food éditoriales en placeholder (domaine autorisé dans next.config.mjs)
const FALLBACK_RECIPES: Array<{
  id: string;
  title: string;
  description: string;
  cuisine: string;
  total_time_minutes: number;
  servings: number;
  difficulty: "easy" | "medium" | "hard";
  image_url: string | null;
  dietary_tags: string[];
  rating_average: number | null;
}> = [
  {
    id: "fallback-1",
    title: "Poulet rôti aux herbes de Provence",
    description: "Le classique dominical revisité, tendre et parfumé.",
    cuisine: "Français",
    total_time_minutes: 75,
    servings: 4,
    difficulty: "easy",
    image_url:
      "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800&auto=format&fit=crop",
    dietary_tags: [],
    rating_average: 4.8,
  },
  {
    id: "fallback-2",
    title: "Risotto aux champignons",
    description: "Crémeux, parfumé au parmesan, prêt en 35 minutes.",
    cuisine: "Italien",
    total_time_minutes: 35,
    servings: 4,
    difficulty: "medium",
    image_url:
      "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=800&auto=format&fit=crop",
    dietary_tags: ["vegetarian"],
    rating_average: 4.6,
  },
  {
    id: "fallback-3",
    title: "Poulet tikka masala maison",
    description: "La sauce curry crémeuse qui fait l'unanimité à table.",
    cuisine: "Indien",
    total_time_minutes: 50,
    servings: 4,
    difficulty: "medium",
    image_url:
      "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?q=80&w=800&auto=format&fit=crop",
    dietary_tags: [],
    rating_average: 4.7,
  },
];

// BUG 7 FIX : getRecipes déclaré APRÈS FALLBACK_RECIPES pour éviter la TDZ (temporal dead zone)
// NEXT_PUBLIC_API_URL est embedded au build time par Vercel — disponible en RSC
async function getRecipes(): Promise<Recipe[]> {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    "https://meal-planner-saas-production.up.railway.app";

  try {
    const res = await fetch(`${apiUrl}/api/v1/recipes?per_page=6`, {
      next: { revalidate: 300 },
      // Timeout 5s — ne pas bloquer le rendu si Railway est down
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return FALLBACK_RECIPES as unknown as Recipe[];
    const data = (await res.json()) as RecipesApiResponse | Recipe[];
    if (Array.isArray(data))
      return data.length > 0 ? data.slice(0, 3) : (FALLBACK_RECIPES as unknown as Recipe[]);
    const results = (data.results ?? data.items ?? []).slice(0, 3);
    return results.length > 0 ? results : (FALLBACK_RECIPES as unknown as Recipe[]);
  } catch {
    // AbortError (timeout), réseau, CORS — fallback statique sans crash
    return FALLBACK_RECIPES as unknown as Recipe[];
  }
}

// --- Composant StaticRecipeCard (Server Component, pas de "use client") ---
// Design food premium portrait 4:5 — badge temps terracotta + rating overlay
// Distinct du RecipeCard client pour éviter le bundle Framer Motion sur la landing

interface StaticRecipeCardProps {
  recipe: (typeof FALLBACK_RECIPES)[0] | Recipe;
  priority?: boolean;
}

function StaticRecipeCard({ recipe, priority = false }: StaticRecipeCardProps) {
  const time = recipe.total_time_minutes;
  const rating =
    recipe.rating_average != null ? Number(recipe.rating_average).toFixed(1) : null;

  return (
    <article className="group block">
      {/* Image container — ratio portrait 4:5 */}
      <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-[#857370]/10">
        {recipe.image_url ? (
          <Image
            src={recipe.image_url}
            alt={recipe.title}
            fill
            sizes="(max-width: 768px) 100vw, 33vw"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
            priority={priority}
          />
        ) : (
          <div
            className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#E2725B]/10 to-[#E2725B]/20"
            aria-hidden="true"
          />
        )}

        {/* Badge temps — overlay haut-droite terracotta */}
        {time > 0 && (
          <span className="absolute right-3 top-3 rounded-full bg-[#E2725B]/90 px-3 py-1.5 text-xs font-semibold text-white shadow-sm">
            {time} MIN
          </span>
        )}

        {/* Rating — overlay bas-gauche */}
        {rating != null && (
          <div className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-black/40 px-2.5 py-1 backdrop-blur-sm">
            <span className="text-amber-400 text-xs leading-none" aria-hidden="true">★</span>
            <span className="text-xs font-semibold text-white">{rating}</span>
          </div>
        )}
      </div>

      {/* Catégorie — small caps terracotta outline */}
      {recipe.cuisine && (
        <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-[#857370]">
          {recipe.cuisine}
        </p>
      )}

      {/* Titre — Noto Serif bold, 2 lignes max */}
      <h3 className="mt-1 font-serif text-base font-bold leading-snug text-[#201a19] line-clamp-2 group-hover:text-[#E2725B] transition-colors duration-200">
        {recipe.title}
      </h3>

      {/* Meta — temps + personnes */}
      <div className="mt-2 flex items-center gap-3 text-xs text-[#857370]">
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {time} min
        </span>
        <span className="flex items-center gap-1">
          <Users className="h-3.5 w-3.5" aria-hidden="true" />
          {recipe.servings} pers.
        </span>
        {rating != null && (
          <span className="flex items-center gap-1">
            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" aria-hidden="true" />
            {rating}
          </span>
        )}
      </div>
    </article>
  );
}

// --- Page principale ---

export default async function LandingPage() {
  // Fetch RSC — ne bloque pas le rendu si l'API est down (try/catch interne)
  const recipes = await getRecipes();
  const displayRecipes = recipes.length > 0 ? recipes : FALLBACK_RECIPES;

  return (
    <>
      {/* =========================================
          HEADER STICKY — navigation landing
      ========================================= */}
      <header className="sticky top-0 z-50 border-b border-[#857370]/20 bg-[#fff8f6]/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            aria-label="Presto — retour à l'accueil"
          >
            <Image src="/logo_maj.png" alt="Presto" width={140} height={44} priority className="mix-blend-multiply object-contain" />
          </Link>

          {/* Navigation desktop */}
          <nav
            className="hidden items-center gap-6 md:flex"
            aria-label="Navigation principale"
          >
            <a
              href="#features"
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Fonctionnalités
            </a>
            <a
              href="#how-it-works"
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Comment ça marche
            </a>
            <a
              href="#recipes"
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Recettes
            </a>
            <a
              href="#pricing"
              className="text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Tarifs
            </a>
          </nav>

          {/* CTAs header */}
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="hidden text-sm font-medium text-neutral-600 transition-colors hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 sm:block"
            >
              Se connecter
            </Link>
            <Link
              href="/signup"
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-primary-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
            >
              Commencer
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>

      <main id="main-content" className="min-h-dvh bg-[#fff8f6]">
        {/* =========================================
            HERO — typographie Fraunces généreuse
        ========================================= */}
        <section
          className="relative flex min-h-[85dvh] flex-col items-center justify-center px-6 py-20 text-center"
          aria-labelledby="hero-title"
        >
          {/* Badge de lancement */}
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-4 py-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-primary-700">
              Beta fermée — rejoignez la liste
            </span>
          </div>

          {/* Titre principal en Fraunces */}
          <h1
            id="hero-title"
            className="font-serif mb-6 max-w-3xl text-5xl font-bold leading-tight text-neutral-900 md:text-7xl md:leading-none"
          >
            Le{" "}
            <span className="text-primary-500">livre de recettes</span>{" "}
            de votre famille,{" "}
            <span className="italic">réinventé</span> par Presto.
          </h1>

          {/* Sous-titre */}
          <p className="mb-10 max-w-xl text-lg leading-relaxed text-neutral-600 md:text-xl">
            Planifiez 5 dîners par semaine en 30 secondes. Presto apprend les goûts de votre
            famille, remplit votre panier drive et génère votre livre PDF du dimanche.
          </p>

          {/* CTA principal */}
          <div className="flex flex-col items-center gap-4 sm:flex-row">
            <Link
              href="/onboarding"
              className="inline-flex min-h-[56px] items-center gap-2 rounded-xl bg-primary-500 px-8 py-4 text-lg font-semibold text-primary-foreground shadow-lg transition-all duration-200 hover:bg-primary-600 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
            >
              Commencer gratuitement
              <ArrowRight className="h-5 w-5" aria-hidden="true" />
            </Link>
            <span className="text-sm text-neutral-500">14 jours gratuits, sans CB</span>
          </div>

          {/* Social proof */}
          <p className="mt-8 text-sm text-neutral-400">
            Rejoignez les familles françaises qui planifient mieux leurs repas
          </p>
        </section>

        {/* =========================================
            VALUE PROPS — 3 colonnes
        ========================================= */}
        <section
          id="features"
          className="border-t border-neutral-200 bg-[hsl(38,60%,97%)] px-6 py-20"
          aria-labelledby="value-props-title"
        >
          <div className="mx-auto max-w-5xl">
            <h2
              id="value-props-title"
              className="font-serif mb-4 text-center text-4xl font-semibold text-neutral-900"
            >
              Pourquoi les familles adorent Presto
            </h2>
            <p className="mb-12 text-center text-base text-neutral-500">
              Une seule app. Toute la magie.
            </p>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              {VALUE_PROPS.map((prop) => {
                const Icon = prop.icon;
                return (
                  <article
                    key={prop.title}
                    className="relative rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm transition-shadow duration-200 hover:shadow-md"
                  >
                    {/* Badge "Bientôt" */}
                    {prop.badge && (
                      <span className="absolute right-4 top-4 rounded-full bg-primary-100 px-2.5 py-0.5 text-xs font-semibold text-primary-700">
                        {prop.badge}
                      </span>
                    )}

                    {/* Icône */}
                    <div
                      className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl ${prop.bgColor}`}
                      aria-hidden="true"
                    >
                      <Icon className={`h-6 w-6 ${prop.color}`} strokeWidth={1.5} />
                    </div>

                    <h3 className="font-serif mb-3 text-xl font-semibold text-neutral-900">
                      {prop.title}
                    </h3>
                    <p className="text-base leading-relaxed text-neutral-600">
                      {prop.description}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* =========================================
            COMMENT CA MARCHE — 3 étapes
        ========================================= */}
        <section
          id="how-it-works"
          className="border-t border-neutral-200 bg-white px-6 py-20"
          aria-labelledby="how-title"
        >
          <div className="mx-auto max-w-5xl">
            <h2
              id="how-title"
              className="font-serif mb-4 text-center text-4xl font-semibold text-neutral-900"
            >
              Comment ça marche ?
            </h2>
            <p className="mb-16 text-center text-base text-neutral-500">
              De zéro à votre premier planning en moins de 2 minutes.
            </p>

            {/* Timeline desktop horizontale / mobile verticale */}
            <div className="relative">
              {/* Ligne de connexion desktop */}
              <div
                className="absolute left-1/2 top-[28px] hidden h-0.5 w-[calc(66%-2rem)] -translate-x-1/2 bg-gradient-to-r from-primary-200 via-primary-300 to-primary-200 md:block"
                aria-hidden="true"
              />

              <ol className="relative flex flex-col gap-8 md:flex-row md:gap-0">
                {HOW_IT_WORKS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li
                      key={item.step}
                      className="flex flex-1 flex-col items-center text-center md:px-6"
                    >
                      {/* Numéro en cercle terracotta */}
                      <div
                        className="relative z-10 mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary-500 shadow-lg shadow-primary-500/20"
                        aria-hidden="true"
                      >
                        <Icon className="h-6 w-6 text-white" strokeWidth={1.5} />
                        <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-white text-[11px] font-bold text-primary-600 shadow-sm ring-1 ring-primary-200">
                          {item.step}
                        </span>
                      </div>

                      <h3 className="font-serif mb-2 text-lg font-semibold text-neutral-900">
                        {item.title}
                      </h3>
                      <p className="text-sm leading-relaxed text-neutral-500">
                        {item.description}
                      </p>
                    </li>
                  );
                })}
              </ol>
            </div>

            {/* CTA sous la timeline */}
            <div className="mt-12 text-center">
              <Link
                href="/onboarding"
                className="inline-flex min-h-[52px] items-center gap-2 rounded-xl bg-primary-500 px-8 py-3 text-base font-semibold text-white shadow-md transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
              >
                Essayer maintenant — c&apos;est gratuit
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>

        {/* =========================================
            RECETTES DU MONDE — fetch RSC, design food premium portrait
        ========================================= */}
        <section
          id="recipes"
          className="border-t border-neutral-200 bg-[#fff8f6] px-6 py-20"
          aria-labelledby="recipes-title"
        >
          <div className="mx-auto max-w-5xl">
            {/* Sous-titre small caps terracotta */}
            <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#E2725B]">
              Des saveurs du monde entier
            </p>
            <h2
              id="recipes-title"
              className="font-serif mt-2 mb-4 text-center text-4xl font-bold text-[#201a19]"
            >
              Des recettes du monde entier
            </h2>
            <p className="mb-12 text-center text-base text-[#857370]">
              Plus de 200 recettes testées, adaptées aux familles françaises.
              {recipes.length === 0 && (
                <span className="ml-1 text-xs text-[#857370]/60">(aperçu — données illustratives)</span>
              )}
            </p>

            {/* Grille portrait 4:5 — 1 colonne mobile → 3 desktop */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {displayRecipes.map((recipe, index) => (
                <StaticRecipeCard
                  key={recipe.id}
                  recipe={recipe}
                  priority={index < 2}
                />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/recipes"
                className="inline-flex items-center gap-2 rounded-full border border-[#857370]/20 bg-white px-6 py-3 text-sm font-medium text-[#201a19] transition-all hover:border-[#E2725B]/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E2725B]/40"
              >
                Explorer toutes les recettes
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </section>

        {/* =========================================
            PRICING — 2 plans
        ========================================= */}
        <section
          id="pricing"
          className="border-t border-neutral-200 bg-white px-6 py-20"
          aria-labelledby="pricing-title"
        >
          <div className="mx-auto max-w-4xl">
            <h2
              id="pricing-title"
              className="font-serif mb-4 text-center text-4xl font-semibold text-neutral-900"
            >
              Un prix simple et transparent
            </h2>
            <p className="mb-12 text-center text-base text-neutral-500">
              Commencez gratuitement. Passez au plan Famille quand vous êtes convaincu.
            </p>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {/* Plan Starter */}
              <article
                className="flex flex-col rounded-2xl border border-neutral-200 bg-neutral-50 p-8"
                aria-label="Plan Starter — gratuit"
              >
                <div className="mb-6">
                  <p className="mb-1 text-sm font-semibold uppercase tracking-wide text-neutral-400">
                    Starter
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className="font-serif text-4xl font-bold text-neutral-900">
                      Gratuit
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-neutral-500">Pour découvrir Presto</p>
                </div>

                <ul className="mb-8 flex-1 space-y-3">
                  {[
                    "3 recettes par semaine",
                    "Liste de courses basique",
                    "Profil individuel",
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2.5 text-sm text-neutral-600">
                      <span
                        className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-neutral-200 text-neutral-500"
                        aria-hidden="true"
                      >
                        ✓
                      </span>
                      {feature}
                    </li>
                  ))}
                  {[
                    "Livre PDF hebdomadaire",
                    "Drive intégré",
                    "Profils famille",
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2.5 text-sm text-neutral-400 line-through decoration-neutral-300">
                      <span
                        className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-neutral-100"
                        aria-hidden="true"
                      >
                        ✗
                      </span>
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/signup"
                  className="inline-flex min-h-[48px] w-full items-center justify-center rounded-xl border border-neutral-300 bg-white px-6 py-3 text-sm font-semibold text-neutral-700 transition-all hover:border-neutral-400 hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-[0.98]"
                >
                  Commencer gratuitement
                </Link>
              </article>

              {/* Plan Famille */}
              <article
                className="relative flex flex-col rounded-2xl border-2 border-primary-500 bg-white p-8 shadow-md shadow-primary-500/10"
                aria-label="Plan Famille — 9,99€/mois"
              >
                {/* Badge Populaire */}
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center rounded-full bg-primary-500 px-4 py-1 text-xs font-bold uppercase tracking-wide text-white shadow-sm">
                    Populaire
                  </span>
                </div>

                <div className="mb-6 pt-2">
                  <p className="mb-1 text-sm font-semibold uppercase tracking-wide text-primary-600">
                    Famille
                  </p>
                  <div className="flex items-baseline gap-1">
                    <span className="font-serif text-4xl font-bold text-neutral-900">
                      9,99€
                    </span>
                    <span className="text-sm text-neutral-400">/mois</span>
                  </div>
                  <p className="mt-2 text-sm text-neutral-500">Presto s&apos;adapte à votre famille</p>
                </div>

                <ul className="mb-8 flex-1 space-y-3">
                  {[
                    "7 dîners générés par Presto",
                    "Profils famille illimités",
                    "Livre PDF hebdomadaire",
                    "Liste de courses partagée",
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2.5 text-sm text-neutral-700">
                      <span
                        className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-600"
                        aria-hidden="true"
                      >
                        ✓
                      </span>
                      {feature}
                    </li>
                  ))}
                  <li className="flex items-center gap-2.5 text-sm text-neutral-400">
                    <span
                      className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-neutral-100 text-neutral-400"
                      aria-hidden="true"
                    >
                      ✓
                    </span>
                    Drive intégré{" "}
                    <span className="ml-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs font-semibold text-primary-600">
                      Bientôt
                    </span>
                  </li>
                </ul>

                <Link
                  href="/signup"
                  className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl bg-primary-500 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-primary-500/20 transition-all hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-[0.98]"
                >
                  Commencer — 14 jours gratuits
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <p className="mt-3 text-center text-xs text-neutral-400">
                  Sans engagement. Résiliable à tout moment.
                </p>
              </article>
            </div>
          </div>
        </section>

        {/* =========================================
            CTA FINAL
        ========================================= */}
        <section className="border-t border-neutral-200 bg-[hsl(38,60%,97%)] px-6 py-20 text-center" aria-labelledby="cta-title">
          <div className="mx-auto max-w-2xl">
            <h2
              id="cta-title"
              className="font-serif mb-4 text-4xl font-bold text-neutral-900"
            >
              Votre première semaine, en 90 secondes.
            </h2>
            <p className="mb-8 text-lg text-neutral-600">
              3 questions, et nous générons votre plan de la semaine. Gratuit pendant 14 jours.
            </p>
            <Link
              href="/onboarding"
              className="inline-flex min-h-[56px] items-center gap-2 rounded-xl bg-primary-500 px-8 py-4 text-lg font-semibold text-primary-foreground shadow-lg transition-all duration-200 hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 active:scale-95"
            >
              Commencer — c&apos;est gratuit
              <ArrowRight className="h-5 w-5" aria-hidden="true" />
            </Link>
            <p className="mt-4 text-sm text-neutral-400">
              9,99€/mois après l&apos;essai. Résiliable à tout moment.
            </p>
          </div>
        </section>

        {/* =========================================
            FOOTER
        ========================================= */}
        <footer className="border-t border-neutral-200 bg-white px-6 py-12">
          <div className="mx-auto max-w-5xl">
            <div className="flex flex-col items-center gap-6 md:flex-row md:items-start md:justify-between">
              {/* Logo + baseline */}
              <div>
                <Image src="/logo_maj.png" alt="Presto" width={120} height={38} className="mix-blend-multiply object-contain" />
                <p className="mt-1 text-sm text-neutral-400">
                  Le livre de recettes de votre famille, réinventé par Presto.
                </p>
              </div>

              {/* Liens */}
              <nav
                className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-neutral-500 md:justify-end"
                aria-label="Liens du pied de page"
              >
                <Link
                  href="/about"
                  className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  À propos
                </Link>
                <Link
                  href="/legal/terms"
                  className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  CGV
                </Link>
                <Link
                  href="/legal/privacy"
                  className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  Confidentialité
                </Link>
                <Link
                  href="/contact"
                  className="hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  Contact
                </Link>
              </nav>
            </div>

            {/* Bas de footer */}
            <div className="mt-8 flex flex-col items-center gap-2 border-t border-neutral-100 pt-8 text-center text-xs text-neutral-400 md:flex-row md:justify-between md:text-left">
              <p>Made with ❤️ en France</p>
              <p>© 2026 Presto. Tous droits réservés.</p>
            </div>
          </div>
        </footer>
      </main>
    </>
  );
}
