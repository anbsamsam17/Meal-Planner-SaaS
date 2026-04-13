"""
Schémas Pydantic pour le domaine Planning (plans hebdomadaires).

Aligné avec les modèles ORM :
- apps/api/src/db/models/planning.py
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---- Resume recette (pour le champ recipes[] de WeeklyPlanDetail) ----

class RecipeSummary(BaseModel):
    """
    Resume d'une recette incluse dans un plan hebdomadaire.

    FIX BLOQUANT 5 (audit 2026-04-13) : le frontend attend un tableau recipes[]
    dans la reponse WeeklyPlanDetail pour construire les RecipeCards via
    recipesById.get(meal.recipe_id). Ce schema fournit les champs necessaires
    sans dupliquer le RecipeOut complet (pas de slug, source, servings, etc.).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str | None = None
    photo_url: str | None = None
    total_time_min: int | None = None
    difficulty: int | None = None
    cuisine_type: str | None = None
    tags: list[str] = []
    quality_score: float | None = None


# ---- Repas planifié ----

class PlannedMealRead(BaseModel):
    """Repas individuel dans un plan hebdomadaire."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    day_of_week: int = Field(ge=1, le=7, description="1=lundi, ..., 7=dimanche.")
    slot: str = Field(description="Créneau du repas ('dinner', 'lunch').")
    recipe_id: UUID
    servings_adjusted: int
    # Données dénormalisées pour l'affichage (jointure recette)
    recipe_title: str | None = None
    recipe_cuisine_type: str | None = None
    recipe_total_time_min: int | None = None
    recipe_difficulty: int | None = None
    recipe_photo_url: str | None = None


# ---- Item liste de courses ----

class ShoppingListItemRead(BaseModel):
    """Ingrédient dans la liste de courses consolidée."""

    ingredient_id: str
    canonical_name: str
    category: str | None
    rayon: str = Field(description="Rayon supermarché (fruits_legumes, viandes_poissons, etc.).")
    off_id: str | None = Field(description="Identifiant Open Food Facts.")
    quantities: list[dict] = Field(description="Quantités par unité [{quantity_display, quantity_value, unit}].")
    checked: bool = Field(default=False, description="Élément coché dans la liste partagée.")
    in_fridge: bool = Field(default=False, description="Déjà en stock dans le frigo.")


# ---- Plan hebdomadaire ----

class WeeklyPlanRead(BaseModel):
    """Plan hebdomadaire sans les détails des repas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    week_start: date
    status: str = Field(description="Statut : 'draft', 'validated', 'archived'.")
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WeeklyPlanDetail(BaseModel):
    """
    Plan hebdomadaire complet avec repas, recettes et liste de courses.

    FIX BLOQUANT 5 (audit 2026-04-13) : ajout du champ recipes[] pour le frontend.
    Le frontend indexe les recettes par ID (recipesById) pour afficher les RecipeCards.
    Les champs denormalises dans PlannedMealRead (recipe_title, etc.) sont conserves
    pour la retrocompatibilite.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    week_start: date
    status: str
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    meals: list[PlannedMealRead] = []
    recipes: list[RecipeSummary] = []
    shopping_list: list[ShoppingListItemRead] = []


class GeneratePlanRequest(BaseModel):
    """
    Requête de génération d'un plan hebdomadaire.

    Phase 2 : ajout des filtres avancés budget_max et include_fridge.
    """

    week_start: date = Field(
        description="Lundi de la semaine cible (format YYYY-MM-DD).",
    )
    num_dinners: int = Field(
        default=5,
        ge=3,
        le=7,
        description="Nombre de dîners à planifier (3-7).",
    )

    # ---- Filtres Phase 2 ----
    budget_max: str | None = Field(
        default=None,
        description=(
            "Budget maximum hebdomadaire : 'économique', 'moyen', 'premium'. "
            "Filtre les recettes selon le tag budget. "
            "None = pas de filtre."
        ),
    )
    include_fridge: bool = Field(
        default=False,
        description=(
            "Si True, active le mode frigo : booste les recettes qui utilisent "
            "les ingrédients disponibles dans le stock du foyer "
            "(voir fridge_items). Priorité aux items proches de l'expiration."
        ),
    )

    def model_post_init(self, __context: object) -> None:
        """Validation : week_start doit être un lundi."""
        if self.week_start.isoweekday() != 1:
            raise ValueError(
                f"week_start doit être un lundi. Reçu : {self.week_start} "
                f"(jour de semaine : {self.week_start.isoweekday()})."
            )


class SwapMealRequest(BaseModel):
    """Requête de remplacement d'un repas dans un plan draft."""

    new_recipe_id: UUID = Field(description="UUID de la recette de remplacement.")


class ValidatePlanRequest(BaseModel):
    """Requête de validation d'un plan (passage draft → validated)."""

    confirm: bool = Field(
        default=True,
        description="Confirmation explicite de la validation.",
    )
