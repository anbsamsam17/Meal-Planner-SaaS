"""models/__init__.py — Import et réexport de tous les modèles ORM.

Ce fichier doit importer TOUS les modèles pour qu'Alembic puisse les découvrir
lors de l'autogenerate (alembic revision --autogenerate).
Sans ces imports, Alembic ne voit pas les tables et génère une migration DROP ALL.

Ordre d'import respecte les dépendances inter-modèles (FK) :
1. Household (pas de dépendances)
2. Recipe (pas de dépendances tenant)
3. Planning (dépend de Household et Recipe)
4. Feedback (dépend de Household, Recipe, Planning)
5. Subscription (dépend de Household) — Phase 2
"""

# MemberTasteVector est importé uniquement depuis feedback.py (qui le ré-exporte depuis household.py).
# Importer depuis les deux modules causerait un double import F811 et une confusion mypy.
from src.db.models.feedback import MemberTasteVector, RecipeFeedback
from src.db.models.household import Household, HouseholdMember, MemberPreference
from src.db.models.planning import FridgeItem, PlannedMeal, ShoppingList, WeeklyBook, WeeklyPlan
from src.db.models.recipe import Ingredient, Recipe, RecipeEmbedding, RecipeIngredient
# Phase 2 : abonnements Stripe et événements d'engagement
from src.db.models.subscription import EngagementEvent, Subscription

__all__ = [
    # Planning
    "FridgeItem",
    # Household
    "Household",
    "HouseholdMember",
    # Recipe
    "Ingredient",
    "MemberPreference",
    "MemberTasteVector",
    "PlannedMeal",
    "Recipe",
    "RecipeEmbedding",
    # Feedback
    "RecipeFeedback",
    "RecipeIngredient",
    "ShoppingList",
    "WeeklyBook",
    "WeeklyPlan",
    # Phase 2 — Stripe + Rétention
    "Subscription",
    "EngagementEvent",
]
