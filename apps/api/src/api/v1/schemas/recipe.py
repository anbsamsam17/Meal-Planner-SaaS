"""
Schémas Pydantic pour le domaine Recettes.

Aligné avec les modèles ORM :
- apps/api/src/db/models/recipe.py

Schémas distincts pour :
- RecipeOut : liste et résumé (sans ingrédients)
- RecipeDetail : détail complet (avec ingrédients et instructions)
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngredientOut(BaseModel):
    """Ingrédient dans une liste de recette."""

    id: UUID
    canonical_name: str
    category: str | None
    off_id: str | None

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientOut(BaseModel):
    """Ingrédient avec sa quantité dans le contexte d'une recette."""

    ingredient_id: UUID
    canonical_name: str
    quantity: float | None
    unit: str | None
    notes: str | None
    position: int

    model_config = ConfigDict(from_attributes=True)


class RecipeOut(BaseModel):
    """Représentation publique d'une recette (sans ingrédients détaillés)."""

    id: UUID
    title: str
    slug: str
    source: str | None = None
    servings: int | None = None
    prep_time_min: int | None = None
    cook_time_min: int | None = None
    total_time_min: int | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    cuisine_type: str | None = None
    photo_url: str | None = None
    tags: list[str] = []
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


class RecipeDetail(RecipeOut):
    """Détail complet d'une recette avec ingrédients et instructions."""

    description: str | None = None
    instructions: list[dict] = Field(
        default=[],
        description="Étapes de préparation [{'step': 1, 'text': '...'}].",
    )
    ingredients: list[RecipeIngredientOut] = Field(
        default=[],
        description="Ingrédients avec quantités.",
    )

    model_config = ConfigDict(from_attributes=True)


class RecipeSearchResult(BaseModel):
    """Résultat paginé de la recherche de recettes."""

    results: list[RecipeOut]
    total: int
    query: str
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
