"""
Script d'import des recettes de démonstration depuis sample_recipes.json.

Contourne le pipeline de scraping pour insérer directement 10 recettes
françaises de test en base de données via SQLAlchemy.

Utile pour :
- Développement local sans accès à Marmiton (sélecteurs CSS changés)
- Démos produit avec des données réalistes
- Tests d'intégration end-to-end (dashboard → recettes → planning)

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner \\
    uv run python -m src.scripts.import_sample_recipes

Variables d'environnement :
    DATABASE_URL    Obligatoire — connexion PostgreSQL async (asyncpg).
    DRY_RUN         Optionnel — "true" pour parser sans insérer (validation JSON).
    LOG_LEVEL       Optionnel — DEBUG/INFO/WARNING (défaut: INFO).
"""

import asyncio
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from loguru import logger


# Chemin vers le fichier JSON des recettes de démonstration
SAMPLE_RECIPES_PATH = Path(__file__).parent / "sample_recipes.json"


def _configure_logging() -> None:
    """Configure loguru pour la sortie console du script."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> — {message}"
        ),
    )


def _validate_env() -> None:
    """Vérifie que DATABASE_URL est définie avant de démarrer."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "DATABASE_URL manquante. "
            "Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner"
        )
        sys.exit(1)


def _load_sample_recipes() -> list[dict]:
    """Charge et valide les recettes depuis sample_recipes.json."""
    if not SAMPLE_RECIPES_PATH.exists():
        logger.error(f"Fichier non trouvé : {SAMPLE_RECIPES_PATH}")
        sys.exit(1)

    with open(SAMPLE_RECIPES_PATH, encoding="utf-8") as f:
        recipes = json.load(f)

    # Validation minimale des champs obligatoires
    required_fields = {"title", "ingredients", "instructions", "servings"}
    for i, recipe in enumerate(recipes):
        missing = required_fields - set(recipe.keys())
        if missing:
            logger.error(f"Recette #{i} manque les champs : {missing}")
            sys.exit(1)

    logger.info(f"sample_recipes_loaded", count=len(recipes), path=str(SAMPLE_RECIPES_PATH))
    return recipes


def _difficulty_to_int(difficulty: int | str | None) -> int:
    """
    Convertit la difficulté vers l'échelle 1-5.

    Accepte un entier (passthrough) ou une chaîne (très facile→1, très difficile→5).
    """
    if isinstance(difficulty, int):
        return max(1, min(5, difficulty))

    mapping = {
        "très facile": 1,
        "very_easy": 1,
        "facile": 2,
        "easy": 2,
        "moyen": 3,
        "medium": 3,
        "difficile": 4,
        "hard": 4,
        "très difficile": 5,
        "very_hard": 5,
    }
    if isinstance(difficulty, str):
        return mapping.get(difficulty.lower(), 3)
    return 3  # Valeur par défaut : moyen


async def _insert_recipe(session, recipe: dict, dry_run: bool) -> bool:
    """
    Insère une recette dans la base de données.

    Pipeline simplifié (sans scraping ni validation LLM) :
    1. Vérifier que la recette n'existe pas déjà (titre exact)
    2. Insérer dans la table recipes
    3. Créer les ingrédients canoniques (lookup ou création)
    4. Insérer les recipe_ingredients

    Args:
        session: Session SQLAlchemy async.
        recipe: Dict avec les données de la recette.
        dry_run: Si True, ne fait rien en base.

    Returns:
        True si insérée, False si ignorée (doublon).
    """
    from sqlalchemy import text

    title = recipe["title"]

    # Vérification doublon par titre exact
    result = await session.execute(
        text("SELECT id FROM recipes WHERE title = :title LIMIT 1"),
        {"title": title},
    )
    existing = result.fetchone()
    if existing:
        logger.debug(f"recipe_skipped_duplicate", title=title)
        return False

    if dry_run:
        logger.info(f"[DRY_RUN] Would insert: {title}")
        return True

    recipe_id = str(uuid4())
    prep_time = recipe.get("prep_time_min") or 0
    cook_time = recipe.get("cook_time_min") or 0
    total_time = prep_time + cook_time

    # Difficulté en entier 1-5
    difficulty = _difficulty_to_int(recipe.get("difficulty"))

    # Insertion dans la table recipes
    await session.execute(
        text(
            """
            INSERT INTO recipes (
                id, title, slug, source_name, source_url,
                instructions, servings, prep_time_min, cook_time_min, total_time_min,
                cuisine_type, tags, difficulty, quality_score,
                is_validated, created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :source_name, :source_url,
                :instructions, :servings, :prep_time, :cook_time, :total_time,
                :cuisine_type, :tags, :difficulty, :quality_score,
                TRUE, NOW(), NOW()
            )
            ON CONFLICT (title) DO NOTHING
            """
        ),
        {
            "id": recipe_id,
            "title": title,
            # Slug simple : titre en minuscules avec tirets
            "slug": title.lower().replace(" ", "-").replace("'", "").replace("œ", "oe"),
            "source_name": "sample",
            "source_url": f"local://sample/{recipe_id}",
            # Instructions : liste de chaînes → JSON PostgreSQL
            "instructions": json.dumps(recipe.get("instructions", []), ensure_ascii=False),
            "servings": recipe.get("servings", 4),
            "prep_time": prep_time,
            "cook_time": cook_time,
            "total_time": total_time,
            "cuisine_type": recipe.get("cuisine_type", "française"),
            # Tags : liste → JSON PostgreSQL (format attendu par le frontend)
            "tags": json.dumps(recipe.get("tags", []), ensure_ascii=False),
            "difficulty": difficulty,
            # Score de qualité maximal : recettes vérifiées manuellement
            "quality_score": 1.0,
        },
    )

    # Insertion des ingrédients canoniques + recipe_ingredients
    ingredients_raw: list[str] = recipe.get("ingredients", [])
    ingredient_rows = []

    for ingredient_str in ingredients_raw:
        # Extraction du nom canonique : supprimer les quantités en début de chaîne
        # Ex : "200 g de farine" → "farine"
        # Heuristique simple : prendre la partie après "de ", "d'", ou le dernier mot
        parts = ingredient_str.strip().split()
        # Cherche "de" ou "d'" dans la chaîne
        canonical_name = ingredient_str.strip()
        for i, word in enumerate(parts):
            if word.lower() in ("de", "d'", "des"):
                canonical_name = " ".join(parts[i + 1 :])
                break

        # Cleanup : supprimer les parenthèses et le contenu
        import re
        canonical_name = re.sub(r"\(.*?\)", "", canonical_name).strip()
        canonical_name = canonical_name.lower().strip(" ,.")
        if not canonical_name:
            continue

        # Lookup ou création de l'ingrédient canonique
        result = await session.execute(
            text(
                "SELECT id FROM ingredients WHERE canonical_name = :name LIMIT 1"
            ),
            {"name": canonical_name},
        )
        ing_row = result.fetchone()

        if ing_row:
            ingredient_id = str(ing_row[0])
        else:
            ingredient_id = str(uuid4())
            await session.execute(
                text(
                    """
                    INSERT INTO ingredients (id, canonical_name, created_at)
                    VALUES (:id, :name, NOW())
                    ON CONFLICT (canonical_name) DO NOTHING
                    """
                ),
                {"id": ingredient_id, "name": canonical_name},
            )
            # Recharger l'ID en cas de conflit ON CONFLICT DO NOTHING
            result = await session.execute(
                text(
                    "SELECT id FROM ingredients WHERE canonical_name = :name LIMIT 1"
                ),
                {"name": canonical_name},
            )
            ing_row_2 = result.fetchone()
            if ing_row_2:
                ingredient_id = str(ing_row_2[0])

        ingredient_rows.append({
            "recipe_id": recipe_id,
            "ingredient_id": ingredient_id,
            "quantity": None,
            "unit": None,
            "raw_text": ingredient_str,
        })

    # Insertion batch des recipe_ingredients
    for row in ingredient_rows:
        await session.execute(
            text(
                """
                INSERT INTO recipe_ingredients
                    (recipe_id, ingredient_id, quantity, unit, raw_text)
                VALUES
                    (:recipe_id, :ingredient_id, :quantity, :unit, :raw_text)
                ON CONFLICT DO NOTHING
                """
            ),
            row,
        )

    await session.commit()
    logger.info(
        "recipe_inserted",
        title=title,
        ingredients_count=len(ingredient_rows),
    )
    return True


async def main() -> None:
    """Point d'entrée principal du script d'import."""
    _configure_logging()
    _validate_env()

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    db_url = os.getenv("DATABASE_URL")

    if dry_run:
        logger.info("Mode DRY_RUN activé — aucune écriture en base.")

    recipes = _load_sample_recipes()

    logger.info(
        "import_start",
        total=len(recipes),
        db_url=db_url.split("@")[-1] if db_url else "?",  # Ne pas logger le mot de passe
    )

    # Création du moteur SQLAlchemy async
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    inserted = 0
    skipped = 0
    errors = 0

    async with session_factory() as session:
        for recipe in recipes:
            try:
                was_inserted = await _insert_recipe(session, recipe, dry_run)
                if was_inserted:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.error(
                    "recipe_insert_error",
                    title=recipe.get("title", "?"),
                    error=str(exc),
                )
                errors += 1
                # Rollback de la transaction courante pour continuer les suivantes
                await session.rollback()

    await engine.dispose()

    # ---- Rapport final ----
    logger.info("=" * 50)
    logger.info("RAPPORT D'IMPORT SAMPLE RECIPES")
    logger.info(f"  Total traité  : {len(recipes)}")
    logger.info(f"  Insérées      : {inserted}")
    logger.info(f"  Ignorées      : {skipped} (doublons)")
    logger.info(f"  Erreurs       : {errors}")
    logger.info("=" * 50)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
