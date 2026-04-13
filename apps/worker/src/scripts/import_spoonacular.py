"""Import de recettes depuis l'API Spoonacular vers PostgreSQL Supabase.

Récupère des recettes par cuisine et par régime alimentaire, normalise les
données pour correspondre au schéma DB (recipes / ingredients / recipe_ingredients),
puis insère via upsert avec gestion des doublons.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... SPOONACULAR_API_KEY=... \\
    uv run python -m src.scripts.import_spoonacular

Variables d'environnement :
    DATABASE_URL            Obligatoire — connexion PostgreSQL async (asyncpg).
    SPOONACULAR_API_KEY     Obligatoire — clé API Spoonacular (free tier 150 req/jour).
    MAX_RECIPES             Optionnel — nombre max de recettes à importer (défaut : 50).
    CUISINES                Optionnel — liste de cuisines séparées par virgule
                            (défaut : toutes les cuisines prédéfinies).
    DRY_RUN                 Optionnel — "true" pour simuler sans écriture en base.
    LOG_LEVEL               Optionnel — DEBUG/INFO/WARNING (défaut : INFO).
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SPOONACULAR_BASE = "https://api.spoonacular.com"
SPOONACULAR_DAILY_LIMIT = 150

# Compteur de requêtes en mémoire — réinitialisé à chaque exécution du script.
# Pour la tâche Celery (longue durée), le compteur du SpoonacularClient existant
# dans apps/worker/src/agents/recipe_scout/connectors/spoonacular.py persiste.
_request_count = 0

CUISINES_DEFAULT: list[str] = [
    "french",
    "italian",
    "japanese",
    "mexican",
    "indian",
    "thai",
    "mediterranean",
    "chinese",
    "korean",
    "vietnamese",
]

# Catégorie par défaut pour les ingrédients Spoonacular (champ obligatoire en DB).
# La table ingredients a une colonne category NOT NULL — "other" est la valeur de repli.
INGREDIENT_CATEGORY_DEFAULT = "other"

# Score de qualité par défaut pour les imports API Spoonacular (données vérifiées par Spoonacular).
QUALITY_SCORE_DEFAULT = 0.80


# ---------------------------------------------------------------------------
# Helpers de mapping Spoonacular → schéma DB
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Retire les balises HTML d'une chaîne et normalise les espaces."""
    clean = re.sub(r"<[^>]+>", "", text)
    # Normaliser les entités HTML les plus courantes
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    clean = clean.replace("&nbsp;", " ").replace("&eacute;", "é").replace("&egrave;", "è")
    return " ".join(clean.split()).strip()


def _slugify(text: str) -> str:
    """Convertit un titre en slug URL-safe.

    Exemple : "Poulet rôti à l'ail" → "poulet-roti-a-l-ail"
    """
    slug = text.lower()
    # Remplacer les caractères accentués communs
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "ô": "o", "ö": "o",
        "î": "i", "ï": "i",
        "ç": "c", "œ": "oe", "æ": "ae",
    }
    for char, replacement in replacements.items():
        slug = slug.replace(char, replacement)
    # Remplacer tout ce qui n'est pas alphanumérique par des tirets
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def map_difficulty(recipe: dict[str, Any]) -> int:
    """Calcule un niveau de difficulté 1-5 basé sur le temps et le nombre d'étapes.

    Échelle :
        1 = très facile  (≤ 15 min et ≤ 3 étapes)
        2 = facile       (≤ 30 min et ≤ 5 étapes)
        3 = moyen        (≤ 60 min)
        4 = difficile    (≤ 120 min)
        5 = très difficile (> 120 min)
    """
    time_min = recipe.get("readyInMinutes") or 30
    steps_count = 0
    analyzed = recipe.get("analyzedInstructions") or []
    if analyzed:
        steps_count = len(analyzed[0].get("steps") or [])

    if time_min <= 15 and steps_count <= 3:
        return 1
    if time_min <= 30 and steps_count <= 5:
        return 2
    if time_min <= 60:
        return 3
    if time_min <= 120:
        return 4
    return 5


def map_cuisine(cuisines: list[str]) -> str:
    """Traduit les noms de cuisine Spoonacular (anglais) en français."""
    mapping: dict[str, str] = {
        "French": "française",
        "Italian": "italienne",
        "Japanese": "japonaise",
        "Mexican": "mexicaine",
        "Indian": "indienne",
        "Thai": "thaïlandaise",
        "Chinese": "chinoise",
        "Mediterranean": "méditerranéenne",
        "Korean": "coréenne",
        "Vietnamese": "vietnamienne",
        "American": "américaine",
        "Greek": "grecque",
        "Spanish": "espagnole",
        "Lebanese": "libanaise",
        "Moroccan": "marocaine",
        "Middle Eastern": "moyen-orientale",
        "European": "européenne",
        "Eastern European": "est-européenne",
        "German": "allemande",
        "British": "britannique",
        "Cajun": "cajun",
        "Caribbean": "caraïbéenne",
    }
    for cuisine in cuisines:
        if cuisine in mapping:
            return mapping[cuisine]
    return "internationale"


def extract_tags(recipe: dict[str, Any]) -> list[str]:
    """Extrait les tags sémantiques depuis les métadonnées Spoonacular.

    Tags extraits : régimes alimentaires, durée, type de plat, label santé.
    """
    tags: list[str] = []

    if recipe.get("vegetarian"):
        tags.append("végétarien")
    if recipe.get("vegan"):
        tags.append("vegan")
    if recipe.get("glutenFree"):
        tags.append("sans-gluten")
    if recipe.get("dairyFree"):
        tags.append("sans-lactose")
    if recipe.get("veryHealthy"):
        tags.append("healthy")
    if recipe.get("cheap"):
        tags.append("économique")

    ready_in = recipe.get("readyInMinutes") or 60
    if ready_in <= 15:
        tags.append("express")
    elif ready_in <= 30:
        tags.append("rapide")

    for dish_type in recipe.get("dishTypes") or []:
        if dish_type in ("main course", "dinner", "lunch"):
            tags.append("plat")
        elif dish_type == "dessert":
            tags.append("dessert")
        elif dish_type in ("appetizer", "starter", "antipasti", "antipasto"):
            tags.append("entrée")
        elif dish_type == "breakfast":
            tags.append("petit-déjeuner")
        elif dish_type == "soup":
            tags.append("soupe")
        elif dish_type == "salad":
            tags.append("salade")

    return list(set(tags))


def extract_instructions(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Convertit les instructions Spoonacular au format JSONB interne.

    Format cible : [{"step": 1, "text": "..."}, ...]
    Limite à 10 étapes pour garder le JSON lisible.
    Fallback sur les instructions HTML brutes si les instructions analysées sont absentes.
    """
    instructions: list[dict[str, Any]] = []

    for section in recipe.get("analyzedInstructions") or []:
        for step in section.get("steps") or []:
            text = (step.get("step") or "").strip()
            if text:
                instructions.append({"step": step["number"], "text": text})

    if not instructions:
        raw_html = recipe.get("instructions") or ""
        if raw_html:
            clean_text = _strip_html(raw_html)
            # Découper sur les points terminaux ou les retours à la ligne
            sentences = re.split(r"\.\s+|\n", clean_text)
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip(" .")
                if sentence:
                    instructions.append({"step": i + 1, "text": sentence})

    return instructions[:10]


def _parse_ingredient_quantity(ingredient: dict[str, Any]) -> tuple[float, str, str]:
    """Extrait la quantité, l'unité et le nom canonique d'un ingrédient Spoonacular.

    Returns:
        Tuple (quantity, unit, canonical_name).
        quantity >= 0.001 (contrainte DB : quantity > 0).
        unit : chaîne non vide ("unité" si ingrédient sans unité explicite).
    """
    measures = ingredient.get("measures") or {}
    metric = measures.get("metric") or {}

    quantity = float(metric.get("amount") or ingredient.get("amount") or 1.0)
    unit = (metric.get("unitShort") or metric.get("unitLong") or ingredient.get("unit") or "").strip()

    if not unit:
        unit = "unité"

    # La contrainte DB exige quantity > 0
    if quantity <= 0:
        quantity = 1.0

    # Nom canonique : utiliser nameClean si disponible, sinon name
    canonical_name = (ingredient.get("nameClean") or ingredient.get("name") or "").strip().lower()
    if not canonical_name:
        canonical_name = "ingrédient inconnu"

    return quantity, unit, canonical_name


def normalize_recipe(spoon_recipe: dict[str, Any]) -> dict[str, Any]:
    """Normalise une recette Spoonacular vers le schéma DB interne.

    Ne lève jamais d'exception — les champs manquants sont remplacés par des valeurs
    par défaut sécurisées.

    Returns:
        Dict prêt pour l'insertion dans la table recipes.
    """
    title = (spoon_recipe.get("title") or "Recette sans titre").strip()
    slug_base = _slugify(title)
    # Ajouter l'ID Spoonacular au slug pour garantir l'unicité
    spoon_id = spoon_recipe.get("id") or ""
    slug = f"{slug_base}-{spoon_id}" if spoon_id else slug_base

    description_html = spoon_recipe.get("summary") or ""
    description = _strip_html(description_html)[:500]

    prep_time = int(spoon_recipe.get("preparationMinutes") or 0)
    cook_time = int(spoon_recipe.get("cookingMinutes") or spoon_recipe.get("readyInMinutes") or 30)
    # Éviter les valeurs négatives (Spoonacular renvoie parfois -1)
    prep_time = max(0, prep_time)
    cook_time = max(0, cook_time)

    return {
        "title": title,
        "slug": slug,
        "source": "spoonacular",
        "source_url": spoon_recipe.get("sourceUrl") or "",
        "description": description,
        "photo_url": spoon_recipe.get("image") or "",
        "servings": max(1, int(spoon_recipe.get("servings") or 4)),
        "prep_time_min": prep_time,
        "cook_time_min": cook_time,
        "difficulty": map_difficulty(spoon_recipe),
        "cuisine_type": map_cuisine(spoon_recipe.get("cuisines") or []),
        "tags": extract_tags(spoon_recipe),
        "quality_score": QUALITY_SCORE_DEFAULT,
        "instructions": extract_instructions(spoon_recipe),
    }


# ---------------------------------------------------------------------------
# Client HTTP Spoonacular (léger, sans tenacity pour conserver la lisibilité)
# ---------------------------------------------------------------------------


def _check_quota() -> None:
    """Lève une exception si la limite quotidienne locale est dépassée.

    Note : ce compteur est local au processus. Le client SpoonacularClient dans
    connectors/spoonacular.py maintient son propre compteur pour le pipeline agent.
    """
    global _request_count
    if _request_count >= SPOONACULAR_DAILY_LIMIT:
        raise RuntimeError(
            f"Limite locale Spoonacular atteinte : {_request_count}/{SPOONACULAR_DAILY_LIMIT} req/jour. "
            "Relancer demain."
        )
    if _request_count >= int(SPOONACULAR_DAILY_LIMIT * 0.8):
        logger.warning(
            "spoonacular_quota_approaching",
            request_count=_request_count,
            limit=SPOONACULAR_DAILY_LIMIT,
            percent=round(_request_count / SPOONACULAR_DAILY_LIMIT * 100),
        )


async def _api_get(
    client: httpx.AsyncClient,
    api_key: str,
    endpoint: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Effectue une requête GET Spoonacular avec gestion du quota et des erreurs HTTP.

    Incrémente le compteur local à chaque appel réussi.
    Lève httpx.HTTPStatusError pour les codes 4xx/5xx.
    """
    global _request_count
    _check_quota()

    all_params = {"apiKey": api_key, **params}
    logger.debug("spoonacular_get", endpoint=endpoint, request_count=_request_count)

    response = await client.get(f"{SPOONACULAR_BASE}{endpoint}", params=all_params, timeout=30)

    if response.status_code == 402:
        raise RuntimeError(
            "Quota Spoonacular dépassé (HTTP 402). Réessayer demain."
        )
    if response.status_code == 401:
        raise ValueError(
            "Clé SPOONACULAR_API_KEY invalide (HTTP 401). Vérifier la variable d'environnement."
        )

    response.raise_for_status()
    _request_count += 1
    return response.json()


async def fetch_recipes_by_cuisine(
    client: httpx.AsyncClient,
    api_key: str,
    cuisine: str,
    number: int = 10,
) -> list[dict[str, Any]]:
    """Récupère des recettes Spoonacular pour une cuisine donnée.

    Utilise complexSearch avec addRecipeInformation=True pour éviter un second
    appel de détail par recette (économie de quota).
    """
    data = await _api_get(client, api_key, "/recipes/complexSearch", {
        "cuisine": cuisine,
        "number": min(number, 100),
        "addRecipeInformation": True,
        "fillIngredients": True,
        "instructionsRequired": True,
        "sort": "popularity",
    })
    results = data.get("results") or []
    logger.info(
        "spoonacular_cuisine_fetched",
        cuisine=cuisine,
        count=len(results),
        total_results=data.get("totalResults", 0),
    )
    return results


async def fetch_random_recipes(
    client: httpx.AsyncClient,
    api_key: str,
    number: int = 10,
    tags: str = "",
) -> list[dict[str, Any]]:
    """Récupère des recettes aléatoires, optionnellement filtrées par tag de régime."""
    params: dict[str, Any] = {"number": min(number, 100)}
    if tags:
        params["tags"] = tags

    data = await _api_get(client, api_key, "/recipes/random", params)
    results = data.get("recipes") or []
    logger.info(
        "spoonacular_random_fetched",
        tags=tags or "none",
        count=len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Insertion en base de données
# ---------------------------------------------------------------------------


async def _upsert_ingredient(
    session: Any,
    canonical_name: str,
) -> str:
    """Insère ou récupère un ingrédient canonique.

    Utilise ON CONFLICT DO NOTHING + SELECT pour gérer les races conditions.
    La colonne `category` est NOT NULL en base : la valeur par défaut "other" est utilisée.

    Returns:
        UUID de l'ingrédient sous forme de chaîne.
    """
    from sqlalchemy import text

    # Tenter l'insertion — ignorée si le nom canonique existe déjà
    ingredient_id = str(uuid4())
    await session.execute(
        text(
            """
            INSERT INTO ingredients (id, canonical_name, category, created_at)
            VALUES (:id, :name, :category, NOW())
            ON CONFLICT (canonical_name) DO NOTHING
            """
        ),
        {
            "id": ingredient_id,
            "name": canonical_name,
            "category": INGREDIENT_CATEGORY_DEFAULT,
        },
    )

    # Récupérer l'ID réel (que ce soit le nôtre ou celui d'un doublon existant)
    result = await session.execute(
        text("SELECT id FROM ingredients WHERE canonical_name = :name LIMIT 1"),
        {"name": canonical_name},
    )
    row = result.fetchone()
    if row is None:
        # Ne devrait pas arriver, mais on se protège
        raise RuntimeError(f"Impossible de retrouver l'ingrédient après INSERT : {canonical_name!r}")

    return str(row[0])


async def _insert_recipe_with_ingredients(
    session: Any,
    recipe_data: dict[str, Any],
    ingredients_raw: list[dict[str, Any]],
    dry_run: bool,
) -> bool:
    """Insère une recette et ses ingrédients dans la base de données.

    Stratégie :
    - Vérifier le doublon par source_url OU slug avant d'insérer.
    - INSERT recipes ON CONFLICT (slug) DO NOTHING.
    - Pour chaque ingrédient Spoonacular, upsert dans ingredients, puis INSERT recipe_ingredients.

    Returns:
        True si la recette a été insérée, False si elle existait déjà.
    """
    from sqlalchemy import text

    title = recipe_data["title"]
    slug = recipe_data["slug"]
    source_url = recipe_data.get("source_url") or ""

    # Vérification doublon par source_url OU slug
    check_query = text(
        """
        SELECT id FROM recipes
        WHERE slug = :slug OR (source_url != '' AND source_url = :source_url)
        LIMIT 1
        """
    )
    result = await session.execute(check_query, {"slug": slug, "source_url": source_url})
    existing = result.fetchone()
    if existing:
        logger.debug("recipe_skipped_duplicate", title=title, slug=slug)
        return False

    if dry_run:
        logger.info("[DRY_RUN] would_insert", title=title, ingredients=len(ingredients_raw))
        return True

    recipe_id = str(uuid4())
    instructions_json = json.dumps(recipe_data["instructions"], ensure_ascii=False)
    tags_json = json.dumps(recipe_data["tags"], ensure_ascii=False)

    # Insertion de la recette — ON CONFLICT (slug) DO NOTHING pour la sécurité des races
    await session.execute(
        text(
            """
            INSERT INTO recipes (
                id, title, slug, source, source_url,
                description, photo_url,
                instructions, servings,
                prep_time_min, cook_time_min,
                difficulty, cuisine_type,
                tags, quality_score,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :source, :source_url,
                :description, :photo_url,
                :instructions::jsonb, :servings,
                :prep_time_min, :cook_time_min,
                :difficulty, :cuisine_type,
                :tags::jsonb, :quality_score,
                NOW(), NOW()
            )
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {
            "id": recipe_id,
            "title": title,
            "slug": slug,
            "source": recipe_data["source"],
            "source_url": source_url,
            "description": recipe_data.get("description") or "",
            "photo_url": recipe_data.get("photo_url") or "",
            "instructions": instructions_json,
            "servings": recipe_data["servings"],
            "prep_time_min": recipe_data["prep_time_min"],
            "cook_time_min": recipe_data["cook_time_min"],
            "difficulty": recipe_data["difficulty"],
            "cuisine_type": recipe_data["cuisine_type"],
            "tags": tags_json,
            "quality_score": recipe_data["quality_score"],
        },
    )

    # Vérifier que la recette a bien été insérée (ON CONFLICT peut avoir ignoré)
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    row = result.fetchone()
    if row is None:
        logger.warning("recipe_insert_ignored_conflict", slug=slug)
        return False

    actual_recipe_id = str(row[0])

    # Insertion des ingrédients avec upsert + liaison recipe_ingredients
    for position, ingredient_spoon in enumerate(ingredients_raw):
        canonical_name: str
        try:
            quantity, unit, canonical_name = _parse_ingredient_quantity(ingredient_spoon)
        except Exception as exc:
            logger.warning(
                "ingredient_parse_error",
                ingredient=ingredient_spoon.get("name", "?"),
                error=str(exc),
            )
            continue

        try:
            ingredient_id = await _upsert_ingredient(session, canonical_name)
        except Exception as exc:
            logger.warning(
                "ingredient_upsert_error",
                canonical_name=canonical_name,
                error=str(exc),
            )
            continue

        # raw_text pour la traçabilité (champ optionnel absent du modèle ORM mais géré via text())
        raw_text = (ingredient_spoon.get("original") or f"{quantity} {unit} {canonical_name}").strip()

        await session.execute(
            text(
                """
                INSERT INTO recipe_ingredients
                    (recipe_id, ingredient_id, quantity, unit, notes, position)
                VALUES
                    (:recipe_id, :ingredient_id, :quantity, :unit, :notes, :position)
                ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                """
            ),
            {
                "recipe_id": actual_recipe_id,
                "ingredient_id": ingredient_id,
                "quantity": quantity,
                "unit": unit,
                "notes": raw_text[:200] if raw_text else None,
                "position": position,
            },
        )

    await session.commit()
    logger.info(
        "recipe_inserted",
        title=title,
        recipe_id=actual_recipe_id,
        ingredients_count=len(ingredients_raw),
        tags=recipe_data["tags"],
    )
    return True


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


def _validate_env() -> tuple[str, str]:
    """Vérifie que DATABASE_URL et SPOONACULAR_API_KEY sont définies.

    Returns:
        Tuple (database_url, api_key).

    Raises:
        SystemExit si une variable obligatoire est manquante.
    """
    db_url = os.getenv("DATABASE_URL", "")
    api_key = os.getenv("SPOONACULAR_API_KEY", "")

    missing: list[str] = []
    if not db_url:
        missing.append("DATABASE_URL")
    if not api_key:
        missing.append("SPOONACULAR_API_KEY")

    if missing:
        logger.error(
            "env_vars_missing",
            missing=missing,
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@host/db SPOONACULAR_API_KEY=xxx",
        )
        sys.exit(1)

    return db_url, api_key


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


async def run_import(
    database_url: str,
    api_key: str,
    max_recipes: int = 50,
    cuisines: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Orchestre l'import complet depuis Spoonacular vers la base de données.

    Appelable directement depuis une tâche Celery (await run_import(...)).

    Returns:
        Dict avec les compteurs : total_fetched, inserted, skipped, errors.
    """
    global _request_count
    _request_count = 0

    if cuisines is None or not cuisines:
        cuisines = CUISINES_DEFAULT

    logger.info(
        "spoonacular_import_start",
        max_recipes=max_recipes,
        cuisines=cuisines,
        dry_run=dry_run,
    )

    # Création du moteur SQLAlchemy async
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Compteurs de rapport
    total_fetched = 0
    inserted = 0
    skipped = 0
    errors = 0

    async with httpx.AsyncClient(
        headers={
            "Accept": "application/json",
            "User-Agent": "PrestoBot/1.0 (+https://presto.fr/bot)",
        }
    ) as http_client:
        all_recipes: list[dict[str, Any]] = []

        # Étape 1 : Collecte par cuisine
        recipes_per_cuisine = max(2, max_recipes // len(cuisines))
        for cuisine in cuisines:
            if _request_count >= SPOONACULAR_DAILY_LIMIT:
                logger.warning("spoonacular_quota_reached_during_fetch", cuisine=cuisine)
                break
            try:
                recipes = await fetch_recipes_by_cuisine(
                    http_client, api_key, cuisine, recipes_per_cuisine
                )
                all_recipes.extend(recipes)
            except RuntimeError as exc:
                # Quota dépassé — arrêter immédiatement
                logger.error("spoonacular_quota_error", error=str(exc))
                break
            except Exception as exc:
                logger.warning(
                    "spoonacular_cuisine_fetch_error",
                    cuisine=cuisine,
                    error=str(exc),
                )

        # Étape 2 : Recettes aléatoires végétariennes (si quota disponible)
        if _request_count < SPOONACULAR_DAILY_LIMIT - 1:
            try:
                veg_recipes = await fetch_random_recipes(http_client, api_key, 5, "vegetarian")
                all_recipes.extend(veg_recipes)
            except Exception as exc:
                logger.warning(
                    "spoonacular_random_fetch_error",
                    tags="vegetarian",
                    error=str(exc),
                )

        # Déduplication par ID Spoonacular (évite les doublons dans la même session)
        seen_ids: set[int] = set()
        unique_recipes: list[dict[str, Any]] = []
        for r in all_recipes:
            spoon_id = r.get("id")
            if spoon_id and spoon_id not in seen_ids:
                seen_ids.add(spoon_id)
                unique_recipes.append(r)
            elif not spoon_id:
                unique_recipes.append(r)

        # Limiter au max demandé
        unique_recipes = unique_recipes[:max_recipes]
        total_fetched = len(unique_recipes)

        logger.info(
            "spoonacular_collection_done",
            total_fetched=total_fetched,
            api_requests_used=_request_count,
            quota_remaining=SPOONACULAR_DAILY_LIMIT - _request_count,
        )

        if dry_run:
            logger.info("[DRY_RUN] Aperçu des 5 premières recettes :")
            for r in unique_recipes[:5]:
                logger.info(
                    "[DRY_RUN] recipe_preview",
                    title=r.get("title"),
                    image=r.get("image"),
                    cuisines=r.get("cuisines"),
                    ready_in=r.get("readyInMinutes"),
                )

        # Étape 3 : Normalisation et insertion
        async with session_factory() as session:
            for spoon_recipe in unique_recipes:
                try:
                    recipe_data = normalize_recipe(spoon_recipe)
                    ingredients_raw: list[dict[str, Any]] = (
                        spoon_recipe.get("extendedIngredients") or []
                    )

                    was_inserted = await _insert_recipe_with_ingredients(
                        session,
                        recipe_data,
                        ingredients_raw,
                        dry_run,
                    )

                    if was_inserted:
                        inserted += 1
                    else:
                        skipped += 1

                except Exception as exc:
                    logger.error(
                        "recipe_processing_error",
                        title=spoon_recipe.get("title", "?"),
                        spoonacular_id=spoon_recipe.get("id"),
                        error=str(exc),
                    )
                    errors += 1
                    try:
                        await session.rollback()
                    except Exception:
                        pass

    await engine.dispose()

    # Rapport final
    logger.info("=" * 60)
    logger.info("RAPPORT IMPORT SPOONACULAR")
    logger.info(f"  Total récupéré     : {total_fetched}")
    logger.info(f"  Insérées           : {inserted}")
    logger.info(f"  Ignorées (doublons): {skipped}")
    logger.info(f"  Erreurs            : {errors}")
    logger.info(f"  Requêtes API       : {_request_count}/{SPOONACULAR_DAILY_LIMIT}")
    logger.info("=" * 60)

    return {
        "total_fetched": total_fetched,
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "api_requests": _request_count,
    }


async def main() -> None:
    """Point d'entrée CLI du script."""
    _configure_logging()
    database_url, api_key = _validate_env()

    max_recipes = int(os.getenv("MAX_RECIPES", "50"))
    cuisines_env = os.getenv("CUISINES", "")
    cuisines: list[str] = cuisines_env.split(",") if cuisines_env else CUISINES_DEFAULT
    dry_run = os.getenv("DRY_RUN", "").lower() == "true"

    stats = await run_import(
        database_url=database_url,
        api_key=api_key,
        max_recipes=max_recipes,
        cuisines=cuisines,
        dry_run=dry_run,
    )

    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
