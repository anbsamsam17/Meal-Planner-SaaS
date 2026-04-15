"""
Script de backfill des embeddings pour les recettes existantes.

Génère et insère les embeddings pgvector pour toutes les recettes
qui n'ont pas encore d'entrée dans recipe_embeddings.

Contexte (2026-04-14) :
- 591 recettes seed importées via import_sample_recipes.py sans embeddings
- La tâche embed_recipe (Celery) avait un bug : appelait embedder.embed() au lieu
  de embedder.embed_text() → AttributeError silencieux → aucun embedding généré
- Ce script est le remède immédiat pour peupler recipe_embeddings en une seule passe

Usage :
    cd apps/worker
    uv pip install 'mealplanner-worker[ml]'   # installe sentence-transformers
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner \\
    uv run python -m src.scripts.backfill_embeddings

Variables d'environnement :
    DATABASE_URL    Obligatoire — connexion PostgreSQL async (asyncpg).
    BATCH_SIZE      Optionnel — nombre de recettes traitées par batch (défaut: 32).
    DRY_RUN         Optionnel — "true" pour calculer sans insérer.
    LOG_LEVEL       Optionnel — DEBUG/INFO/WARNING (défaut: INFO).
"""

import asyncio
import os
import sys
import time

from loguru import logger


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
    """Vérifie les prérequis avant de démarrer."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "DATABASE_URL manquante. "
            "Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/mealplanner"
        )
        sys.exit(1)

    try:
        from src.agents.recipe_scout.embedder import RecipeEmbedder  # noqa: F401
    except ImportError:
        logger.error(
            "sentence-transformers non installé. "
            "Lancer : uv pip install 'mealplanner-worker[ml]'"
        )
        sys.exit(1)


async def _fetch_recipes_without_embeddings(session) -> list[dict]:
    """
    Récupère toutes les recettes sans embedding dans recipe_embeddings.

    Utilise un LEFT JOIN pour identifier les recettes manquantes.
    Inclut les ingrédients canoniques pour construire un texte riche.

    Returns:
        Liste de dicts avec id, title, cuisine_type, tags, ingredients.
    """
    from sqlalchemy import text

    result = await session.execute(
        text(
            """
            SELECT
                r.id::text,
                r.title,
                r.cuisine_type,
                r.tags,
                r.prep_time_min,
                r.cook_time_min
            FROM recipes r
            LEFT JOIN recipe_embeddings re ON re.recipe_id = r.id
            WHERE re.recipe_id IS NULL
            ORDER BY r.created_at ASC
            """
        )
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def _fetch_recipe_ingredients(session, recipe_id: str) -> list[str]:
    """
    Récupère les noms canoniques des 10 premiers ingrédients d'une recette.

    Args:
        session: Session SQLAlchemy async.
        recipe_id: UUID de la recette.

    Returns:
        Liste de noms canoniques d'ingrédients.
    """
    from sqlalchemy import text

    result = await session.execute(
        text(
            """
            SELECT i.canonical_name
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = :recipe_id
            ORDER BY ri.position
            LIMIT 10
            """
        ),
        {"recipe_id": recipe_id},
    )
    return [row[0] for row in result.fetchall()]


async def _insert_embedding(
    session,
    recipe_id: str,
    embedding: list[float],
    tags: list,
    total_time_min: int | None,
    cuisine_type: str | None,
    dry_run: bool,
) -> None:
    """
    Insère ou met à jour l'embedding dans recipe_embeddings.

    Utilise ON CONFLICT DO UPDATE pour être idempotent.

    Args:
        session: Session SQLAlchemy async.
        recipe_id: UUID de la recette.
        embedding: Vecteur 384 dims.
        tags: Tags de la recette.
        total_time_min: Temps total de préparation en minutes.
        cuisine_type: Type de cuisine.
        dry_run: Si True, ne fait pas l'insertion.
    """
    if dry_run:
        return

    from sqlalchemy import text

    embedding_str = "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"

    await session.execute(
        text(
            """
            INSERT INTO recipe_embeddings (
                recipe_id, embedding, tags, total_time_min, cuisine_type
            ) VALUES (
                :recipe_id, CAST(:embedding AS vector), CAST(:tags AS text[]), :total_time_min, :cuisine_type
            )
            ON CONFLICT (recipe_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                tags = EXCLUDED.tags,
                total_time_min = EXCLUDED.total_time_min,
                cuisine_type = EXCLUDED.cuisine_type,
                updated_at = NOW()
            """
        ),
        {
            "recipe_id": recipe_id,
            "embedding": embedding_str,
            "tags": tags if isinstance(tags, list) else [],
            "total_time_min": total_time_min,
            "cuisine_type": cuisine_type,
        },
    )


async def main() -> None:
    """Point d'entrée principal du script de backfill."""
    _configure_logging()
    _validate_env()

    batch_size = int(os.getenv("BATCH_SIZE", "32"))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    db_url = os.getenv("DATABASE_URL")

    if dry_run:
        logger.info("Mode DRY_RUN — les embeddings NE seront PAS insérés en base.")

    # Chargement du modèle (singleton — chargé une seule fois)
    logger.info("backfill_embedder_loading", model="all-MiniLM-L6-v2")
    from src.agents.recipe_scout.embedder import RecipeEmbedder

    embedder = RecipeEmbedder.get_instance()
    # Forcer le chargement du modèle maintenant (lazy load)
    embedder.embed_text("init")
    logger.info("backfill_embedder_ready")

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, pool_size=5)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    start_time = time.monotonic()
    total_processed = 0
    total_inserted = 0
    total_errors = 0

    async with session_factory() as session:
        # Récupération de toutes les recettes sans embedding
        recipes_without = await _fetch_recipes_without_embeddings(session)

        if not recipes_without:
            logger.info("backfill_nothing_to_do", message="Toutes les recettes ont déjà un embedding.")
            await engine.dispose()
            return

        logger.info(
            "backfill_start",
            total_recipes=len(recipes_without),
            batch_size=batch_size,
            dry_run=dry_run,
        )

        # Traitement par batch pour éviter de saturer la mémoire
        for batch_start in range(0, len(recipes_without), batch_size):
            batch = recipes_without[batch_start : batch_start + batch_size]

            # Construction des textes pour le batch embedding
            batch_texts = []
            for recipe in batch:
                ingredient_names = await _fetch_recipe_ingredients(session, recipe["id"])

                # Normalisation des tags : peut être une liste Python ou None
                tags_raw = recipe.get("tags") or []
                if isinstance(tags_raw, str):
                    import json
                    try:
                        tags_raw = json.loads(tags_raw)
                    except (json.JSONDecodeError, ValueError):
                        tags_raw = []

                text = embedder.build_recipe_text(
                    title=recipe["title"],
                    ingredients=ingredient_names,
                    cuisine_type=recipe.get("cuisine_type"),
                    tags=tags_raw[:5] if tags_raw else [],
                )
                batch_texts.append(text)

            # Calcul des embeddings en batch (plus rapide que les appels individuels)
            try:
                embeddings = embedder.embed_batch(batch_texts, batch_size=batch_size)
            except Exception as exc:
                logger.error(
                    "backfill_batch_embed_error",
                    batch_start=batch_start,
                    error=str(exc),
                )
                total_errors += len(batch)
                continue

            # Insertion des embeddings en base
            for i, recipe in enumerate(batch):
                total_processed += 1
                try:
                    tags_raw = recipe.get("tags") or []
                    if isinstance(tags_raw, str):
                        import json
                        try:
                            tags_raw = json.loads(tags_raw)
                        except (json.JSONDecodeError, ValueError):
                            tags_raw = []

                    prep = recipe.get("prep_time_min") or 0
                    cook = recipe.get("cook_time_min") or 0
                    total_time = (prep + cook) or None

                    await _insert_embedding(
                        session=session,
                        recipe_id=recipe["id"],
                        embedding=embeddings[i],
                        tags=tags_raw,
                        total_time_min=total_time,
                        cuisine_type=recipe.get("cuisine_type"),
                        dry_run=dry_run,
                    )
                    total_inserted += 1

                except Exception as exc:
                    logger.error(
                        "backfill_insert_error",
                        recipe_id=recipe["id"],
                        title=recipe["title"][:50],
                        error=str(exc),
                    )
                    total_errors += 1

            # Commit par batch pour éviter une transaction trop longue
            if not dry_run:
                await session.commit()

            batch_end = min(batch_start + batch_size, len(recipes_without))
            logger.info(
                "backfill_batch_done",
                processed=f"{batch_end}/{len(recipes_without)}",
                inserted_this_batch=len(batch) - (total_errors - (total_errors - total_errors)),
                elapsed_s=round(time.monotonic() - start_time, 1),
            )

    await engine.dispose()

    elapsed = time.monotonic() - start_time

    # ---- Rapport final ----
    logger.info("=" * 60)
    logger.info("RAPPORT BACKFILL EMBEDDINGS")
    logger.info(f"  Durée             : {elapsed:.1f}s")
    logger.info(f"  Recettes traitées : {total_processed}")
    logger.info(f"  Embeddings insérés : {total_inserted}")
    logger.info(f"  Erreurs           : {total_errors}")
    if dry_run:
        logger.info("  Mode DRY_RUN — aucune écriture en base.")
    logger.info("=" * 60)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
