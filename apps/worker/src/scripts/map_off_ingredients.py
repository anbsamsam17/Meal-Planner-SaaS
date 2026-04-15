"""Mapping des ingrédients canoniques vers les produits Open Food Facts.

Pour chaque ingrédient sans `off_id` dans la table `ingredients`, interroge
l'API Open Food Facts, calcule un score de confiance composite, et met à jour
les colonnes OFF si le match est jugé suffisamment fiable.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... \\
    uv run python -m src.scripts.map_off_ingredients

Variables d'environnement :
    DATABASE_URL        Obligatoire — connexion PostgreSQL async (asyncpg).
    DRY_RUN             Optionnel — "true" pour simuler sans écriture (défaut : false).
    BATCH_SIZE          Optionnel — ingrédients par batch (défaut : 20).
    OFF_DELAY           Optionnel — délai entre requêtes OFF en secondes (défaut : 0.7).
    MIN_CONFIDENCE      Optionnel — seuil d'acceptation du match (défaut : 0.6).
    LOG_LEVEL           Optionnel — DEBUG/INFO/WARNING (défaut : INFO).
    SKIP_GENERICS       Optionnel — "true" pour ignorer les ingrédients génériques (défaut : true).
    FORCE_REFRESH       Optionnel — "true" pour re-mapper les ingrédients déjà mappés (défaut : false).
"""

import asyncio
import os
import sys
import time
from datetime import datetime, UTC
from typing import Any

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

# Ingrédients trop génériques pour un mapping produit drive pertinent.
# L'utilisateur choisira lui-même sa marque pour ces basiques.
GENERIC_SKIP_LIST: frozenset[str] = frozenset({
    "sel",
    "poivre",
    "eau",
    "huile",
    "huile d'olive",
    "beurre",
    "sucre",
    "farine",
    "oeuf",
    "lait",
    "crème",
    "vinaigre",
})

# Correspondances entre les catégories internes et les tags de catégories OFF.
# Utilisées pour le score de cohérence catégorie (+0.0 à +0.3).
CATEGORY_OFF_TAGS: dict[str, list[str]] = {
    "meat": ["meats", "poultry", "beef", "pork", "seafood", "fish"],
    "vegetable": ["vegetables", "legumes", "fresh-vegetables"],
    "fruit": ["fruits", "fresh-fruits"],
    "dairy": ["dairy", "cheeses", "yogurts", "milks"],
    "grain": ["cereals", "bread", "pasta", "rice", "grains"],
    "spice": ["spices", "condiments", "herbs"],
    "beverage": ["beverages", "juices", "waters"],
    "other": [],
}

# Seuil de scans OFF au-delà duquel un produit est considéré populaire.
POPULARITY_SCAN_THRESHOLD = 500


# ---------------------------------------------------------------------------
# Score de confiance
# ---------------------------------------------------------------------------


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Calcule le ratio de similarité entre deux chaînes via la distance de Levenshtein.

    Retourne un float entre 0.0 (aucune similarité) et 1.0 (identiques).
    Algorithme en O(m*n) — acceptable pour des chaînes courtes (noms de produits).
    """
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    # Matrice de programmation dynamique (optimisée sur 2 lignes)
    prev_row = list(range(len2 + 1))
    for i, char1 in enumerate(s1):
        curr_row = [i + 1]
        for j, char2 in enumerate(s2):
            insert_cost = curr_row[j] + 1
            delete_cost = prev_row[j + 1] + 1
            replace_cost = prev_row[j] + (0 if char1 == char2 else 1)
            curr_row.append(min(insert_cost, delete_cost, replace_cost))
        prev_row = curr_row

    distance = prev_row[len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


def _name_similarity_score(canonical_name: str, product_name: str) -> float:
    """Calcule le sous-score de similarité de nom, plafonné à 0.5.

    Stratégie :
    - Comparaison directe du nom canonique vs nom du produit.
    - Bonus si le nom canonique apparaît intégralement dans le nom du produit.
    """
    if not product_name:
        return 0.0

    # Normaliser les deux chaînes
    canonical = canonical_name.lower().strip()
    product = product_name.lower().strip()

    # Similarité Levenshtein directe
    ratio = _levenshtein_ratio(canonical, product)

    # Bonus de containment : si le canonique est un sous-mot du produit
    if canonical in product and len(canonical) >= 3:
        # Le produit contient exactement le terme canonique
        containment_bonus = min(0.2, len(canonical) / len(product))
        ratio = min(1.0, ratio + containment_bonus)

    # Plafonner à 0.5 (poids maximal de ce sous-score)
    return min(0.5, ratio * 0.5)


def _category_score(ingredient_category: str, product_categories_tags: list[str]) -> float:
    """Calcule le sous-score de cohérence catégorie, plafonné à 0.3.

    Compare la catégorie interne de l'ingrédient avec les tags de catégories OFF.
    """
    if not product_categories_tags or ingredient_category not in CATEGORY_OFF_TAGS:
        return 0.0

    expected_tags = CATEGORY_OFF_TAGS.get(ingredient_category, [])
    if not expected_tags:
        # Catégorie "other" — pas de pénalité, pas de bonus
        return 0.15

    product_tags_lower = [t.lower() for t in product_categories_tags]

    for expected_tag in expected_tags:
        for product_tag in product_tags_lower:
            if expected_tag in product_tag or product_tag in expected_tag:
                return 0.3

    return 0.0


def _popularity_score(product: dict[str, Any]) -> float:
    """Calcule le sous-score de popularité du produit, plafonné à 0.2.

    Basé sur le nombre de scans renseignés dans OFF (`unique_scans_n`).
    Un produit très scanné est plus susceptible d'avoir des données fiables.
    """
    scans = product.get("unique_scans_n") or 0
    if scans <= 0:
        return 0.0
    if scans >= POPULARITY_SCAN_THRESHOLD:
        return 0.2
    # Interpolation linéaire entre 0 et le seuil
    return round((scans / POPULARITY_SCAN_THRESHOLD) * 0.2, 3)


def compute_confidence(
    canonical_name: str,
    ingredient_category: str,
    product: dict[str, Any],
) -> float:
    """Calcule le score de confiance composite pour un produit OFF candidat.

    Score = sous-score_nom (0-0.5) + sous-score_catégorie (0-0.3) + sous-score_popularité (0-0.2)
    Score maximal théorique : 1.0

    Args:
        canonical_name:      Nom canonique de l'ingrédient (ex: "poulet").
        ingredient_category: Catégorie interne (ex: "meat").
        product:             Objet produit brut retourné par l'API OFF.

    Returns:
        Float entre 0.0 et 1.0.
    """
    product_name = product.get("product_name") or product.get("product_name_fr") or ""
    categories_tags = product.get("categories_tags") or []

    name_score = _name_similarity_score(canonical_name, product_name)
    cat_score = _category_score(ingredient_category, categories_tags)
    pop_score = _popularity_score(product)

    total = name_score + cat_score + pop_score
    return round(min(1.0, total), 4)


def _best_product(
    candidates: list[dict[str, Any]],
    canonical_name: str,
    ingredient_category: str,
) -> tuple[dict[str, Any] | None, float]:
    """Sélectionne le meilleur produit parmi les candidats OFF.

    Returns:
        Tuple (product, confidence). product est None si la liste est vide.
    """
    if not candidates:
        return None, 0.0

    best: dict[str, Any] | None = None
    best_score = -1.0

    for product in candidates:
        score = compute_confidence(canonical_name, ingredient_category, product)
        if score > best_score:
            best_score = score
            best = product

    return best, best_score


# ---------------------------------------------------------------------------
# Client HTTP Open Food Facts
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _off_search(
    client: httpx.AsyncClient,
    search_terms: str,
    page_size: int = 5,
) -> list[dict[str, Any]]:
    """Interroge l'API de recherche OFF avec retry sur erreurs réseau.

    Retourne la liste brute des produits (jusqu'à page_size résultats).
    Ne lève pas d'exception sur réponse vide ou résultat nul.
    """
    params = {
        "search_terms": search_terms,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": str(page_size),
        "lc": "fr",
        "cc": "fr",
    }

    logger.debug("off_search_request", terms=search_terms)
    response = await client.get(OFF_SEARCH_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    products = data.get("products") or []
    logger.debug("off_search_response", terms=search_terms, count=len(products))
    return products


# ---------------------------------------------------------------------------
# Accès à la base de données
# ---------------------------------------------------------------------------


async def _fetch_ingredients_to_map(
    session: Any,
    batch_size: int,
    force_refresh: bool,
    offset: int,
) -> list[dict[str, Any]]:
    """Récupère un batch d'ingrédients à mapper depuis la base de données.

    Sans force_refresh : ne récupère que les ingrédients sans off_id ET
    sans tentative précédente (off_last_checked_at IS NULL).
    Avec force_refresh : récupère tous les ingrédients.

    Returns:
        Liste de dicts avec les clés : id, canonical_name, category.
    """
    from sqlalchemy import text

    if force_refresh:
        query = text(
            """
            SELECT id, canonical_name, category
            FROM ingredients
            ORDER BY canonical_name
            LIMIT :limit OFFSET :offset
            """
        )
    else:
        query = text(
            """
            SELECT id, canonical_name, category
            FROM ingredients
            WHERE off_last_checked_at IS NULL
            ORDER BY canonical_name
            LIMIT :limit OFFSET :offset
            """
        )

    result = await session.execute(query, {"limit": batch_size, "offset": offset})
    rows = result.fetchall()
    return [
        {"id": str(row[0]), "canonical_name": row[1], "category": row[2]}
        for row in rows
    ]


async def _count_ingredients(session: Any, force_refresh: bool) -> dict[str, int]:
    """Retourne les compteurs globaux pour le rapport initial.

    Returns:
        Dict avec les clés : total, already_mapped, to_map.
    """
    from sqlalchemy import text

    total_result = await session.execute(text("SELECT COUNT(*) FROM ingredients"))
    total = total_result.scalar() or 0

    mapped_result = await session.execute(
        text("SELECT COUNT(*) FROM ingredients WHERE off_id IS NOT NULL")
    )
    already_mapped = mapped_result.scalar() or 0

    if force_refresh:
        to_map = total
    else:
        to_map_result = await session.execute(
            text("SELECT COUNT(*) FROM ingredients WHERE off_last_checked_at IS NULL")
        )
        to_map = to_map_result.scalar() or 0

    return {
        "total": int(total),
        "already_mapped": int(already_mapped),
        "to_map": int(to_map),
    }


async def _update_ingredient_off(
    session: Any,
    ingredient_id: str,
    off_id: str | None,
    off_product_name: str | None,
    off_brand: str | None,
    off_match_confidence: float,
    dry_run: bool,
) -> None:
    """Met à jour les colonnes OFF d'un ingrédient.

    Toujours met à jour off_last_checked_at et off_match_confidence,
    même si aucun produit n'a été trouvé (pour éviter de re-tenter à chaque run).
    """
    if dry_run:
        logger.info(
            "[DRY_RUN] would_update_ingredient",
            ingredient_id=ingredient_id,
            off_id=off_id,
            off_product_name=off_product_name,
            off_match_confidence=off_match_confidence,
        )
        return

    from sqlalchemy import text

    await session.execute(
        text(
            """
            UPDATE ingredients
            SET
                off_id                 = :off_id,
                off_product_name       = :off_product_name,
                off_brand              = :off_brand,
                off_match_confidence   = :off_match_confidence,
                off_last_checked_at    = NOW()
            WHERE id = :ingredient_id
            """
        ),
        {
            "ingredient_id": ingredient_id,
            "off_id": off_id,
            "off_product_name": off_product_name,
            "off_brand": off_brand,
            "off_match_confidence": off_match_confidence,
        },
    )
    await session.commit()


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
        La valeur de DATABASE_URL.

    Raises:
        SystemExit si la variable obligatoire est manquante.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "env_var_missing",
            missing=["DATABASE_URL"],
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
        )
        sys.exit(1)
    return db_url


def _print_report(stats: dict[str, Any]) -> None:
    """Affiche le rapport final de mapping au format structuré."""
    total = stats["total"]
    already_mapped = stats["already_mapped"]
    to_map = stats["to_map"]
    skipped_generics = stats["skipped_generics"]
    mapped_success = stats["mapped_success"]
    high_confidence = stats["high_confidence"]
    medium_confidence = stats["medium_confidence"]
    failures = stats["failures"]

    success_pct = (
        round(mapped_success / to_map * 100, 1) if to_map > 0 else 0.0
    )

    logger.info("=" * 50)
    logger.info("=== Open Food Facts Mapping Report ===")
    logger.info(f"Total ingrédients:        {total}")
    logger.info(f"Déjà mappés:              {already_mapped}")
    logger.info(f"À mapper:                 {to_map}")
    logger.info(f"Ignorés (génériques):     {skipped_generics}")
    logger.info(f"Mappés avec succès:       {mapped_success} ({success_pct}%)")
    logger.info(f"  - Haute confiance (>0.8): {high_confidence}")
    logger.info(f"  - Moyenne confiance:      {medium_confidence}")
    logger.info(f"Échecs:                   {failures}")
    logger.info("=" * 50)


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


async def run_mapping(
    database_url: str,
    dry_run: bool = False,
    batch_size: int = 20,
    off_delay: float = 0.7,
    min_confidence: float = 0.6,
    skip_generics: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Orchestre le mapping complet ingredients → Open Food Facts.

    Appelable directement depuis une tâche Celery (await run_mapping(...)).

    Returns:
        Dict de statistiques : total, already_mapped, to_map, skipped_generics,
        mapped_success, high_confidence, medium_confidence, failures.
    """
    logger.info(
        "off_mapping_start",
        dry_run=dry_run,
        batch_size=batch_size,
        off_delay=off_delay,
        min_confidence=min_confidence,
        skip_generics=skip_generics,
        force_refresh=force_refresh,
    )

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Initialisation des compteurs de rapport
    stats: dict[str, Any] = {
        "total": 0,
        "already_mapped": 0,
        "to_map": 0,
        "skipped_generics": 0,
        "mapped_success": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "failures": 0,
    }

    async with session_factory() as session:
        # Compteurs initiaux pour le rapport
        counts = await _count_ingredients(session, force_refresh)
        stats.update(counts)

        logger.info(
            "off_mapping_counts",
            total=counts["total"],
            already_mapped=counts["already_mapped"],
            to_map=counts["to_map"],
        )

        async with httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "User-Agent": "PrestoBot/1.0 (MealPlanner SaaS; contact: contact@presto.fr)",
            }
        ) as http_client:
            offset = 0
            processed_ids: set[str] = set()

            while True:
                # Récupérer le prochain batch
                batch = await _fetch_ingredients_to_map(
                    session, batch_size, force_refresh, offset
                )
                if not batch:
                    logger.info("off_mapping_no_more_batches", offset=offset)
                    break

                logger.info(
                    "off_mapping_batch_start",
                    offset=offset,
                    batch_count=len(batch),
                )

                for ingredient in batch:
                    ingredient_id = ingredient["id"]
                    canonical_name = ingredient["canonical_name"]
                    category = ingredient["category"]

                    # Éviter les doublons dans la même session (sécurité)
                    if ingredient_id in processed_ids:
                        continue
                    processed_ids.add(ingredient_id)

                    # Ignorer les ingrédients génériques si SKIP_GENERICS
                    if skip_generics and canonical_name in GENERIC_SKIP_LIST:
                        logger.debug(
                            "off_ingredient_skipped_generic",
                            canonical_name=canonical_name,
                        )
                        stats["skipped_generics"] += 1
                        # Marquer comme vérifié pour ne pas re-tenter
                        await _update_ingredient_off(
                            session,
                            ingredient_id,
                            off_id=None,
                            off_product_name=None,
                            off_brand=None,
                            off_match_confidence=0.0,
                            dry_run=dry_run,
                        )
                        continue

                    # Recherche OFF
                    try:
                        candidates = await _off_search(http_client, canonical_name)
                    except httpx.HTTPStatusError as exc:
                        logger.warning(
                            "off_search_http_error",
                            canonical_name=canonical_name,
                            status_code=exc.response.status_code,
                        )
                        stats["failures"] += 1
                        await asyncio.sleep(off_delay * 2)
                        continue
                    except (httpx.ConnectError, httpx.TimeoutException) as exc:
                        logger.error(
                            "off_search_network_error",
                            canonical_name=canonical_name,
                            error=str(exc),
                        )
                        stats["failures"] += 1
                        await asyncio.sleep(off_delay * 2)
                        continue
                    except Exception as exc:
                        logger.error(
                            "off_search_unexpected_error",
                            canonical_name=canonical_name,
                            error=str(exc),
                        )
                        stats["failures"] += 1
                        await asyncio.sleep(off_delay)
                        continue

                    # Sélection du meilleur candidat
                    best_product, confidence = _best_product(
                        candidates, canonical_name, category
                    )

                    if best_product is None:
                        # Aucun résultat : enregistrer confiance 0 pour ne pas re-tenter
                        logger.debug(
                            "off_no_results",
                            canonical_name=canonical_name,
                        )
                        await _update_ingredient_off(
                            session,
                            ingredient_id,
                            off_id=None,
                            off_product_name=None,
                            off_brand=None,
                            off_match_confidence=0.0,
                            dry_run=dry_run,
                        )
                        stats["failures"] += 1

                    else:
                        # Extraire les champs du produit retenu
                        off_id = best_product.get("code") or None
                        off_product_name = (
                            best_product.get("product_name_fr")
                            or best_product.get("product_name")
                            or None
                        )
                        off_brand = best_product.get("brands") or None

                        # Tronquer les champs texte pour correspondre aux contraintes DB
                        if off_product_name:
                            off_product_name = off_product_name[:200]
                        if off_brand:
                            off_brand = off_brand[:100]

                        logger.info(
                            "off_match_found",
                            canonical_name=canonical_name,
                            off_id=off_id,
                            off_product_name=off_product_name,
                            confidence=confidence,
                            accepted=confidence >= min_confidence,
                        )

                        # Enregistrer le résultat qu'il soit au-dessus ou sous le seuil
                        # (la confiance permet à l'utilisateur de décider manuellement)
                        await _update_ingredient_off(
                            session,
                            ingredient_id,
                            off_id=off_id if confidence >= min_confidence else None,
                            off_product_name=off_product_name,
                            off_brand=off_brand,
                            off_match_confidence=confidence,
                            dry_run=dry_run,
                        )

                        if confidence >= min_confidence:
                            stats["mapped_success"] += 1
                            if confidence > 0.8:
                                stats["high_confidence"] += 1
                            else:
                                stats["medium_confidence"] += 1
                        else:
                            # Confiance insuffisante — compté comme échec de mapping
                            stats["failures"] += 1

                    # Respect du rate limiting OFF (100 req/min recommandé)
                    await asyncio.sleep(off_delay)

                offset += batch_size

                # Log de progression toutes les N entrées
                logger.info(
                    "off_mapping_progress",
                    processed=len(processed_ids),
                    mapped_success=stats["mapped_success"],
                    failures=stats["failures"],
                    skipped_generics=stats["skipped_generics"],
                )

    await engine.dispose()

    _print_report(stats)
    return stats


async def main() -> None:
    """Point d'entrée CLI du script."""
    _configure_logging()
    database_url = _validate_env()

    dry_run = os.getenv("DRY_RUN", "").lower() == "true"
    batch_size = int(os.getenv("BATCH_SIZE", "20"))
    off_delay = float(os.getenv("OFF_DELAY", "0.7"))
    min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.6"))
    skip_generics = os.getenv("SKIP_GENERICS", "true").lower() != "false"
    force_refresh = os.getenv("FORCE_REFRESH", "").lower() == "true"

    stats = await run_mapping(
        database_url=database_url,
        dry_run=dry_run,
        batch_size=batch_size,
        off_delay=off_delay,
        min_confidence=min_confidence,
        skip_generics=skip_generics,
        force_refresh=force_refresh,
    )

    # Sortie non-zéro si tous les ingrédients à mapper ont échoué
    if stats["to_map"] > 0 and stats["mapped_success"] == 0 and stats["failures"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
