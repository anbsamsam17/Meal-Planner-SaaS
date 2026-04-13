"""
models/__init__.py — Ré-export des modèles SQLAlchemy depuis apps/api.

FIX #1 (review Phase 1 2026-04-12) : ce module expose les modèles ORM
via mealplanner_db.models.* pour le worker, sans déplacer les fichiers
(propriété database-administrator).

IMPORTANT : ce module ne définit PAS de nouveaux modèles — il ré-exporte
uniquement les modèles définis dans apps/api/src/db/models/.

NOTA pour les développeurs :
- Les modèles canoniques sont dans apps/api/src/db/models/
- Toute modification de modèle doit être faite là-bas (et générer une migration Alembic)
- Ce ré-export se met à jour automatiquement si le sys.path est correctement configuré

NOTA devops-engineer :
- Pour que ces imports fonctionnent, apps/api/src doit être dans PYTHONPATH
  ou apps/api doit être installé comme package via uv workspace.
- Recommandation : mealplanner-api = { workspace = true } dans mealplanner-db dependencies
  OU configurer PYTHONPATH dans le Dockerfile worker pour inclure apps/api/src.
"""

# Ré-export des modèles Recipe
from src.db.models.recipe import (  # type: ignore[import]
    Ingredient,
    Recipe,
    RecipeEmbedding,
    RecipeIngredient,
)

# Ré-export des modèles Household (tenant)
from src.db.models.household import (  # type: ignore[import]
    Household,
    HouseholdMember,
    MemberPreference,
)

# Ré-export des modèles Planning
from src.db.models.planning import (  # type: ignore[import]
    FridgeItem,
    PlannedMeal,
    ShoppingList,
    WeeklyBook,
    WeeklyPlan,
)

# Ré-export des modèles Feedback
from src.db.models.feedback import (  # type: ignore[import]
    MemberTasteVector,
    RecipeFeedback,
)

# Ré-export des modèles Phase 2 — Stripe + RETENTION_LOOP
from src.db.models.subscription import (  # type: ignore[import]
    EngagementEvent,
    Subscription,
)

__all__ = [
    # Recipe
    "Ingredient",
    "Recipe",
    "RecipeEmbedding",
    "RecipeIngredient",
    # Household
    "Household",
    "HouseholdMember",
    "MemberPreference",
    "MemberTasteVector",
    # Planning
    "FridgeItem",
    "PlannedMeal",
    "ShoppingList",
    "WeeklyBook",
    "WeeklyPlan",
    # Feedback
    "RecipeFeedback",
    # Phase 2 — Stripe + Rétention
    "Subscription",
    "EngagementEvent",
]
