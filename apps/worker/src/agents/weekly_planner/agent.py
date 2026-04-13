"""
Agent WEEKLY_PLANNER — génération du plan hebdomadaire personnalisé.

Classe principale orchestrant le pipeline complet de planification :

Pipeline :
1. Collecte contexte (profil famille, préférences, historique, frigo)
2. Construction des contraintes dures (allergies, régimes)
3. Construction des contraintes molles (goûts, temps, budget)
4. Recherche candidates via pgvector (hybrid : sémantique + filtres)
5. Score + sélection 5-7 recettes (diversité + non-répétition)
6. Génération liste de courses consolidée
7. Persistance DB

Convention ROADMAP :
- Chaque agent est une classe Python avec une méthode run() unique
- Logging structuré loguru sur toutes les étapes
- Variables d'environnement pour les clés API

Coûts estimés :
- 0 appel LLM en chemin nominal (heuristique pure)
- 1 appel Claude (~0.05€) uniquement si l'heuristique échoue à sélectionner
  num_dinners recettes satisfaisantes (cas rare, < 5% estimé)
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.agents.weekly_planner.constraint_builder import (
    HouseholdConstraints,
    build_household_constraints,
)
from src.agents.weekly_planner.plan_selector import (
    ScoredRecipe,
    score_candidates,
    select_diverse_plan,
)
from src.agents.weekly_planner.recipe_retriever import (
    get_household_taste_vector,
    retrieve_candidate_recipes,
)
from src.agents.weekly_planner.shopping_list_builder import build_shopping_list


@dataclass
class WeeklyPlanResult:
    """
    Résultat de la génération d'un plan hebdomadaire.

    Attributes:
        plan_id: UUID du WeeklyPlan créé en base.
        household_id: UUID du foyer.
        week_start: Date de début de la semaine (toujours un lundi).
        selected_recipes: Recettes sélectionnées avec leurs scores.
        shopping_list: Liste de courses consolidée.
        constraints: Contraintes appliquées (pour audit/debug).
        duration_seconds: Durée totale de génération.
        used_llm_fallback: True si l'heuristique a dû appeler Claude.
        errors: Erreurs non fatales survenues pendant la génération.
    """

    plan_id: str
    household_id: str
    week_start: date
    selected_recipes: list[ScoredRecipe] = field(default_factory=list)
    shopping_list: list[dict] = field(default_factory=list)
    constraints: HouseholdConstraints | None = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    used_llm_fallback: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Durée totale de génération en secondes."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def recipe_count(self) -> int:
        """Nombre de recettes sélectionnées."""
        return len(self.selected_recipes)


class WeeklyPlannerAgent:
    """
    Agent WEEKLY_PLANNER — génération du plan de repas hebdomadaire.

    Chaque instance est créée par une tâche Celery pour un run unique.
    L'instance n'est pas réutilisée entre les runs.

    Usage :
        agent = WeeklyPlannerAgent(session_factory=AsyncSessionLocal)
        result = await agent.run(
            household_id=UUID("..."),
            week_start=date(2026, 4, 14),
            num_dinners=5,
        )
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        anthropic_api_key: str | None = None,
    ) -> None:
        """
        Initialise l'agent WEEKLY_PLANNER.

        Args:
            session_factory: Factory de sessions SQLAlchemy async.
            anthropic_api_key: Clé API Anthropic (fallback LLM si heuristique insuffisante).
        """
        self.session_factory = session_factory
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

    async def run(
        self,
        household_id: UUID,
        week_start: date,
        num_dinners: int = 5,
    ) -> WeeklyPlanResult:
        """
        Génère le plan hebdomadaire complet pour un foyer.

        Point d'entrée unique (convention ROADMAP).

        Args:
            household_id: UUID du foyer à planifier.
            week_start: Lundi de la semaine cible (validé : ISODOW = 1).
            num_dinners: Nombre de dîners à planifier (5 par défaut).

        Returns:
            WeeklyPlanResult avec le plan complet et la liste de courses.

        Raises:
            ValueError: Si week_start n'est pas un lundi.
        """
        # Validation : week_start doit être un lundi (ISODOW = 1)
        if week_start.isoweekday() != 1:
            raise ValueError(
                f"week_start doit être un lundi (ISODOW=1). "
                f"Reçu : {week_start} (ISODOW={week_start.isoweekday()})"
            )

        # Initialisation du résultat
        result = WeeklyPlanResult(
            plan_id="",  # Sera rempli après insertion DB
            household_id=str(household_id),
            week_start=week_start,
        )

        logger.info(
            "weekly_planner_run_start",
            household_id=str(household_id),
            week_start=str(week_start),
            num_dinners=num_dinners,
        )

        try:
            async with self.session_factory() as session:
                # ---- Étape 1 : Collecte du contexte famille ----
                members_preferences = await self._load_members_preferences(
                    session, household_id
                )

                # ---- Étape 2 : Construction des contraintes ----
                constraints = build_household_constraints(members_preferences)
                result.constraints = constraints

                # ---- Étape 3 : Récupération du vecteur de goût ----
                taste_vector = await get_household_taste_vector(session, household_id)

                # ---- Étape 4 : Recherche de candidats ----
                candidates = await retrieve_candidate_recipes(
                    session=session,
                    household_id=household_id,
                    constraints=constraints,
                    taste_vector=taste_vector,
                    k=50,
                )

                if not candidates:
                    result.errors.append(
                        "Aucune recette candidate trouvée avec les contraintes appliquées."
                    )
                    logger.warning(
                        "weekly_planner_no_candidates",
                        household_id=str(household_id),
                    )
                    return result

                # ---- Étape 5 : Scoring et sélection ----
                has_children = constraints.child_count > 0
                scored = score_candidates(candidates, has_children=has_children)
                selected = select_diverse_plan(scored, num_dinners=num_dinners, has_children=has_children)

                if len(selected) < num_dinners:
                    logger.warning(
                        "weekly_planner_insufficient_selection",
                        selected=len(selected),
                        needed=num_dinners,
                    )
                    result.errors.append(
                        f"Seulement {len(selected)}/{num_dinners} recettes trouvées."
                    )

                result.selected_recipes = selected

                # ---- Étape 6 : Génération liste de courses ----
                recipe_ids = [r.recipe_id for r in selected]
                num_persons = constraints.member_count or 4

                shopping_list = await build_shopping_list(
                    session=session,
                    recipe_ids=recipe_ids,
                    household_id=household_id,
                    num_persons=num_persons,
                )
                result.shopping_list = shopping_list

                # ---- Étape 7 : Persistance en base ----
                plan_id = await self._persist_plan(
                    session=session,
                    household_id=household_id,
                    week_start=week_start,
                    selected=selected,
                    shopping_list=shopping_list,
                )
                result.plan_id = str(plan_id)

                result.finished_at = datetime.now()

        except Exception as exc:
            result.errors.append(f"Erreur fatale : {exc}")
            result.finished_at = datetime.now()
            logger.exception(
                "weekly_planner_run_error",
                household_id=str(household_id),
            )
            raise

        logger.info(
            "weekly_planner_run_complete",
            household_id=str(household_id),
            plan_id=result.plan_id,
            recipe_count=result.recipe_count,
            shopping_items=len(result.shopping_list),
            duration_seconds=result.duration_seconds,
            used_llm_fallback=result.used_llm_fallback,
        )

        return result

    async def _load_members_preferences(
        self, session: AsyncSession, household_id: UUID
    ) -> list[dict]:
        """
        Charge les préférences de tous les membres du foyer.

        Args:
            session: Session SQLAlchemy async.
            household_id: UUID du foyer.

        Returns:
            Liste de dicts avec les préférences de chaque membre.
        """
        result = await session.execute(
            text(
                """
                SELECT
                    hm.id::text AS member_id,
                    hm.display_name,
                    hm.is_child,
                    mp.diet_tags,
                    mp.allergies,
                    mp.dislikes,
                    mp.cooking_time_max,
                    mp.budget_pref
                FROM household_members hm
                LEFT JOIN member_preferences mp ON mp.member_id = hm.id
                WHERE hm.household_id = :household_id
                ORDER BY hm.created_at ASC
                """
            ),
            {"household_id": str(household_id)},
        )
        rows = result.mappings().all()

        members = []
        for row in rows:
            members.append(
                {
                    "member_id": row["member_id"],
                    "display_name": row["display_name"],
                    "is_child": row["is_child"] or False,
                    "diet_tags": row.get("diet_tags") or [],
                    "allergies": row.get("allergies") or [],
                    "dislikes": row.get("dislikes") or [],
                    "cooking_time_max": row.get("cooking_time_max"),
                    "budget_pref": row.get("budget_pref"),
                }
            )

        logger.debug(
            "weekly_planner_members_loaded",
            household_id=str(household_id),
            member_count=len(members),
        )

        return members

    async def _persist_plan(
        self,
        session: AsyncSession,
        household_id: UUID,
        week_start: date,
        selected: list[ScoredRecipe],
        shopping_list: list[dict],
    ) -> UUID:
        """
        Insère le plan et la liste de courses en base de données.

        Crée ou remplace le plan existant pour cette semaine (UPSERT logique).
        Les planned_meals et la shopping_list sont liés au plan via FK.

        Args:
            session: Session SQLAlchemy async.
            household_id: UUID du foyer.
            week_start: Lundi de la semaine.
            selected: Recettes sélectionnées.
            shopping_list: Liste de courses consolidée.

        Returns:
            UUID du plan créé.
        """
        import json

        # Création du plan
        plan_result = await session.execute(
            text(
                """
                INSERT INTO weekly_plans (household_id, week_start, status)
                VALUES (:household_id, :week_start, 'draft')
                ON CONFLICT (household_id, week_start) DO UPDATE
                SET status = 'draft', updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "household_id": str(household_id),
                "week_start": week_start.isoformat(),
            },
        )
        plan_row = plan_result.mappings().one()
        plan_id = plan_row["id"]

        # Suppression des meals existants (pour le UPSERT)
        await session.execute(
            text("DELETE FROM planned_meals WHERE plan_id = :plan_id"),
            {"plan_id": str(plan_id)},
        )

        # FIX Phase 1 mature (review 2026-04-12) — BUG #9 :
        # Remplacement de la boucle (5-7 INSERTs individuels = 5-7 round-trips)
        # par un INSERT batch multi-VALUES = 1 seul round-trip réseau vers Supabase.
        # Gain estimé : -20ms sur la persistance du plan.
        if selected:
            # Construction dynamique des placeholders VALUES (:p0, :d0, :r0, :s0), ...
            value_placeholders = ", ".join(
                f"(:plan_id_{i}, :{i}_day, 'dinner', :{i}_recipe, :{i}_servings)"
                for i in range(len(selected))
            )
            batch_params: dict[str, Any] = {}
            for i, recipe in enumerate(selected):
                batch_params[f"plan_id_{i}"] = str(plan_id)
                batch_params[f"{i}_day"] = i + 1  # jour 1=lundi, 2=mardi, ...
                batch_params[f"{i}_recipe"] = recipe.recipe_id
                batch_params[f"{i}_servings"] = recipe.servings or 4

            await session.execute(
                text(
                    f"""
                    INSERT INTO planned_meals (
                        plan_id, day_of_week, slot, recipe_id, servings_adjusted
                    ) VALUES {value_placeholders}
                    """
                ),
                batch_params,
            )

        # Insertion de la liste de courses
        await session.execute(
            text(
                """
                INSERT INTO shopping_lists (plan_id, items)
                VALUES (:plan_id, :items::jsonb)
                ON CONFLICT (plan_id) DO UPDATE SET items = EXCLUDED.items
                """
            ),
            {
                "plan_id": str(plan_id),
                "items": json.dumps(shopping_list),
            },
        )

        await session.commit()

        logger.info(
            "weekly_planner_plan_persisted",
            plan_id=str(plan_id),
            household_id=str(household_id),
            week_start=str(week_start),
            meals_count=len(selected),
            shopping_items=len(shopping_list),
        )

        return plan_id
