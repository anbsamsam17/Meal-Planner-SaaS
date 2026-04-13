"""
BookGeneratorAgent — génération des livres de recettes hebdomadaires en PDF.

Pipeline complet :
1. Récupère plan + recettes + ingrédients depuis la DB
2. Compile les données (nutrition, temps, difficulté)
3. Rend le template Jinja2 → HTML
4. WeasyPrint convertit HTML → PDF bytes
5. Upload sur MinIO (dev) / R2 (prod)
6. Met à jour weekly_books (pdf_r2_key, content_hash)
7. Log l'événement de notification (RETENTION_LOOP Phase 2)

Idempotence : hash SHA-256 du contenu → skip si déjà généré avec le même hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger

from src.agents.book_generator.pdf_renderer import PdfRenderer
from src.agents.book_generator.storage import BookStorage
from src.agents.book_generator.template_engine import TemplateEngine


class BookGeneratorAgent:
    """
    Orchestrateur de la génération PDF des livres de recettes.

    Instancier une fois par worker Celery (singleton).
    Chaque appel à run() est idempotent : vérifie le content_hash avant de régénérer.
    """

    def __init__(self) -> None:
        self._template_engine = TemplateEngine()
        self._pdf_renderer = PdfRenderer()
        self._storage = BookStorage()

    async def run(self, plan_id: UUID, db_session: Any) -> dict[str, Any]:
        """
        Point d'entrée principal. Génère ou skippe le PDF selon l'idempotence.

        Args:
            plan_id: UUID du plan hebdomadaire validé.
            db_session: Session SQLAlchemy async (injectée par la tâche Celery).

        Returns:
            dict avec les clés : skipped, pdf_key, content_hash, duration_ms.
        """
        import time

        start_ts = time.monotonic()

        logger.info("book_generator_run_start", plan_id=str(plan_id))

        # --- Étape 1 : récupération des données du plan ---
        plan_data = await self._fetch_plan_data(db_session, plan_id)

        if plan_data is None:
            logger.error("book_generator_plan_not_found", plan_id=str(plan_id))
            raise ValueError(f"Plan {plan_id} introuvable ou non validé.")

        # --- Étape 2 : calcul du hash idempotent ---
        content_hash = _compute_plan_hash(plan_data)

        existing_hash = await self._get_existing_hash(db_session, plan_id)
        if existing_hash == content_hash:
            logger.info(
                "book_generator_skip_idempotent",
                plan_id=str(plan_id),
                hash=content_hash[:8],
            )
            return {"skipped": True, "content_hash": content_hash, "pdf_key": None, "duration_ms": 0}

        # --- Étape 3 : rendu Jinja2 → HTML ---
        html_content = self._template_engine.render(plan_data)

        # --- Étape 4 : WeasyPrint HTML → PDF bytes ---
        pdf_bytes = self._pdf_renderer.render(html_content)

        # --- Étape 5 : upload MinIO/R2 ---
        household_id = plan_data["household_id"]
        pdf_key = f"{household_id}/{plan_id}-{content_hash[:8]}.pdf"
        await self._storage.upload(pdf_key, pdf_bytes)

        # --- Étape 6 : mise à jour weekly_books ---
        await self._upsert_weekly_book(
            db_session, plan_id, str(household_id), pdf_key, content_hash
        )

        duration_ms = int((time.monotonic() - start_ts) * 1000)

        logger.info(
            "book_generator_run_complete",
            plan_id=str(plan_id),
            household_id=str(household_id),
            pdf_key=pdf_key,
            hash=content_hash[:8],
            duration_ms=duration_ms,
            pdf_size_bytes=len(pdf_bytes),
        )

        # --- Étape 7 : log notification (stub — implémenté dans RETENTION_LOOP) ---
        logger.info(
            "book_generator_notify_stub",
            plan_id=str(plan_id),
            household_id=str(household_id),
            event="pdf_ready",
            pdf_key=pdf_key,
        )

        return {
            "skipped": False,
            "pdf_key": pdf_key,
            "content_hash": content_hash,
            "duration_ms": duration_ms,
        }

    async def _fetch_plan_data(
        self, session: Any, plan_id: UUID
    ) -> dict[str, Any] | None:
        """
        Récupère le plan hebdomadaire avec toutes ses recettes et ingrédients.

        Joins :
        - weekly_plans → planned_meals → recipes → recipe_ingredients → ingredients

        Returns:
            dict structuré pour le template Jinja2, ou None si plan inexistant.
        """
        from sqlalchemy import text

        # Plan de base
        plan_result = await session.execute(
            text(
                """
                SELECT
                    wp.id, wp.household_id, wp.week_start, wp.status,
                    h.name AS household_name
                FROM weekly_plans wp
                JOIN households h ON h.id = wp.household_id
                WHERE wp.id = :plan_id
                  AND wp.status = 'validated'
                LIMIT 1
                """
            ),
            {"plan_id": str(plan_id)},
        )
        plan_row = plan_result.mappings().one_or_none()

        if plan_row is None:
            return None

        # Repas avec recettes complètes
        meals_result = await session.execute(
            text(
                """
                SELECT
                    pm.day_of_week,
                    pm.slot,
                    pm.servings_adjusted,
                    r.id AS recipe_id,
                    r.title,
                    r.cuisine_type,
                    r.prep_time_min,
                    r.cook_time_min,
                    r.total_time_min,
                    r.difficulty,
                    r.servings,
                    r.photo_url,
                    r.instructions,
                    r.tags,
                    r.quality_score
                FROM planned_meals pm
                JOIN recipes r ON r.id = pm.recipe_id
                WHERE pm.plan_id = :plan_id
                ORDER BY pm.day_of_week ASC, pm.slot ASC
                """
            ),
            {"plan_id": str(plan_id)},
        )
        meals_rows = meals_result.mappings().all()

        # Ingrédients pour toutes les recettes du plan
        recipe_ids = [str(row["recipe_id"]) for row in meals_rows]
        if recipe_ids:
            ing_result = await session.execute(
                text(
                    """
                    SELECT
                        ri.recipe_id::text,
                        i.canonical_name,
                        ri.quantity,
                        ri.unit,
                        ri.notes,
                        ri.position
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = ANY(:recipe_ids::uuid[])
                    ORDER BY ri.recipe_id, ri.position
                    """
                ),
                {"recipe_ids": recipe_ids},
            )
            ing_rows = ing_result.mappings().all()
        else:
            ing_rows = []

        # Indexation des ingrédients par recipe_id
        ingredients_by_recipe: dict[str, list[dict]] = {}
        for ing in ing_rows:
            rid = ing["recipe_id"]
            if rid not in ingredients_by_recipe:
                ingredients_by_recipe[rid] = []
            ingredients_by_recipe[rid].append(dict(ing))

        # Construction de la liste de courses consolidée
        shopping_list = _build_shopping_list(ing_rows)

        # Assemblage final
        recipes = []
        for meal in meals_rows:
            rid = str(meal["recipe_id"])
            recipes.append(
                {
                    "day_of_week": meal["day_of_week"],
                    "slot": meal["slot"],
                    "servings_adjusted": meal["servings_adjusted"],
                    "id": rid,
                    "title": meal["title"],
                    "cuisine_type": meal["cuisine_type"],
                    "prep_time_min": meal["prep_time_min"],
                    "cook_time_min": meal["cook_time_min"],
                    "total_time_min": meal["total_time_min"],
                    "difficulty": meal["difficulty"],
                    "servings": meal["servings"],
                    "photo_url": meal["photo_url"],
                    "instructions": meal["instructions"] or [],
                    "tags": meal["tags"] or [],
                    "ingredients": ingredients_by_recipe.get(rid, []),
                }
            )

        return {
            "plan_id": str(plan_id),
            "household_id": str(plan_row["household_id"]),
            "household_name": plan_row["household_name"],
            "week_start": str(plan_row["week_start"]),
            "generated_at": datetime.utcnow().isoformat(),
            "recipes": recipes,
            "shopping_list": shopping_list,
        }

    async def _get_existing_hash(
        self, session: Any, plan_id: UUID
    ) -> str | None:
        """Retourne le content_hash existant dans weekly_books, ou None."""
        from sqlalchemy import text

        result = await session.execute(
            text(
                "SELECT content_hash FROM weekly_books WHERE plan_id = :plan_id LIMIT 1"
            ),
            {"plan_id": str(plan_id)},
        )
        row = result.fetchone()
        return row[0] if row else None

    async def _upsert_weekly_book(
        self,
        session: Any,
        plan_id: UUID,
        household_id: str,
        pdf_key: str,
        content_hash: str,
    ) -> None:
        """
        Insère ou met à jour l'enregistrement weekly_books.

        Utilise INSERT ... ON CONFLICT pour l'idempotence.
        """
        from sqlalchemy import text

        await session.execute(
            text(
                """
                INSERT INTO weekly_books (plan_id, household_id, pdf_r2_key, content_hash, generated_at)
                VALUES (:plan_id, :household_id, :pdf_key, :content_hash, NOW())
                ON CONFLICT (plan_id)
                DO UPDATE SET
                    pdf_r2_key = EXCLUDED.pdf_r2_key,
                    content_hash = EXCLUDED.content_hash,
                    generated_at = EXCLUDED.generated_at,
                    updated_at = NOW()
                """
            ),
            {
                "plan_id": str(plan_id),
                "household_id": household_id,
                "pdf_key": pdf_key,
                "content_hash": content_hash,
            },
        )
        await session.commit()


def _compute_plan_hash(plan_data: dict[str, Any]) -> str:
    """
    Calcule un hash SHA-256 déterministe du contenu du plan.

    On exclut generated_at (timestamp) pour que le hash soit stable.
    Tout changement de recette ou d'ingrédient déclenche une re-génération.

    Args:
        plan_data: dict complet du plan (output de _fetch_plan_data).

    Returns:
        Chaîne hexadécimale SHA-256 de 64 caractères.
    """
    # Exclure les champs non-déterministes
    stable_data = {
        k: v for k, v in plan_data.items() if k not in ("generated_at",)
    }
    canonical = json.dumps(stable_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_shopping_list(ing_rows: list[Any]) -> list[dict[str, Any]]:
    """
    Consolide les ingrédients de toutes les recettes en une liste de courses.

    Agrège les quantités du même ingrédient (même canonical_name + même unit).
    Groupe par rayon (heuristique simplifiée sur le nom).

    Args:
        ing_rows: Rows ingrédients depuis la DB (mappings sqlalchemy).

    Returns:
        Liste d'items de courses consolidée, triée par rayon.
    """
    # Agrégation par (canonical_name, unit)
    consolidated: dict[tuple[str, str], dict[str, Any]] = {}

    for ing in ing_rows:
        canonical_name = ing["canonical_name"]
        unit = ing["unit"] or ""
        key = (canonical_name, unit)

        if key not in consolidated:
            consolidated[key] = {
                "ingredient": canonical_name,
                "quantity": 0.0,
                "unit": unit,
                "aisle": _guess_aisle(canonical_name),
            }

        qty = ing["quantity"]
        if qty is not None:
            consolidated[key]["quantity"] += float(qty)

    # Tri par rayon puis par ingrédient
    items = sorted(
        consolidated.values(),
        key=lambda x: (x["aisle"], x["ingredient"]),
    )
    return items


_AISLE_KEYWORDS: dict[str, list[str]] = {
    "Fruits et légumes": [
        "tomate", "oignon", "ail", "carotte", "courgette", "poivron",
        "pomme", "banane", "citron", "salade", "épinard", "poireau",
        "champignon", "betterave", "concombre", "avocat",
    ],
    "Viandes et poissons": [
        "poulet", "boeuf", "porc", "veau", "agneau", "saumon",
        "thon", "crevette", "moule", "sardine", "cabillaud",
    ],
    "Produits laitiers": [
        "lait", "crème", "beurre", "fromage", "yaourt", "oeuf",
        "parmesan", "gruyère", "mozzarella", "ricotta",
    ],
    "Épicerie sèche": [
        "farine", "sucre", "sel", "poivre", "huile", "vinaigre",
        "pâte", "riz", "lentille", "pois", "haricot", "semoule",
        "quinoa", "orge", "avoine",
    ],
    "Herbes et épices": [
        "basilic", "thym", "romarin", "cumin", "curry", "paprika",
        "cannelle", "curcuma", "persil", "coriandre", "origan",
    ],
    "Conserves et sauces": [
        "concentré", "tomate pelée", "sauce", "bouillon", "lentille en boîte",
        "haricot en boîte", "olive", "câpre",
    ],
}


def _guess_aisle(ingredient_name: str) -> str:
    """
    Heuristique de classification par rayon basée sur des mots-clés.

    Args:
        ingredient_name: Nom canonique de l'ingrédient.

    Returns:
        Nom du rayon (str).
    """
    lower = ingredient_name.lower()
    for aisle, keywords in _AISLE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return aisle
    return "Autres"
