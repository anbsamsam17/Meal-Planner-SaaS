// apps/web/src/lib/api/endpoints.ts
// Fonctions typées pour chaque endpoint API — couche d'abstraction sur apiClient
// Alignées sur les contrats backend Phase 1 + Phase 2 (backend-developer en parallèle)
// Toutes les requêtes nécessitent un JWT Supabase (sauf /health)
// FIX Phase 1 mature (review 2026-04-12) : alignement contrats frontend↔backend (5 mismatches)
// Phase 2 (2026-04-12) : billing, frigo, livres PDF, filtres avancés

import { apiClient } from "./client";
import type {
  Recipe,
  ShoppingListItem,
  DietaryTag,
  DriveProvider,
  BillingStatus,
  CheckoutResponse,
  PortalResponse,
  FridgeItem,
  FridgeItemCreate,
  FridgeSuggestionsResponse,
  BookInfo,
  BookGenerateResponse,
  RecipeFilters,
  PaginatedResponse,
} from "./types";

// --- Types de requête/réponse alignés sur les contrats API Phase 1 ---

export interface HouseholdCreate {
  name: string;
  // FIX Phase 1 mature (review 2026-04-12) — Mismatch A : backend attend `first_member`, pas `member`
  // Schéma Pydantic HouseholdCreate — champ : first_member
  first_member: {
    display_name: string;
    is_child: boolean;
    birth_date?: string | null;
  };
}

export interface MemberCreate {
  display_name: string;
  is_child: boolean;
  birth_date?: string | null;
}

export interface MemberPreferences {
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
  cooking_time_max: number;
  // FIX Phase 1 mature (review 2026-04-12) — Mismatch C : backend attend les valeurs FR
  // Schéma Pydantic — enum budget_pref : "économique" | "moyen" | "premium"
  budget_pref: "économique" | "moyen" | "premium" | null;
}

export interface HouseholdMemberAPI {
  id: string;
  display_name: string;
  is_child: boolean;
  birth_date: string | null;
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
}

export interface HouseholdPreferencesAPI {
  cooking_time_max: number;
  // FIX Phase 1 mature (review 2026-04-12) — Mismatch C aligné sur l'enum FR
  budget_pref: "économique" | "moyen" | "premium" | null;
  drive_provider: DriveProvider | null;
}

export interface HouseholdAPI {
  id: string;
  owner_id: string;
  name: string;
  drive_provider: DriveProvider | null;
}

export interface HouseholdResponse {
  household: HouseholdAPI;
  members: HouseholdMemberAPI[];
  preferences: HouseholdPreferencesAPI | null;
}

// FIX BLOQUANT 3+4 (2026-04-12) — Aligne PlannedMeal sur le backend (day_of_week int, champs enrichis)
// Le backend retourne day_of_week comme int (1=lundi ISO) et des champs denormalises recipe_*
export interface PlannedMeal {
  id: string;
  plan_id: string;
  day_of_week: number; // 1=lundi, 7=dimanche (int ISO, pas de string)
  slot: string; // "dinner", "lunch", etc.
  recipe_id: string;
  servings_adjusted: number;
  // Champs enrichis denormalises depuis la recette (retournes par le backend)
  recipe_title?: string | null;
  recipe_photo_url?: string | null;
  recipe_total_time_min?: number | null;
  recipe_difficulty?: number | null;
  recipe_cuisine_type?: string | null;
}

// FIX BLOQUANT 3 (2026-04-12) — PlanDetail est plat (pas de champ `plan` wrapper)
// Le backend retourne les champs du plan directement au top-level.
// Status backend : "draft" | "validated" | "archived"
export interface PlanDetail {
  id: string;
  household_id: string;
  week_start: string; // ISO date "YYYY-MM-DD"
  status: "draft" | "validated" | "archived";
  validated_at?: string | null;
  created_at: string;
  updated_at: string;
  meals: PlannedMeal[];
  shopping_list?: ShoppingListItem[];
}

export interface GeneratePlanResponse {
  task_id: string;
}

// FIX Phase 1 mature (review 2026-04-12) — Mismatch E : body generatePlan avec week_start obligatoire
// Etendu avec filtres optionnels pour le modal "4 questions"
export interface GeneratePlanBody {
  week_start: string; // ISO date du lundi de la semaine cible, ex: "2026-04-13"
  num_dinners?: number;
  max_time?: number | null;
  budget?: string | null;
  style?: string | null;
}

// Parametres de generation exposes aux composants
export interface GeneratePlanParams {
  week_start?: string;
  num_dinners?: number;
  max_time?: number | null;
  budget?: string | null;
  style?: string | null;
}

// Calcule le lundi de la semaine courante (ou le prochain si on est après lundi)
// Utilisé pour construire le body de POST /plans/generate
export function getNextMonday(): string {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = dimanche, 1 = lundi, ...
  // Si on est lundi → 0 jours d'écart, sinon calculer le prochain lundi
  const daysUntilMonday = dayOfWeek === 0 ? 1 : dayOfWeek === 1 ? 0 : 8 - dayOfWeek;
  const nextMonday = new Date(today);
  nextMonday.setDate(today.getDate() + daysUntilMonday);
  return nextMonday.toISOString().split("T")[0] as string;
}

export interface RecipeSearchParams {
  q?: string;
  cuisine?: string;
  max_time?: number;
  diet?: DietaryTag;
}

// --- Endpoints Household ---

export async function createHousehold(data: HouseholdCreate): Promise<HouseholdResponse> {
  return apiClient.post<HouseholdResponse>("/api/v1/households", data);
}

export async function getMyHousehold(): Promise<HouseholdResponse> {
  return apiClient.get<HouseholdResponse>("/api/v1/households/me");
}

export async function addHouseholdMember(data: MemberCreate): Promise<HouseholdMemberAPI> {
  return apiClient.post<HouseholdMemberAPI>("/api/v1/households/me/members", data);
}

export async function updateMemberPreferences(
  memberId: string,
  preferences: MemberPreferences,
): Promise<HouseholdMemberAPI> {
  return apiClient.patch<HouseholdMemberAPI>(
    `/api/v1/households/me/members/${memberId}/preferences`,
    preferences,
  );
}

// --- Endpoints Plans ---

// FIX Phase 1 mature (review 2026-04-12) — Mismatch E : body vide → { week_start } obligatoire
// Etendu : accepte filtres optionnels max_time, budget, style depuis le modal "4 questions"
export async function generatePlan(params?: GeneratePlanParams): Promise<GeneratePlanResponse> {
  const body: GeneratePlanBody = {
    week_start: params?.week_start ?? getNextMonday(),
    ...(params?.num_dinners != null && { num_dinners: params.num_dinners }),
    ...(params?.max_time != null && { max_time: params.max_time }),
    ...(params?.budget != null && { budget: params.budget }),
    ...(params?.style != null && { style: params.style }),
  };
  return apiClient.post<GeneratePlanResponse>("/api/v1/plans/generate", body);
}

// Suggestions de recettes pour le swap/ajout — GET /api/v1/plans/{plan_id}/suggestions
export async function getRecipeSuggestions(
  planId: string,
  filters?: { style?: string; max_time?: number },
): Promise<Recipe[]> {
  const params = new URLSearchParams();
  if (filters?.style) params.set("style", filters.style);
  if (filters?.max_time) params.set("max_time", String(filters.max_time));
  const qs = params.toString();
  const raw = await apiClient.get<Record<string, unknown>[]>(
    `/api/v1/plans/${planId}/suggestions${qs ? `?${qs}` : ""}`,
  );
  // L'API peut retourner un tableau directement ou un objet { recipes: [...] }
  const recipes = Array.isArray(raw) ? raw : ((raw as unknown as Record<string, unknown>).recipes as Record<string, unknown>[]) ?? [];
  return recipes as unknown as Recipe[];
}

// Ajouter un repas a un plan (samedi/dimanche) — POST /api/v1/plans/{plan_id}/meals/add
export async function addMealToPlan(
  planId: string,
  dayOfWeek: number,
  recipeId: string,
): Promise<PlannedMeal> {
  return apiClient.post<PlannedMeal>(`/api/v1/plans/${planId}/meals/add`, {
    day_of_week: dayOfWeek,
    recipe_id: recipeId,
  });
}

// FIX BLOQUANT 3 (2026-04-12) — Normalise la reponse API vers PlanDetail plat
// Le backend retourne deja une structure plate, on s'assure que les champs sont presents
function normalizePlanDetail(raw: Record<string, unknown>): PlanDetail {
  return {
    id: raw.id as string,
    household_id: raw.household_id as string,
    week_start: raw.week_start as string,
    status: raw.status as PlanDetail["status"],
    validated_at: (raw.validated_at as string | null) ?? null,
    created_at: raw.created_at as string,
    updated_at: raw.updated_at as string,
    meals: (raw.meals as PlannedMeal[]) ?? [],
    shopping_list: (raw.shopping_list as ShoppingListItem[]) ?? [],
  };
}

export async function getPlan(id: string): Promise<PlanDetail> {
  const raw = await apiClient.get<Record<string, unknown>>(`/api/v1/plans/${id}`);
  return normalizePlanDetail(raw);
}

export async function getCurrentPlan(): Promise<PlanDetail> {
  const raw = await apiClient.get<Record<string, unknown>>("/api/v1/plans/me/current");
  return normalizePlanDetail(raw);
}

export async function validatePlan(planId: string): Promise<void> {
  return apiClient.post<void>(`/api/v1/plans/${planId}/validate`, {});
}

export async function swapMeal(
  planId: string,
  mealId: string,
  recipeId: string,
): Promise<PlannedMeal> {
  return apiClient.patch<PlannedMeal>(`/api/v1/plans/${planId}/meals/${mealId}`, {
    new_recipe_id: recipeId,
  });
}

// Formate les quantites API [{quantity, unit}, ...] en string lisible
function formatShoppingQuantities(quantities: unknown): string {
  if (!Array.isArray(quantities) || quantities.length === 0) return "";
  return quantities
    .map((q: Record<string, unknown>) => `${q.quantity ?? ""} ${q.unit ?? ""}`.trim())
    .join(", ");
}

// Mappe le label rayon francais (backend) vers IngredientCategory (frontend)
// Le backend genere _smart_rayon() qui retourne des labels FR
// Les categories DB sont souvent "other" pour les ingredients TheMealDB
type ShoppingCategory = ShoppingListItem["category"];
const RAYON_FR_TO_CATEGORY: Record<string, ShoppingCategory> = {
  "Epicerie": "grains",
  "Boucherie": "meat",
  "Volaille": "meat",
  "Poissonnerie": "fish",
  "Fruits & legumes": "vegetables",
  "Fruits & légumes": "vegetables",
  "Légumes": "vegetables",
  "Fruits": "fruits",
  "Cremerie": "dairy",
  "Crèmerie": "dairy",
  "Épicerie": "grains",
  "Épices": "herbs",
  "Herbes fraîches": "herbs",
  "Herbes fraiches": "herbs",
  "Huiles & condiments": "condiments",
  "Sauces": "condiments",
  "Légumineuses": "legumes",
};

function mapRayonToCategory(rayon: string | undefined, category: string | undefined): ShoppingCategory {
  // Priorite au rayon FR si disponible (plus precis que category brute de la DB)
  if (rayon && RAYON_FR_TO_CATEGORY[rayon]) {
    return RAYON_FR_TO_CATEGORY[rayon];
  }
  // Fallback sur la category brute si elle correspond a une IngredientCategory valide
  const validCategories: ShoppingCategory[] = [
    "vegetables", "fruits", "meat", "fish", "dairy",
    "grains", "legumes", "condiments", "herbs", "other",
  ];
  if (category && validCategories.includes(category as ShoppingCategory)) {
    return category as ShoppingCategory;
  }
  return "other";
}

export async function getShoppingList(planId: string): Promise<ShoppingListItem[]> {
  // Backend route: GET /api/v1/plans/me/{plan_id}/shopping-list
  // Le prefix /me/ est obligatoire pour passer avant la route dynamique /{plan_id}
  const raw = await apiClient.get<Record<string, unknown>[]>(
    `/api/v1/plans/me/${planId}/shopping-list`,
  );

  // Normaliser les champs API bruts -> ShoppingListItem frontend
  // L'API retourne : { ingredient_id, canonical_name, category, rayon, quantities, checked, in_fridge }
  // Le frontend attend : { id, ingredient_name, quantity, unit, category, is_checked, is_in_stock }
  if (!Array.isArray(raw)) return [];

  return raw.map((item, idx) => {
    const quantities = item.quantities as Array<Record<string, unknown>> | undefined;
    const firstQ = Array.isArray(quantities) && quantities.length > 0 ? quantities[0] : null;

    return {
      id: (item.id as string) ?? (item.ingredient_id as string) ?? `item-${idx}`,
      ingredient_name: (item.ingredient_name as string) ?? (item.canonical_name as string) ?? "Ingredient",
      quantity: firstQ ? (typeof firstQ.quantity === "number" ? firstQ.quantity : 0) : 0,
      unit: firstQ ? (typeof firstQ.unit === "string" ? firstQ.unit : "") : "",
      category: mapRayonToCategory(item.rayon as string | undefined, item.category as string | undefined),
      is_checked: (item.is_checked as boolean) ?? (item.checked as boolean) ?? false,
      is_in_stock: (item.is_in_stock as boolean) ?? (item.in_fridge as boolean) ?? false,
      quantity_display: formatShoppingQuantities(quantities),
      recipe_ids: Array.isArray(item.recipe_ids) ? (item.recipe_ids as string[]) : [],
      estimated_price: (item.estimated_price as number) ?? null,
      open_food_facts_id: (item.open_food_facts_id as string) ?? (item.off_id as string) ?? null,
    };
  });
}

// --- Normalisation Recipe : mappe les champs API bruts vers les champs frontend ---

/**
 * Convertit une difficulté numérique (1-5) en label textuel.
 * Conserve le format string si déjà normalisé.
 */
function mapDifficulty(d: unknown): "easy" | "medium" | "hard" | null {
  if (d == null) return null;
  // Si déjà un label textuel, le retourner tel quel
  if (d === "easy" || d === "medium" || d === "hard") return d;
  // Conversion numérique : 1-2 → easy, 3 → medium, 4-5 → hard
  const num = typeof d === "number" ? d : Number(d);
  if (Number.isNaN(num)) return null;
  if (num <= 2) return "easy";
  if (num <= 3) return "medium";
  return "hard";
}

/**
 * Normalise un objet recette brut de l'API vers le type Recipe frontend.
 * Conserve aussi les champs API originaux pour compatibilité descendante.
 */
function normalizeRecipe(apiRecipe: Record<string, unknown>): Recipe {
  const raw = apiRecipe as Record<string, any>;
  return {
    ...raw,
    // Champs normalisés mappés depuis les noms API
    id: raw.id,
    title: raw.title,
    slug: raw.slug ?? undefined,
    description: raw.description ?? null,
    image_url: raw.photo_url ?? raw.image_url ?? null,
    total_time_minutes: raw.total_time_min ?? raw.total_time_minutes ?? null,
    prep_time_minutes: raw.prep_time_min ?? raw.prep_time_minutes ?? null,
    cook_time_minutes: raw.cook_time_min ?? raw.cook_time_minutes ?? null,
    cuisine: raw.cuisine_type ?? raw.cuisine ?? null,
    difficulty: mapDifficulty(raw.difficulty),
    dietary_tags: raw.tags ?? raw.dietary_tags ?? [],
    rating_average: raw.quality_score != null ? Math.min(5, raw.quality_score * 5) : (raw.rating_average ?? null),
    rating_count: raw.rating_count ?? 0,
    servings: raw.servings ?? null,
    // Champs API originaux conservés pour les composants qui les lisent directement
    photo_url: raw.photo_url ?? null,
    total_time_min: raw.total_time_min ?? null,
    prep_time_min: raw.prep_time_min ?? null,
    cook_time_min: raw.cook_time_min ?? null,
    cuisine_type: raw.cuisine_type ?? null,
    tags: raw.tags ?? [],
    quality_score: raw.quality_score ?? null,
  } as Recipe;
}

// --- Endpoints Recipes ---

export async function getRecipe(id: string): Promise<Recipe> {
  const raw = await apiClient.get<Record<string, unknown>>(`/api/v1/recipes/${id}`);
  return normalizeRecipe(raw);
}

export async function searchRecipes(params: RecipeSearchParams): Promise<Recipe[]> {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set("q", params.q);
  if (params.cuisine) searchParams.set("cuisine", params.cuisine);
  if (params.max_time) searchParams.set("max_time", String(params.max_time));
  if (params.diet) searchParams.set("diet", params.diet);

  const queryString = searchParams.toString();
  return apiClient.get<Recipe[]>(`/api/v1/recipes/search${queryString ? `?${queryString}` : ""}`);
}

// Recherche recettes avec filtres avancés Phase 2
// BUG-001 fix : l'API attend max_difficulty (pas difficulty)
// BUG-005 fix : normalisation des recettes retournées
export async function searchRecipesAdvanced(
  filters: RecipeFilters,
): Promise<PaginatedResponse<Recipe>> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.cuisine) params.set("cuisine", filters.cuisine);
  if (filters.max_time) params.set("max_time", String(filters.max_time));
  // BUG-001 : l'API déclare min_difficulty / max_difficulty, pas "difficulty"
  // On envoie max_difficulty pour filtrer "au plus cette difficulté"
  if (filters.difficulty) params.set("max_difficulty", String(filters.difficulty));
  if (filters.budget) params.set("budget", filters.budget);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  // L'API n'accepte qu'un seul diet (str | None) -- envoyer uniquement le premier
  if (filters.diet) {
    const firstDiet = Array.isArray(filters.diet) ? filters.diet[0] : filters.diet;
    if (firstDiet) params.set("diet", firstDiet);
  }

  const qs = params.toString();
  const raw = await apiClient.get<Record<string, any>>(`/api/v1/recipes${qs ? `?${qs}` : ""}`);

  // L'API retourne { results: [...], total, page, per_page }
  // On normalise chaque recette pour aligner les champs
  const rawRecipes: Record<string, unknown>[] = raw.results ?? raw.data ?? [];
  const normalizedRecipes = rawRecipes.map(normalizeRecipe);

  return {
    data: normalizedRecipes,
    results: normalizedRecipes,
    total: raw.total ?? 0,
    page: raw.page ?? 1,
    per_page: raw.per_page ?? filters.per_page ?? 24,
    has_next: raw.has_next ?? false,
  } as PaginatedResponse<Recipe> & { results: Recipe[] };
}

// --- Endpoints Feedbacks ---

// FIX Phase 1 mature (review 2026-04-12) — Mismatch B : enum feedback_type aligné sur le backend
// Backend schéma Pydantic FeedbackCreate attend : "cooked" | "skipped" | "favorited"
// Mapping UI → backend :
//   (Adoré)     → "cooked" avec rating 5
//   (Correct)   → "cooked" avec rating 3
//   (Pas terrible) → "skipped" avec rating 1
export type BackendFeedbackType = "cooked" | "skipped" | "favorited";

export interface FeedbackCreate {
  recipe_id: string;
  rating: 1 | 2 | 3 | 4 | 5;
  feedback_type: BackendFeedbackType;
  notes?: string | null;
}

export interface FeedbackResponse {
  id: string;
  recipe_id: string;
  rating: number;
  feedback_type: BackendFeedbackType;
  notes: string | null;
  created_at: string;
}

export async function createFeedback(data: FeedbackCreate): Promise<FeedbackResponse> {
  return apiClient.post<FeedbackResponse>("/api/v1/feedbacks", data);
}

// ============================================================
// PHASE 2 — Billing Stripe
// ============================================================

export async function getBillingStatus(): Promise<BillingStatus> {
  return apiClient.get<BillingStatus>("/api/v1/billing/status");
}

export async function createCheckout(plan: string): Promise<CheckoutResponse> {
  return apiClient.post<CheckoutResponse>("/api/v1/billing/checkout", { plan });
}

export async function createPortal(): Promise<PortalResponse> {
  return apiClient.post<PortalResponse>("/api/v1/billing/portal", {});
}

// ============================================================
// Catalogue ingrédients — recherche fuzzy
// ============================================================

export interface IngredientSearchResult {
  id: string;
  name: string;
  category: string | null;
  unit_default: string | null;
}

export async function searchIngredients(q: string, limit = 10): Promise<IngredientSearchResult[]> {
  if (q.trim().length < 2) return [];
  return apiClient.get<IngredientSearchResult[]>(
    `/api/v1/ingredients/search?q=${encodeURIComponent(q.trim())}&limit=${limit}`
  );
}

// ============================================================
// PHASE 2 — Mode Frigo
// ============================================================

export async function getFridge(): Promise<FridgeItem[]> {
  return apiClient.get<FridgeItem[]>("/api/v1/fridge");
}

export async function addFridgeItem(data: FridgeItemCreate): Promise<FridgeItem> {
  return apiClient.post<FridgeItem>("/api/v1/fridge", data);
}

export async function removeFridgeItem(id: string): Promise<void> {
  return apiClient.delete<void>(`/api/v1/fridge/${id}`);
}

export async function getFridgeSuggestions(): Promise<FridgeSuggestionsResponse> {
  return apiClient.post<FridgeSuggestionsResponse>("/api/v1/fridge/suggest-recipes", {});
}

// ============================================================
// PHASE 2 — Livres PDF
// ============================================================

export async function getPlansHistory(): Promise<BookInfo[]> {
  return apiClient.get<BookInfo[]>("/api/v1/plans/me/history");
}

export async function getBookUrl(planId: string): Promise<BookInfo> {
  return apiClient.get<BookInfo>(`/api/v1/plans/${planId}/book`);
}

export async function generateBook(planId: string): Promise<BookGenerateResponse> {
  return apiClient.post<BookGenerateResponse>(`/api/v1/plans/${planId}/book/generate`, {});
}
