// apps/web/src/lib/api/endpoints.ts
// Fonctions typées pour chaque endpoint API — couche d'abstraction sur apiClient
// Alignées sur les contrats backend Phase 1 + Phase 2 (backend-developer en parallèle)
// Toutes les requêtes nécessitent un JWT Supabase (sauf /health)
// FIX Phase 1 mature (review 2026-04-12) : alignement contrats frontend↔backend (5 mismatches)
// Phase 2 (2026-04-12) : billing, frigo, livres PDF, filtres avancés

import { apiClient } from "./client";
import type {
  Recipe,
  WeeklyPlan,
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

export interface PlannedMeal {
  id: string;
  day_of_week: string;
  meal_type: "breakfast" | "lunch" | "dinner";
  recipe_id: string;
  servings: number;
  recipe?: Recipe;
}

export interface PlanDetail {
  plan: WeeklyPlan;
  // FIX Phase 1 mature (review 2026-04-12) — Mismatch D : backend retourne `meals`, pas `planned_meals`
  // Schéma Pydantic PlanDetail — champ : meals
  meals: PlannedMeal[];
  recipes: Recipe[];
}

export interface GeneratePlanResponse {
  task_id: string;
}

// FIX Phase 1 mature (review 2026-04-12) — Mismatch E : body generatePlan avec week_start obligatoire
export interface GeneratePlanBody {
  week_start: string; // ISO date du lundi de la semaine cible, ex: "2026-04-13"
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
export async function generatePlan(): Promise<GeneratePlanResponse> {
  const body: GeneratePlanBody = { week_start: getNextMonday() };
  return apiClient.post<GeneratePlanResponse>("/api/v1/plans/generate", body);
}

export async function getPlan(id: string): Promise<PlanDetail> {
  return apiClient.get<PlanDetail>(`/api/v1/plans/${id}`);
}

export async function getCurrentPlan(): Promise<PlanDetail> {
  return apiClient.get<PlanDetail>("/api/v1/plans/me/current");
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
    recipe_id: recipeId,
  });
}

export async function getShoppingList(planId: string): Promise<ShoppingListItem[]> {
  return apiClient.get<ShoppingListItem[]>(`/api/v1/plans/me/${planId}/shopping-list`);
}

// --- Endpoints Recipes ---

export async function getRecipe(id: string): Promise<Recipe> {
  return apiClient.get<Recipe>(`/api/v1/recipes/${id}`);
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
export async function searchRecipesAdvanced(
  filters: RecipeFilters,
): Promise<PaginatedResponse<Recipe>> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.cuisine) params.set("cuisine", filters.cuisine);
  if (filters.max_time) params.set("max_time", String(filters.max_time));
  if (filters.difficulty) params.set("difficulty", String(filters.difficulty));
  if (filters.budget) params.set("budget", filters.budget);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  // diet peut être un tableau
  if (filters.diet) {
    const diets = Array.isArray(filters.diet) ? filters.diet : [filters.diet];
    diets.forEach((d) => params.append("diet", d));
  }

  const qs = params.toString();
  return apiClient.get<PaginatedResponse<Recipe>>(`/api/v1/recipes${qs ? `?${qs}` : ""}`);
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
