"""
mealplanner_db — Package partagé SQLAlchemy/session pour MealPlanner SaaS.

FIX #1 (review Phase 1 2026-04-12) : ce package résout le BUG CRITICAL "Worker ne peut pas
accéder aux modèles DB". Stratégie choisie : package de ré-export léger.

Décision architecturale (vs alternative "copie dans apps/worker") :
- POUR le package partagé : source de vérité unique, pas de maintenance en double,
  cohérence garantie entre l'API et le worker, chemin de migration propre.
- CONTRE la copie : divergence silencieuse entre les deux copies, maintenance double,
  risque de bugs difficiles à détecter lors d'une migration de schéma.
- DÉCISION : package partagé mealplanner-db (ce fichier).

Les modèles SQLAlchemy restent dans apps/api/src/db/models/ (propriété DBA).
Ce package expose les mêmes objets via mealplanner_db.* pour permettre au worker
d'accéder aux modèles sans créer de dépendance directe vers apps/api.

Usage dans apps/worker :
    from mealplanner_db import AsyncSessionLocal, engine
    from mealplanner_db.models import Recipe, RecipeEmbedding, RecipeIngredient

NOTA devops-engineer :
- Ajouter "packages/db" dans [tool.uv.workspace] members du pyproject.toml racine.
- Ajouter mealplanner-db = { workspace = true } dans les dépendances de apps/api et apps/worker.
"""

from mealplanner_db.session import AsyncSessionLocal, close_engine, engine, get_db
from mealplanner_db.base import Base

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "close_engine",
    "engine",
    "get_db",
]
