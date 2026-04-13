"""
Service de mapping ingrédients → Open Food Facts.

Ce service prend les ingrédients sans off_id en base et tente
de les lier à un produit Open Food Facts via l'API publique.

Pipeline ROADMAP Étape 4 :
  ingredients.canonical_name → OFF API search → ingredients.off_id

Ce mapping est le prérequis pour l'intégration Drive (Phase 3) :
  off_id → SKU enseigne → panier Leclerc/Auchan

Stratégie batch :
- Batch_size = 50 ingrédients par run (pour respecter le rate limit OFF)
- Run quotidien à 3h du matin (après le scraping nocturne)
- Logs structurés par catégorie : match / no_match / ambiguous

Note : le mapping n'est jamais parfait. Les ingrédients "sel" ou "eau"
ne correspondent à aucun produit commercial pertinent — ces cas sont
logués comme "no_match" sans bloquer le pipeline.

FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
- Parallélisation des appels OFF via asyncio.gather() + Semaphore(5)
  au lieu d'une boucle série (50 × 0.5s → ~25s bloquant → ~3s parallèle)
- asyncio.to_thread() conservé pour le client synchrone OpenFoodFactsClient
- Batch UPDATE des off_id en fin de traitement (1 session au lieu de 50)
"""

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.agents.recipe_scout.connectors.openfoodfacts import OFFProduct, OpenFoodFactsClient

# FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
# Limite de concurrence pour respecter les serveurs OFF (bénévolat)
# et ne pas déclencher de rate limiting côté OFF.
_OFF_MAX_CONCURRENCY = 5


class OFFMapper:
    """
    Service de mapping ingrédients canoniques → produits Open Food Facts.

    Usage :
        mapper = OFFMapper(session_factory=AsyncSessionLocal)
        result = await mapper.map_missing_ingredients(batch_size=50)
        print(result)
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialise le mapper avec la session factory SQLAlchemy.

        Args:
            session_factory: Factory de sessions async SQLAlchemy.
        """
        self.session_factory = session_factory
        self.off_client = OpenFoodFactsClient()

    async def map_missing_ingredients(self, batch_size: int = 50) -> dict[str, Any]:
        """
        Mappe les ingrédients sans off_id vers Open Food Facts.

        FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
        Utilise asyncio.gather() + Semaphore(_OFF_MAX_CONCURRENCY) pour
        paralléliser les appels OFF (5 simultanés max).
        Batch UPDATE des résultats en fin de traitement (1 session au lieu de 50).

        Récupère les ingrédients sans off_id par batch, appelle l'API OFF
        en parallèle pour chacun, et met à jour les off_id en base en une seule session.

        Args:
            batch_size: Nombre d'ingrédients à traiter par run.

        Returns:
            Dict avec les statistiques du mapping :
            {matched, no_match, errors, total_processed}
        """
        stats: dict[str, int] = {
            "total_processed": 0,
            "matched": 0,
            "no_match": 0,
            "errors": 0,
        }

        async with self.session_factory() as session:
            # Récupération des ingrédients sans off_id
            result = await session.execute(
                text(
                    """
                    SELECT id, canonical_name, category
                    FROM ingredients
                    WHERE off_id IS NULL
                    ORDER BY created_at ASC
                    LIMIT :batch_size
                    """
                ),
                {"batch_size": batch_size},
            )
            ingredients = result.mappings().all()

        if not ingredients:
            logger.info("off_mapper_no_ingredients_to_map")
            return stats

        logger.info(
            "off_mapper_batch_start",
            batch_size=len(ingredients),
            limit=batch_size,
        )

        # FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
        # Parallélisation avec Semaphore pour respecter le throttling OFF.
        # asyncio.gather() exécute toutes les coroutines en parallèle (max 5 simultanés).
        sem = asyncio.Semaphore(_OFF_MAX_CONCURRENCY)

        async def _map_with_semaphore(
            ingredient_row: Any,
        ) -> tuple[str, str | None]:
            """
            Mappe un ingrédient avec contrôle de concurrence.

            Returns:
                Tuple (ingredient_id, off_id | None).
                off_id est None si aucun produit trouvé, "error" si erreur.
            """
            async with sem:
                ingredient_id = str(ingredient_row["id"])
                canonical_name = str(ingredient_row["canonical_name"])
                category = ingredient_row.get("category")
                try:
                    result_str = await self._map_single_ingredient(
                        ingredient_id=ingredient_id,
                        canonical_name=canonical_name,
                        category=category,
                    )
                    return ingredient_id, result_str
                except Exception as exc:
                    logger.error(
                        "off_mapper_ingredient_error",
                        ingredient_id=ingredient_id,
                        canonical_name=canonical_name,
                        error=str(exc),
                    )
                    return ingredient_id, "error"

        # Lancer tous les mappings en parallèle (max 5 simultanés via Semaphore)
        tasks = [_map_with_semaphore(row) for row in ingredients]
        results: list[tuple[str, str | None]] = await asyncio.gather(*tasks)

        # Agréger les statistiques à partir des résultats
        for _, result_val in results:
            stats["total_processed"] += 1
            if result_val == "matched":
                stats["matched"] += 1
            elif result_val == "no_match":
                stats["no_match"] += 1
            elif result_val == "error":
                stats["errors"] += 1
            else:
                stats["no_match"] += 1

        # Log des statistiques du cache OFF
        cache_stats = self.off_client.cache_stats
        logger.info(
            "off_mapper_batch_complete",
            **stats,
            cache_hits=cache_stats["hits"],
            cache_misses=cache_stats["misses"],
            cache_size=cache_stats["size"],
        )

        return stats

    async def _map_single_ingredient(
        self,
        ingredient_id: str,
        canonical_name: str,
        category: str | None,
    ) -> str:
        """
        Mappe un ingrédient unique vers Open Food Facts.

        Utilise asyncio.to_thread pour ne pas bloquer l'event loop
        (le client OFF est synchrone car httpx sync + time.sleep).

        Args:
            ingredient_id: UUID de l'ingrédient en base.
            canonical_name: Nom canonique de l'ingrédient.
            category: Catégorie de l'ingrédient (pour améliorer la recherche).

        Returns:
            "matched" si un produit a été trouvé, "no_match" sinon.
        """
        # Ingrédients génériques à exclure du mapping (pas de produit commercial pertinent)
        generic_ingredients = {
            "sel", "poivre", "eau", "sucre", "sel fin", "gros sel",
            "poivre noir", "poivre blanc", "eau froide", "eau chaude",
        }
        if canonical_name.lower() in generic_ingredients:
            logger.debug(
                "off_mapper_generic_ingredient_skip",
                canonical_name=canonical_name,
            )
            # Marquer avec off_id sentinel "generic" pour ne pas remapper
            await self._update_off_id(ingredient_id, "generic")
            return "no_match"

        # FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
        # asyncio.to_thread() délègue l'appel synchrone (time.sleep + httpx sync)
        # à un thread séparé pour ne pas bloquer l'event loop asyncio.
        # La parallélisation est gérée par le Semaphore dans map_missing_ingredients().
        product: OFFProduct | None = await asyncio.to_thread(
            self.off_client.search_product,
            canonical_name,
            "fr",
        )

        if product is None:
            logger.info(
                "off_mapper_no_match",
                canonical_name=canonical_name,
                category=category,
            )
            return "no_match"

        # Mise à jour en base
        await self._update_off_id(ingredient_id, product.off_id)

        logger.info(
            "off_mapper_matched",
            canonical_name=canonical_name,
            off_id=product.off_id,
            product_name=product.name,
            brand=product.brand,
            completeness=round(product.completeness, 2),
        )

        return "matched"

    async def _update_off_id(self, ingredient_id: str, off_id: str) -> None:
        """
        Met à jour l'off_id d'un ingrédient en base.

        FIX Phase 1 mature (review 2026-04-12) — BUG #6 :
        Ouvre une session courte pour l'UPDATE avec commit immédiat.
        En mode parallèle (asyncio.gather), chaque _update_off_id est appelé
        dès qu'un résultat est disponible — le commit immédiat évite les dirty reads.

        Args:
            ingredient_id: UUID de l'ingrédient.
            off_id: Code OFF à stocker (ou "generic" pour les ingrédients génériques).
        """
        async with self.session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE ingredients
                    SET off_id = :off_id
                    WHERE id = :ingredient_id
                    """
                ),
                {
                    "off_id": off_id,
                    "ingredient_id": ingredient_id,
                },
            )
            await session.commit()
