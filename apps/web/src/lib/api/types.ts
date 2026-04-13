// apps/web/src/lib/api/types.ts
// Types pour les réponses de l'API FastAPI
// Phase 1 — complet avec tous les types pour Household, Member, Recipe, Plan, ShoppingList, Feedback
// Phase 2 (2026-04-12) : BillingStatus, FridgeItem, BookInfo, RecipeFilters
// FIX Phase 1 mature (review 2026-04-12) : alignement contrats — budget_pref FR, feedback_type backend

// --- Recette ---

export interface Recipe {
  id: string;
  title: string;
  description: string;
  image_url: string | null;
  prep_time_minutes: number;
  cook_time_minutes: number;
  total_time_minutes: number;
  servings: number;
  difficulty: "easy" | "medium" | "hard";
  cuisine: string; // Ex: "Français", "Italien", "Japonais"
  dietary_tags: DietaryTag[];
  ingredients: Ingredient[];
  instructions: Instruction[];
  nutrition: NutritionInfo | null;
  rating_average: number | null; // 1.0 - 5.0
  rating_count: number;
  source_url: string | null;
  created_at: string; // ISO date
  updated_at: string; // ISO date
}

// Ingrédient normalisé
export interface Ingredient {
  id: string;
  name: string;
  quantity: number;
  unit: string; // "g", "kg", "L", "ml", "pièce", "cuillère à soupe"...
  note: string | null; // Ex: "finement haché"
  category: IngredientCategory;
  open_food_facts_id: string | null; // Pour le mapping drive (Phase 3)
}

// Instruction de préparation
export interface Instruction {
  step_number: number;
  description: string;
  duration_seconds: number | null;
  image_url: string | null;
}

// Informations nutritionnelles
export interface NutritionInfo {
  calories: number;
  proteins_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
}

// --- Plan hebdomadaire ---

export interface WeeklyPlan {
  id: string;
  household_id: string;
  week_start_date: string; // ISO date — lundi
  days: DayPlan[];
  status: "draft" | "confirmed" | "completed";
  shopping_list: ShoppingListItem[];
  created_at: string;
}

// Plan pour un jour de la semaine
export interface DayPlan {
  date: string; // ISO date
  day_of_week: "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";
  recipe: Recipe | null; // Null si pas de repas planifié ce jour
  servings_override: number | null;
}

// --- Liste de courses ---

export interface ShoppingListItem {
  id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  category: IngredientCategory;
  is_checked: boolean;
  is_in_stock: boolean; // Marqué "déjà en stock"
  recipe_ids: string[]; // Quelles recettes nécessitent cet ingrédient
  estimated_price: number | null; // En euros — Phase 3
  open_food_facts_id: string | null; // Pour le mapping drive (Phase 3)
}

// --- Household ---

export interface Household {
  id: string;
  owner_id: string;
  name: string;
  drive_provider: DriveProvider | null;
  cooking_time_preference: "under-20" | "20-40" | "over-40";
  members: HouseholdMember[];
  created_at: string;
  updated_at: string;
}

// Membre du foyer
export interface HouseholdMember {
  id: string;
  name: string;
  display_name: string;
  is_child: boolean;
  birth_date: string | null;
  age_range: "adult" | "under-3" | "3-6" | "7-12" | "13-plus" | null;
  dietary_restrictions: DietaryTag[];
  diet_tags: string[];
  allergies: string[];
  dislikes: string[];
  created_at: string;
}

// --- Feedback (notation recette) ---

// FIX Phase 1 mature (review 2026-04-12) — Mismatch B : enum aligné sur le backend
// Backend schéma Pydantic : "cooked" | "skipped" | "favorited"
export interface RecipeFeedback {
  id: string;
  recipe_id: string;
  household_member_id: string | null;
  rating: 1 | 2 | 3 | 4 | 5;
  feedback_type: "cooked" | "skipped" | "favorited";
  notes: string | null;
  created_at: string;
}

// --- Types paginés ---

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

// --- Erreur API standardisée (format FastAPI) ---

export interface ApiError {
  status_code: number;
  detail: string;
  correlation_id: string;
}

// ============================================================
// PHASE 2 — Billing, Frigo, Livres PDF, Filtres recettes
// ============================================================

// --- Billing / Stripe ---

export type BillingPlan = "starter" | "famille" | "coach";
export type BillingStatus_Status = "active" | "trialing" | "past_due" | "canceled" | "unpaid";

export interface BillingStatus {
  plan: BillingPlan;
  status: BillingStatus_Status;
  current_period_end: string | null; // ISO date — prochaine facture
  cancel_at_period_end: boolean;
  stripe_customer_id: string | null;
}

export interface CheckoutResponse {
  checkout_url: string; // URL Stripe Checkout (redirect)
}

export interface PortalResponse {
  portal_url: string; // URL Stripe Customer Portal (redirect)
}

// --- Frigo (Mode frigo) ---

export type FridgeItemUnit =
  | "g"
  | "kg"
  | "ml"
  | "L"
  | "pièce"
  | "tranche"
  | "botte"
  | "sachet"
  | "boîte"
  | "pot"
  | "autre";

export interface FridgeItem {
  id: string;
  household_id: string;
  ingredient_name: string;
  quantity: number;
  unit: FridgeItemUnit;
  expiry_date: string | null; // ISO date YYYY-MM-DD
  created_at: string;
  updated_at: string;
}

export interface FridgeItemCreate {
  ingredient_name: string;
  quantity: number;
  unit: FridgeItemUnit;
  expiry_date?: string | null; // ISO date YYYY-MM-DD
}

export interface FridgeSuggestionsResponse {
  recipes: Recipe[];
  matched_ingredients: string[]; // Ingrédients du frigo utilisés
}

// --- Livres PDF hebdomadaires ---

export type BookStatus = "available" | "generating" | "error" | "not_generated";

export interface BookInfo {
  id: string;
  plan_id: string;
  week_start_date: string; // ISO date lundi
  generated_at: string | null; // ISO datetime
  status: BookStatus;
  pdf_url: string | null; // URL MinIO/R2 directe
  page_count: number | null;
}

export interface BookGenerateResponse {
  task_id: string;
  status: "queued" | "already_available";
  book_id: string | null;
}

// --- Filtres recettes avancés ---

export interface RecipeFilters {
  q?: string;
  cuisine?: string;
  max_time?: number; // minutes — slider 15-120
  difficulty?: 1 | 2 | 3 | 4 | 5;
  diet?: DietaryTag | DietaryTag[];
  budget?: "économique" | "moyen" | "premium";
  page?: number;
  per_page?: number;
}

// --- Types utilitaires ---

export type DietaryTag =
  | "vegetarian"
  | "vegan"
  | "gluten-free"
  | "gluten_free"
  | "lactose-free"
  | "lactose_free"
  | "no-pork"
  | "no_pork"
  | "no-seafood"
  | "no_seafood"
  | "nut-free"
  | "nut_free"
  | "halal";

export type IngredientCategory =
  | "vegetables"
  | "fruits"
  | "meat"
  | "fish"
  | "dairy"
  | "grains"
  | "legumes"
  | "condiments"
  | "herbs"
  | "other";

export type DriveProvider =
  | "leclerc"
  | "auchan"
  | "carrefour"
  | "intermarche"
  | "other"
  | "none";
