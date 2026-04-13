"""
Tâches Celery pour l'agent RECIPE_SCOUT.

Ces tâches sont la couche d'intégration entre Celery et les classes Python.
Chaque tâche est :
- Routée vers la queue appropriée (scraping, llm, embedding)
- Configurable via les arguments (idempotente si possible)
- Dotée d'un retry automatique avec backoff exponentiel

Déclenchement :
- Nocturne : `run_recipe_scout_nightly` via Celery Beat (cron 02h00)
- Mapping OFF : `map_ingredients_to_off_task` via Celery Beat (cron 03h00)
- À la demande : appel direct depuis l'API ou les tests

Architecture Celery chain/group :
  run_recipe_scout_nightly()
    → group([scrape_marmiton_batch(urls)])
    → chain par recette :
        validate_recipe_quality(id)
        → embed_recipe(id)
        → tag_recipe(id)
"""

import asyncio
import os
from typing import Any
from uuid import UUID

from celery.utils.log import get_task_logger
from loguru import logger

from src.app import celery_app

# Logger Celery pour la compatibilité avec les workers
task_logger = get_task_logger(__name__)


@celery_app.task(
    name="src.agents.recipe_scout.tasks.scrape_marmiton_batch",
    queue="scraping",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=1800,
    time_limit=2100,
)
def scrape_marmiton_batch(self, url_list: list[str]) -> dict[str, Any]:
    """
    Scrape une liste d'URLs Marmiton en batch.

    Lance le spider Marmiton en mode synchrone (Scrapy n'est pas async).
    Les recettes scrapées sont retournées pour traitement ultérieur.

    Tâche routée vers la queue `scraping` pour isolation des ressources.
    Soft time limit : 30 minutes (batch de scraping peut être long).

    Args:
        url_list: Liste d'URLs Marmiton à scraper.

    Returns:
        Dict avec les statistiques du scraping.
    """
    from src.agents.recipe_scout.scrapers.marmiton import MarmitonScraper

    logger.info(
        "task_scrape_marmiton_start",
        url_count=len(url_list),
        task_id=self.request.id,
    )

    scraper = MarmitonScraper()
    scraped = []
    errors = []

    for url in url_list:
        try:
            recipe = scraper.scrape_url(url)
            if recipe and scraper.is_valid_raw_recipe(recipe):
                scraped.append(recipe.title)
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            logger.warning("task_scrape_url_error", url=url, error=str(exc))

    logger.info(
        "task_scrape_marmiton_complete",
        scraped_count=len(scraped),
        error_count=len(errors),
        task_id=self.request.id,
    )

    return {
        "scraped_count": len(scraped),
        "error_count": len(errors),
        "urls_processed": len(url_list),
    }


@celery_app.task(
    name="src.agents.recipe_scout.tasks.validate_recipe_quality",
    queue="llm",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=150,
)
def validate_recipe_quality(self, recipe_id: str) -> dict[str, Any]:
    """
    Valide la qualité d'une recette existante en base via LLM.

    Récupère la recette depuis la DB, appelle le validateur LLM Claude,
    et met à jour le quality_score en base.

    Args:
        recipe_id: UUID de la recette à valider.

    Returns:
        Dict avec le quality_score, is_valid et le recipe_id.
    """
    from src.agents.recipe_scout.validator import validate_recipe_quality as _validate

    logger.info(
        "task_validate_recipe_start",
        recipe_id=recipe_id,
        task_id=self.request.id,
    )

    async def _run() -> dict[str, Any]:
        from mealplanner_db.models import Recipe
        from mealplanner_db.session import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            # Récupération de la recette avec ses ingrédients
            recipe = await session.get(Recipe, UUID(recipe_id))
            if recipe is None:
                raise ValueError(f"Recette {recipe_id} introuvable en base.")

            # Extraction des ingrédients bruts depuis recipe_ingredients
            result = await session.execute(
                text(
                    """
                    SELECT i.canonical_name, ri.quantity, ri.unit, ri.notes
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = :recipe_id
                    ORDER BY ri.position
                    """
                ),
                {"recipe_id": recipe_id},
            )
            ingredient_rows = result.mappings().all()

            ingredients_raw = [
                f"{row['quantity']} {row['unit']} {row['canonical_name']}"
                if row.get("quantity") else row["canonical_name"]
                for row in ingredient_rows
            ]

            # Instructions depuis le champ JSONB
            instructions_list = recipe.instructions or []
            instructions_raw = [
                step.get("text", "") if isinstance(step, dict) else str(step)
                for step in instructions_list
                if step
            ]

            # Appel validateur LLM
            api_key = os.getenv("ANTHROPIC_API_KEY")
            validation = await _validate(
                title=recipe.title,
                ingredients=ingredients_raw,
                instructions=instructions_raw,
                prep_time_min=recipe.prep_time_min,
                cook_time_min=recipe.cook_time_min,
                api_key=api_key,
            )

            # Mise à jour du quality_score en base
            await session.execute(
                text(
                    """
                    UPDATE recipes
                    SET quality_score = :score, updated_at = NOW()
                    WHERE id = :recipe_id
                    """
                ),
                {"score": validation.quality_score, "recipe_id": recipe_id},
            )
            await session.commit()

            logger.info(
                "task_validate_recipe_complete",
                recipe_id=recipe_id,
                quality_score=round(validation.quality_score, 3),
                is_valid=validation.is_valid,
                issues_count=len(validation.issues),
            )

            return {
                "recipe_id": recipe_id,
                "score": validation.quality_score,
                "is_valid": validation.is_valid,
                "passed": validation.quality_score >= 0.6,
                "issues_count": len(validation.issues),
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


@celery_app.task(
    name="src.agents.recipe_scout.tasks.embed_recipe",
    queue="embedding",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=150,
)
def embed_recipe(self, recipe_id: str) -> dict[str, Any]:
    """
    Calcule et stocke l'embedding vectoriel d'une recette.

    Charge le modèle sentence-transformers (singleton — chargé une seule fois),
    calcule le vecteur 384 dims, et l'insère dans recipe_embeddings.

    Args:
        recipe_id: UUID de la recette à vectoriser.

    Returns:
        Dict avec le recipe_id et la dimension du vecteur.
    """
    try:
        from src.agents.recipe_scout.embedder import RecipeEmbedder
    except ImportError:
        logger.warning("embed_skipped_no_sentence_transformers", recipe_id=recipe_id)
        return {"recipe_id": recipe_id, "status": "skipped", "reason": "sentence-transformers not installed"}

    logger.info(
        "task_embed_recipe_start",
        recipe_id=recipe_id,
        task_id=self.request.id,
    )

    async def _run() -> dict[str, Any]:
        from mealplanner_db.models import Recipe
        from mealplanner_db.session import AsyncSessionLocal
        from sqlalchemy import text

        embedder = RecipeEmbedder.get_instance()

        async with AsyncSessionLocal() as session:
            recipe = await session.get(Recipe, UUID(recipe_id))
            if recipe is None:
                raise ValueError(f"Recette {recipe_id} introuvable en base.")

            # Récupération des ingrédients canoniques
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
            ingredient_names = [row[0] for row in result.fetchall()]

            # Construction du texte pour l'embedding
            text_to_embed = embedder.build_recipe_text(
                title=recipe.title,
                ingredients=ingredient_names,
                cuisine_type=recipe.cuisine_type,
                tags=recipe.tags or [],
            )

            # Calcul de l'embedding
            embedding = embedder.embed(text_to_embed)
            embedding_str = "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"

            # Insertion ou mise à jour dans recipe_embeddings
            total_time = (recipe.prep_time_min or 0) + (recipe.cook_time_min or 0) or None

            await session.execute(
                text(
                    """
                    INSERT INTO recipe_embeddings (
                        recipe_id, embedding, tags, total_time_min, cuisine_type
                    ) VALUES (
                        :recipe_id, :embedding::vector, :tags, :total_time_min, :cuisine_type
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
                    "tags": recipe.tags or [],
                    "total_time_min": total_time,
                    "cuisine_type": recipe.cuisine_type,
                },
            )
            await session.commit()

            logger.info(
                "task_embed_recipe_complete",
                recipe_id=recipe_id,
                embedding_dim=len(embedding),
            )

            return {
                "recipe_id": recipe_id,
                "embedding_dim": len(embedding),
                "status": "completed",
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


@celery_app.task(
    name="src.agents.recipe_scout.tasks.tag_recipe",
    queue="llm",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=150,
)
def tag_recipe(self, recipe_id: str) -> dict[str, Any]:
    """
    Génère et stocke les tags LLM pour une recette existante en base.

    Récupère la recette, appelle le tagger LLM Claude,
    et met à jour les colonnes tags et cuisine_type.

    Args:
        recipe_id: UUID de la recette à tagger.

    Returns:
        Dict avec les tags générés et le cuisine_type.
    """
    logger.info(
        "task_tag_recipe_start",
        recipe_id=recipe_id,
        task_id=self.request.id,
    )

    async def _run() -> dict[str, Any]:
        from mealplanner_db.models import Recipe
        from mealplanner_db.session import AsyncSessionLocal
        from sqlalchemy import text

        from src.agents.recipe_scout.tagger import merge_tags_to_list
        from src.agents.recipe_scout.tagger import tag_recipe as _tag

        async with AsyncSessionLocal() as session:
            recipe = await session.get(Recipe, UUID(recipe_id))
            if recipe is None:
                raise ValueError(f"Recette {recipe_id} introuvable en base.")

            # Récupération des ingrédients bruts
            result = await session.execute(
                text(
                    """
                    SELECT i.canonical_name, ri.quantity, ri.unit
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = :recipe_id
                    ORDER BY ri.position
                    """
                ),
                {"recipe_id": recipe_id},
            )
            ingredient_rows = result.mappings().all()
            ingredients_raw = [
                f"{row['quantity']} {row['unit']} {row['canonical_name']}"
                if row.get("quantity") else row["canonical_name"]
                for row in ingredient_rows
            ]

            # Instructions depuis JSONB
            instructions_list = recipe.instructions or []
            instructions_raw = [
                step.get("text", "") if isinstance(step, dict) else str(step)
                for step in instructions_list
                if step
            ]

            # Appel tagger LLM
            tags_result = await _tag(
                title=recipe.title,
                ingredients=ingredients_raw,
                instructions=instructions_raw,
                prep_time_min=recipe.prep_time_min,
                cook_time_min=recipe.cook_time_min,
                existing_tags=recipe.tags or [],
            )
            tags_list = merge_tags_to_list(tags_result)

            # Mise à jour en base
            await session.execute(
                text(
                    """
                    UPDATE recipes
                    SET tags = :tags,
                        cuisine_type = :cuisine_type,
                        updated_at = NOW()
                    WHERE id = :recipe_id
                    """
                ),
                {
                    "tags": tags_list,
                    "cuisine_type": tags_result.cuisine,
                    "recipe_id": recipe_id,
                },
            )
            await session.commit()

            logger.info(
                "task_tag_recipe_complete",
                recipe_id=recipe_id,
                cuisine=tags_result.cuisine,
                tags_count=len(tags_list),
            )

            return {
                "recipe_id": recipe_id,
                "cuisine_type": tags_result.cuisine,
                "tags": tags_list,
                "status": "completed",
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


@celery_app.task(
    queue="embedding",
    name="recipe_scout.map_ingredients_to_off",
    bind=True,
    max_retries=1,
    soft_time_limit=3600,  # 1 heure max pour le batch OFF
    time_limit=3700,
)
def map_ingredients_to_off_task(self, batch_size: int = 50) -> dict[str, Any]:
    """
    Batch mapping des ingrédients canoniques vers Open Food Facts.

    Planifié par Celery Beat tous les jours à 3h du matin,
    après le scraping nocturne (run_recipe_scout_nightly à 2h).

    Args:
        batch_size: Nombre d'ingrédients à traiter par run.

    Returns:
        Dict avec les statistiques du mapping.
    """
    logger.info(
        "task_map_ingredients_off_start",
        batch_size=batch_size,
        task_id=self.request.id,
    )

    async def _run() -> dict[str, Any]:
        from mealplanner_db.session import AsyncSessionLocal

        from src.agents.recipe_scout.off_mapper import OFFMapper

        mapper = OFFMapper(session_factory=AsyncSessionLocal)
        stats = await mapper.map_missing_ingredients(batch_size=batch_size)
        return stats

    try:
        result = asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_run())
        finally:
            loop.close()

    logger.info(
        "task_map_ingredients_off_complete",
        task_id=self.request.id,
        **result,
    )

    return {"status": "completed", **result}


@celery_app.task(
    name="recipe_scout.import_from_spoonacular",
    queue="scraping",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    soft_time_limit=600,   # 10 minutes max (free tier 150 req/jour)
    time_limit=660,
)
def import_from_spoonacular_task(
    self,
    max_recipes: int = 50,
    cuisines: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Importe des recettes depuis l'API Spoonacular dans PostgreSQL.

    Tâche déclenchable manuellement ou via Celery Beat (batch hebdomadaire recommandé
    pour rester dans la limite de 150 req/jour du free tier).

    Args:
        max_recipes: Nombre maximum de recettes à importer (défaut : 50).
        cuisines: Cuisines cibles séparées par virgule. Chaîne vide = toutes les cuisines
                  par défaut (french, italian, japanese, mexican, indian, thai, ...).
        dry_run: Si True, simule l'import sans écriture en base (utile pour tester le quota).

    Returns:
        Dict avec les compteurs : total_fetched, inserted, skipped, errors, api_requests.
    """
    from src.scripts.import_spoonacular import CUISINES_DEFAULT, run_import

    db_url = os.getenv("DATABASE_URL", "")
    api_key = os.getenv("SPOONACULAR_API_KEY", "")

    if not db_url:
        logger.error("import_from_spoonacular_task_no_db_url")
        return {"status": "error", "reason": "DATABASE_URL manquante"}

    if not api_key:
        logger.error("import_from_spoonacular_task_no_api_key")
        return {"status": "error", "reason": "SPOONACULAR_API_KEY manquante"}

    cuisines_list: list[str] = cuisines.split(",") if cuisines else CUISINES_DEFAULT

    logger.info(
        "task_import_spoonacular_start",
        max_recipes=max_recipes,
        cuisines=cuisines_list,
        dry_run=dry_run,
        task_id=self.request.id,
    )

    def _run_async() -> dict[str, Any]:
        """Lance la coroutine async dans un event loop isolé."""
        try:
            return asyncio.run(
                run_import(
                    database_url=db_url,
                    api_key=api_key,
                    max_recipes=max_recipes,
                    cuisines=cuisines_list,
                    dry_run=dry_run,
                )
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    run_import(
                        database_url=db_url,
                        api_key=api_key,
                        max_recipes=max_recipes,
                        cuisines=cuisines_list,
                        dry_run=dry_run,
                    )
                )
            finally:
                loop.close()

    try:
        stats = _run_async()
    except Exception as exc:
        logger.error(
            "task_import_spoonacular_error",
            error=str(exc),
            task_id=self.request.id,
        )
        raise self.retry(exc=exc)

    logger.info(
        "task_import_spoonacular_complete",
        task_id=self.request.id,
        **stats,
    )

    return {"status": "completed", **stats}


@celery_app.task(
    name="src.agents.recipe_scout.tasks.run_recipe_scout_nightly",
    queue="default",
    bind=True,
    max_retries=1,
    soft_time_limit=7200,  # 2 heures pour le batch nocturne complet
    time_limit=7500,
)
def run_recipe_scout_nightly(self) -> dict[str, Any]:
    """
    Orchestre le pipeline complet RECIPE_SCOUT pour le batch nocturne.

    Lance en séquence :
    1. Collecte depuis toutes les sources (Marmiton + 750g + Allrecipes + APIs)
    2. Normalisation, déduplication, validation, tagging, embedding
    3. Insertion en DB

    Planifié par Celery Beat à 02h00 chaque nuit.
    Durée estimée : 30-90 minutes selon le volume et les latences API.

    Returns:
        Dict avec les statistiques du run.
    """
    logger.info(
        "task_recipe_scout_nightly_start",
        task_id=self.request.id,
    )

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("task_recipe_scout_nightly_no_db_url")
        return {"status": "error", "reason": "DATABASE_URL manquante"}

    from src.agents.recipe_scout.agent import RecipeScoutAgent

    agent = RecipeScoutAgent(
        db_url=db_url,
        max_recipes_per_source=100,
        sources=["marmiton", "750g", "allrecipes", "spoonacular", "edamam"],
    )

    try:
        stats = asyncio.run(agent.run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(agent.run())
        finally:
            loop.close()

    result = {
        "status": "completed",
        "total_scraped": stats.total_scraped,
        "total_inserted": stats.total_inserted,
        "total_rejected_quality": stats.total_rejected_quality,
        "total_deduplicated": stats.total_deduplicated,
        "errors_count": len(stats.errors),
        "duration_seconds": stats.duration_seconds,
        "success_rate": round(stats.success_rate, 3),
    }

    logger.info(
        "task_recipe_scout_nightly_complete",
        task_id=self.request.id,
        **result,
    )

    return result
