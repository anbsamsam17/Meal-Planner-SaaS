"""Nettoyage des recettes de mauvaise qualité dans la base de données.

Analyse chaque recette et calcule un score de qualité détaillé sur 100 points.
Supprime en cascade (embeddings → ingrédients → recette) toutes les recettes
dont le score est inférieur au seuil configuré.

Seules les recettes provenant de sources de mauvaise qualité connues (themealdb,
sample) peuvent être supprimées. Les imports Spoonacular, Edamam, Marmiton et
750g sont protégés.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... \\
    uv run python -m src.scripts.cleanup_low_quality

Variables d'environnement :
    DATABASE_URL        Obligatoire — connexion PostgreSQL async (asyncpg).
    QUALITY_THRESHOLD   Optionnel — score minimum pour conserver (défaut : 50).
    DRY_RUN             Optionnel — "true" pour simuler sans écriture (défaut : true).
    LOG_LEVEL           Optionnel — DEBUG/INFO/WARNING (défaut : INFO).
    BATCH_SIZE          Optionnel — nombre de recettes traitées par lot (défaut : 100).
"""

import asyncio
import os
import sys
from collections import defaultdict
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Sources autorisées à la suppression — les autres sont protégées.
DELETABLE_SOURCES: frozenset[str] = frozenset({"themealdb", "sample"})

# Seuil par défaut : les recettes avec score < 50 sont supprimées.
DEFAULT_QUALITY_THRESHOLD = 50

# Taille des lots SQL pour les DELETE en cascade.
DEFAULT_BATCH_SIZE = 100

# URL placeholder connue TheMealDB (photo absente).
PLACEHOLDER_PHOTO_PATTERNS: tuple[str, ...] = (
    "placeholder",
    "no-image",
    "no_image",
    "default",
    "missing",
    "thumb/0.jpg",
)


# ---------------------------------------------------------------------------
# Calcul du score de qualité
# ---------------------------------------------------------------------------


def _photo_is_valid(photo_url: str | None) -> bool:
    """Retourne True si la photo_url est présente et ne ressemble pas à un placeholder."""
    if not photo_url or not photo_url.strip():
        return False
    url_lower = photo_url.lower()
    for pattern in PLACEHOLDER_PHOTO_PATTERNS:
        if pattern in url_lower:
            return False
    return True


def _nutrition_is_valid(nutrition: dict[str, Any] | None) -> bool:
    """Retourne True si nutrition contient au moins calories et protein_g."""
    if not nutrition or not isinstance(nutrition, dict):
        return False
    has_calories = nutrition.get("calories") is not None
    has_protein = nutrition.get("protein_g") is not None
    return has_calories and has_protein


def _instructions_are_detailed(instructions: list[dict[str, Any]] | None) -> bool:
    """Retourne True si la recette a >= 3 steps avec chacun > 20 caractères."""
    if not instructions or not isinstance(instructions, list):
        return False
    detailed_steps = [
        step
        for step in instructions
        if isinstance(step, dict)
        and len((step.get("text") or "").strip()) > 20
    ]
    return len(detailed_steps) >= 3


def calculate_quality_score(
    recipe: dict[str, Any],
    ingredient_count: int,
) -> tuple[int, dict[str, int]]:
    """Calcule le score de qualité d'une recette sur 100 points.

    Critères et points associés :
        photo_url valide              +20
        nutrition avec calories+prot  +20
        >= 3 steps détaillés (> 20c)  +20
        description > 50 chars        +10
        >= 3 tags                     +10
        >= 4 ingrédients              +10
        cuisine_type non null         + 5
        prep_time ET cook_time        + 5
        ─────────────────────────────────
        Total max                    100

    Returns:
        Tuple (score_total, détail_par_critère).
    """
    breakdown: dict[str, int] = {}

    # Photo (+20)
    breakdown["photo"] = 20 if _photo_is_valid(recipe.get("photo_url")) else 0

    # Nutrition (+20)
    breakdown["nutrition"] = 20 if _nutrition_is_valid(recipe.get("nutrition")) else 0

    # Instructions détaillées (+20)
    breakdown["instructions"] = (
        20 if _instructions_are_detailed(recipe.get("instructions")) else 0
    )

    # Description (+10)
    description = (recipe.get("description") or "").strip()
    breakdown["description"] = 10 if len(description) > 50 else 0

    # Tags (+10)
    tags = recipe.get("tags") or []
    breakdown["tags"] = 10 if len(tags) >= 3 else 0

    # Ingrédients (+10)
    breakdown["ingredients"] = 10 if ingredient_count >= 4 else 0

    # Cuisine type (+5)
    breakdown["cuisine_type"] = 5 if recipe.get("cuisine_type") else 0

    # Temps de préparation et de cuisson (+5)
    has_prep = recipe.get("prep_time_min") is not None
    has_cook = recipe.get("cook_time_min") is not None
    breakdown["timing"] = 5 if (has_prep and has_cook) else 0

    total = sum(breakdown.values())
    return total, breakdown


# ---------------------------------------------------------------------------
# Requêtes SQL
# ---------------------------------------------------------------------------


async def _fetch_recipes_batch(
    session: Any,
    offset: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    """Récupère un lot de recettes des sources supprimables avec leur nombre d'ingrédients.

    Filtre en amont sur DELETABLE_SOURCES pour ne jamais charger les recettes
    de qualité (Spoonacular, Edamam, etc.).
    """
    from sqlalchemy import text

    # La liste DELETABLE_SOURCES est construite statiquement — sécurisée.
    sources_placeholder = ", ".join(f"'{s}'" for s in sorted(DELETABLE_SOURCES))

    result = await session.execute(
        text(
            f"""
            SELECT
                r.id,
                r.title,
                r.source,
                r.photo_url,
                r.nutrition,
                r.instructions,
                r.description,
                r.tags,
                r.cuisine_type,
                r.prep_time_min,
                r.cook_time_min,
                r.quality_score,
                COUNT(ri.ingredient_id) AS ingredient_count
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            WHERE r.source IN ({sources_placeholder})
            GROUP BY r.id
            ORDER BY r.created_at ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": batch_size, "offset": offset},
    )
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


async def _count_deletable_recipes(session: Any) -> int:
    """Retourne le nombre total de recettes des sources supprimables."""
    from sqlalchemy import text

    sources_placeholder = ", ".join(f"'{s}'" for s in sorted(DELETABLE_SOURCES))
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM recipes WHERE source IN ({sources_placeholder})")
    )
    row = result.fetchone()
    return int(row[0]) if row else 0


async def _get_avg_quality_score(session: Any, source_filter: str | None = None) -> float:
    """Retourne le score qualité moyen de toutes les recettes, ou par source."""
    from sqlalchemy import text

    if source_filter:
        result = await session.execute(
            text(
                "SELECT AVG(quality_score) FROM recipes WHERE source = :source AND quality_score IS NOT NULL"
            ),
            {"source": source_filter},
        )
    else:
        result = await session.execute(
            text("SELECT AVG(quality_score) FROM recipes WHERE quality_score IS NOT NULL")
        )
    row = result.fetchone()
    if row is None or row[0] is None:
        return 0.0
    return float(row[0])


async def _count_recipes_by_source(session: Any) -> dict[str, int]:
    """Retourne le nombre de recettes groupé par source."""
    from sqlalchemy import text

    result = await session.execute(
        text("SELECT source, COUNT(*) FROM recipes GROUP BY source ORDER BY COUNT(*) DESC")
    )
    return {row[0]: int(row[1]) for row in result.fetchall()}


async def _delete_recipes_cascade(
    session: Any,
    recipe_ids: list[str],
    dry_run: bool,
) -> int:
    """Supprime les recettes et leurs dépendances en cascade.

    Ordre : recipe_embeddings → recipe_ingredients → recipes.
    Utilise des opérations en lot pour les performances.

    Returns:
        Nombre de recettes effectivement supprimées (0 en DRY_RUN).
    """
    from sqlalchemy import text

    if not recipe_ids:
        return 0

    if dry_run:
        logger.debug(
            "[DRY_RUN] would_delete_cascade",
            recipe_count=len(recipe_ids),
        )
        return 0

    # Construction du placeholder pour la liste d'IDs
    id_params = {f"id_{i}": rid for i, rid in enumerate(recipe_ids)}
    id_placeholders = ", ".join(f":id_{i}" for i in range(len(recipe_ids)))

    # 1. Suppression des embeddings
    await session.execute(
        text(f"DELETE FROM recipe_embeddings WHERE recipe_id IN ({id_placeholders})"),
        id_params,
    )

    # 2. Suppression des ingrédients liés
    await session.execute(
        text(f"DELETE FROM recipe_ingredients WHERE recipe_id IN ({id_placeholders})"),
        id_params,
    )

    # 3. Suppression des recettes
    result = await session.execute(
        text(f"DELETE FROM recipes WHERE id IN ({id_placeholders})"),
        id_params,
    )

    await session.commit()
    deleted = result.rowcount if result.rowcount is not None else len(recipe_ids)
    return deleted


# ---------------------------------------------------------------------------
# Moteur principal
# ---------------------------------------------------------------------------


async def run_cleanup(
    database_url: str,
    quality_threshold: int = DEFAULT_QUALITY_THRESHOLD,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Orchestre l'analyse et la suppression des recettes de mauvaise qualité.

    Appelable directement depuis une tâche Celery (await run_cleanup(...)).

    Args:
        database_url:       URL de connexion PostgreSQL async.
        quality_threshold:  Score minimum pour conserver une recette (0-100).
        batch_size:         Nombre de recettes analysées par lot.
        dry_run:            Si True, aucune modification n'est appliquée en base.

    Returns:
        Dict de statistiques : total_analyzed, to_delete, deleted, kept,
        avg_score_before, avg_score_after (estimé), by_source.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    logger.info(
        "cleanup_start",
        quality_threshold=quality_threshold,
        batch_size=batch_size,
        dry_run=dry_run,
        deletable_sources=sorted(DELETABLE_SOURCES),
    )

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Compteurs globaux
    total_analyzed = 0
    to_delete: list[dict[str, Any]] = []  # {"id", "title", "source", "score", "breakdown"}
    score_sum_analyzed = 0.0
    score_sum_kept = 0.0
    kept_count = 0
    by_source_analyzed: dict[str, int] = defaultdict(int)
    by_source_to_delete: dict[str, int] = defaultdict(int)

    async with session_factory() as session:
        # Statistiques globales avant nettoyage
        total_deletable = await _count_deletable_recipes(session)
        avg_score_before = await _get_avg_quality_score(session)
        counts_by_source_before = await _count_recipes_by_source(session)

        logger.info(
            "db_state_before",
            total_deletable=total_deletable,
            avg_quality_score_all=round(avg_score_before, 3),
            by_source=counts_by_source_before,
        )

        if total_deletable == 0:
            logger.info("no_deletable_recipes_found")
            await engine.dispose()
            return {
                "total_analyzed": 0,
                "to_delete": 0,
                "deleted": 0,
                "kept": 0,
                "avg_score_before": avg_score_before,
                "avg_score_after": avg_score_before,
                "by_source": {},
            }

        # Analyse par lots
        offset = 0
        while True:
            batch = await _fetch_recipes_batch(session, offset, batch_size)
            if not batch:
                break

            for recipe in batch:
                recipe_id = str(recipe["id"])
                title = recipe["title"] or "Sans titre"
                source = recipe["source"] or "unknown"
                ingredient_count = int(recipe["ingredient_count"] or 0)

                score, breakdown = calculate_quality_score(recipe, ingredient_count)
                total_analyzed += 1
                score_sum_analyzed += score
                by_source_analyzed[source] += 1

                logger.debug(
                    "recipe_analyzed",
                    title=title,
                    source=source,
                    score=score,
                    breakdown=breakdown,
                    ingredient_count=ingredient_count,
                )

                if score < quality_threshold:
                    to_delete.append(
                        {
                            "id": recipe_id,
                            "title": title,
                            "source": source,
                            "score": score,
                            "breakdown": breakdown,
                        }
                    )
                    by_source_to_delete[source] += 1
                    logger.info(
                        "recipe_marked_for_deletion",
                        title=title,
                        source=source,
                        score=score,
                        threshold=quality_threshold,
                        missing_criteria=[k for k, v in breakdown.items() if v == 0],
                    )
                else:
                    kept_count += 1
                    score_sum_kept += score

            offset += batch_size
            logger.debug(
                "batch_processed",
                offset=offset,
                total_analyzed=total_analyzed,
                to_delete_so_far=len(to_delete),
            )

        # Calcul des moyennes
        avg_score_analyzed = (
            score_sum_analyzed / total_analyzed if total_analyzed > 0 else 0.0
        )
        avg_score_kept = (
            score_sum_kept / kept_count if kept_count > 0 else 0.0
        )

        # Rapport avant suppression
        logger.info("=" * 60)
        logger.info("ANALYSE TERMINÉE — RÉCAPITULATIF")
        logger.info(f"  Recettes analysées         : {total_analyzed}")
        logger.info(f"  Score moyen (analysées)    : {avg_score_analyzed:.1f}/100")
        logger.info(f"  À supprimer (score < {quality_threshold})  : {len(to_delete)}")
        logger.info(f"  À conserver                : {kept_count}")
        logger.info(f"  Score moyen (conservées)   : {avg_score_kept:.1f}/100")
        logger.info("  Distribution par source :")
        for src in sorted(by_source_analyzed):
            analyzed = by_source_analyzed[src]
            deleted = by_source_to_delete.get(src, 0)
            logger.info(f"    {src}: {analyzed} analysées, {deleted} à supprimer")
        logger.info("=" * 60)

        if dry_run:
            logger.info("[DRY_RUN] Aucune modification appliquée en base.")
            logger.info(
                "[DRY_RUN] Relancer avec DRY_RUN=false pour effectuer la suppression."
            )
            if to_delete:
                logger.info(f"[DRY_RUN] Exemples de recettes qui seraient supprimées :")
                for entry in to_delete[:10]:
                    logger.info(
                        "[DRY_RUN] would_delete",
                        title=entry["title"],
                        source=entry["source"],
                        score=entry["score"],
                    )
                if len(to_delete) > 10:
                    logger.info(f"[DRY_RUN] ... et {len(to_delete) - 10} autres recettes.")

            await engine.dispose()
            return {
                "total_analyzed": total_analyzed,
                "to_delete": len(to_delete),
                "deleted": 0,
                "kept": kept_count,
                "avg_score_before": round(avg_score_analyzed, 2),
                "avg_score_after": round(avg_score_kept, 2),
                "by_source": {
                    src: {
                        "analyzed": by_source_analyzed[src],
                        "to_delete": by_source_to_delete.get(src, 0),
                    }
                    for src in sorted(by_source_analyzed)
                },
            }

        # Suppression en cascade par lots
        total_deleted = 0
        ids_to_delete = [entry["id"] for entry in to_delete]

        for batch_start in range(0, len(ids_to_delete), batch_size):
            batch_ids = ids_to_delete[batch_start : batch_start + batch_size]
            deleted_count = await _delete_recipes_cascade(session, batch_ids, dry_run=False)
            total_deleted += deleted_count
            logger.info(
                "batch_deleted",
                batch_deleted=deleted_count,
                total_deleted_so_far=total_deleted,
                remaining=len(ids_to_delete) - batch_start - len(batch_ids),
            )

        # Score moyen après nettoyage (recettes restantes)
        avg_score_after = await _get_avg_quality_score(session)
        counts_by_source_after = await _count_recipes_by_source(session)

        logger.info("=" * 60)
        logger.info("RAPPORT FINAL — NETTOYAGE TERMINÉ")
        logger.info(f"  Recettes analysées         : {total_analyzed}")
        logger.info(f"  Recettes supprimées        : {total_deleted}")
        logger.info(f"  Recettes conservées        : {kept_count}")
        logger.info(f"  Score moyen global avant   : {avg_score_before:.3f}")
        logger.info(f"  Score moyen global après   : {avg_score_after:.3f}")
        logger.info("  État final par source :")
        for src, count in sorted(counts_by_source_after.items()):
            logger.info(f"    {src}: {count} recettes")
        logger.info("=" * 60)

    await engine.dispose()

    return {
        "total_analyzed": total_analyzed,
        "to_delete": len(to_delete),
        "deleted": total_deleted,
        "kept": kept_count,
        "avg_score_before": round(avg_score_before, 3),
        "avg_score_after": round(avg_score_after, 3),
        "by_source": {
            src: {
                "analyzed": by_source_analyzed[src],
                "to_delete": by_source_to_delete.get(src, 0),
            }
            for src in sorted(by_source_analyzed)
        },
    }


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure loguru avec sortie console structurée."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> — {message}"
        ),
        serialize=False,
    )


def _validate_env() -> str:
    """Vérifie que DATABASE_URL est définie.

    Returns:
        L'URL de connexion à la base de données.

    Raises:
        SystemExit si la variable obligatoire est manquante.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "env_var_missing",
            missing="DATABASE_URL",
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
        )
        sys.exit(1)
    return db_url


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


async def main() -> None:
    """Point d'entrée CLI du script."""
    _configure_logging()
    database_url = _validate_env()

    quality_threshold = int(os.getenv("QUALITY_THRESHOLD", str(DEFAULT_QUALITY_THRESHOLD)))
    batch_size = int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    # DRY_RUN est "true" par défaut pour éviter les suppressions accidentelles.
    dry_run = os.getenv("DRY_RUN", "true").lower() != "false"

    if dry_run:
        logger.info(
            "mode_dry_run_actif",
            hint="Pour appliquer les suppressions, relancer avec DRY_RUN=false",
        )

    stats = await run_cleanup(
        database_url=database_url,
        quality_threshold=quality_threshold,
        batch_size=batch_size,
        dry_run=dry_run,
    )

    # Résumé final en console
    logger.info(
        "cleanup_summary",
        total_analyzed=stats["total_analyzed"],
        to_delete=stats["to_delete"],
        deleted=stats["deleted"],
        kept=stats["kept"],
        avg_score_before=stats["avg_score_before"],
        avg_score_after=stats["avg_score_after"],
        dry_run=dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())
