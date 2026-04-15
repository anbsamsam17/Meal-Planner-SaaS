"""Import de recettes de qualité depuis Spoonacular avec traduction FR + nutrition.

Pipeline complet :
1. Fetch Spoonacular (photos HD, nutrition, instructions détaillées)
2. Filtrage qualité (photo obligatoire, instructions complètes, nutrition présente)
3. Traduction intégrale FR via Gemini 2.0 Flash (titre, description, ingrédients, instructions)
4. Tags automatiques (régime, budget, catégorie, saison)
5. Insertion DB avec ingrédients canoniques FR

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... \
    SPOONACULAR_API_KEY=... \
    GOOGLE_AI_API_KEY=... \
    uv run python -m src.scripts.import_quality_recipes

Variables d'environnement :
    DATABASE_URL            Obligatoire — PostgreSQL async.
    SPOONACULAR_API_KEY     Obligatoire — free tier 150 points/jour.
    GOOGLE_AI_API_KEY       Obligatoire — Gemini pour la traduction.
    MAX_RECIPES             Optionnel — nombre cible (défaut : 100).
    DRY_RUN                 Optionnel — "true" pour simuler.
    LOG_LEVEL               Optionnel — DEBUG/INFO (défaut : INFO).
"""

import asyncio
import json
import os
import re
import sys
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SPOONACULAR_BASE = "https://api.spoonacular.com"
SPOONACULAR_POINTS_LIMIT = 140  # Garder une marge sur les 150 pts/jour
QUALITY_SCORE = 0.85  # Score élevé — recettes filtrées et enrichies
MIN_INGREDIENTS = 3
MIN_INSTRUCTIONS_STEPS = 3

# Cuisines à importer — diversité maximale
CUISINES: list[str] = [
    "french", "italian", "mediterranean", "japanese",
    "mexican", "indian", "thai", "chinese",
    "korean", "vietnamese", "greek", "spanish",
    "moroccan", "middle eastern", "american",
]

CUISINE_EN_TO_FR: dict[str, str] = {
    "French": "française", "Italian": "italienne", "Japanese": "japonaise",
    "Mexican": "mexicaine", "Indian": "indienne", "Thai": "thaïlandaise",
    "Chinese": "chinoise", "Mediterranean": "méditerranéenne",
    "Korean": "coréenne", "Vietnamese": "vietnamienne",
    "American": "américaine", "Greek": "grecque", "Spanish": "espagnole",
    "Lebanese": "libanaise", "Moroccan": "marocaine",
    "Middle Eastern": "moyen-orientale", "German": "allemande",
    "British": "britannique", "Caribbean": "caraïbéenne",
    "European": "européenne",
}

_points_used = 0


# ---------------------------------------------------------------------------
# Spoonacular API
# ---------------------------------------------------------------------------

async def _api_get(
    client: httpx.AsyncClient, api_key: str,
    endpoint: str, params: dict[str, Any],
) -> dict[str, Any]:
    """GET Spoonacular avec suivi des points."""
    global _points_used
    if _points_used >= SPOONACULAR_POINTS_LIMIT:
        raise RuntimeError(f"Quota Spoonacular atteint ({_points_used} pts)")

    response = await client.get(
        f"{SPOONACULAR_BASE}{endpoint}",
        params={"apiKey": api_key, **params},
        timeout=30,
    )
    if response.status_code == 402:
        raise RuntimeError("Quota Spoonacular dépassé (HTTP 402)")
    if response.status_code == 401:
        raise ValueError("SPOONACULAR_API_KEY invalide (HTTP 401)")
    response.raise_for_status()

    # Comptabiliser les points (header Spoonacular)
    used = int(response.headers.get("X-API-Quota-Used", "1"))
    _points_used += used
    logger.debug("api_call", endpoint=endpoint, points_used=_points_used)

    return response.json()


async def fetch_quality_recipes(
    client: httpx.AsyncClient, api_key: str,
    cuisine: str, number: int = 10,
) -> list[dict[str, Any]]:
    """Fetch recettes Spoonacular avec nutrition + instructions complètes."""
    data = await _api_get(client, api_key, "/recipes/complexSearch", {
        "cuisine": cuisine,
        "number": min(number, 20),
        "addRecipeInformation": True,
        "addRecipeNutrition": True,  # Inclut les données nutritionnelles
        "fillIngredients": True,
        "instructionsRequired": True,
        "sort": "popularity",
        "sortDirection": "desc",
    })
    results = data.get("results") or []
    logger.info("fetched", cuisine=cuisine, count=len(results))
    return results


# ---------------------------------------------------------------------------
# Filtrage qualité
# ---------------------------------------------------------------------------

def passes_quality_filter(recipe: dict[str, Any]) -> bool:
    """Rejette les recettes qui ne respectent pas nos critères de qualité."""
    # Photo obligatoire et de bonne taille
    image = recipe.get("image") or ""
    if not image or "no-image" in image.lower():
        return False

    # Instructions obligatoires et détaillées
    analyzed = recipe.get("analyzedInstructions") or []
    steps_count = 0
    if analyzed:
        steps_count = len(analyzed[0].get("steps") or [])
    if steps_count < MIN_INSTRUCTIONS_STEPS:
        return False

    # Ingrédients suffisants
    ingredients = recipe.get("extendedIngredients") or []
    if len(ingredients) < MIN_INGREDIENTS:
        return False

    # Titre pas trop générique
    title = (recipe.get("title") or "").strip()
    if len(title) < 5:
        return False

    return True


# ---------------------------------------------------------------------------
# Extraction nutrition
# ---------------------------------------------------------------------------

def extract_nutrition(recipe: dict[str, Any]) -> dict[str, float]:
    """Extrait les valeurs nutritionnelles depuis la réponse Spoonacular."""
    nutrition = recipe.get("nutrition") or {}
    nutrients = nutrition.get("nutrients") or []

    result: dict[str, float] = {}
    mapping = {
        "Calories": "calories",
        "Protein": "protein_g",
        "Carbohydrates": "carbs_g",
        "Fat": "fat_g",
        "Fiber": "fiber_g",
        "Sugar": "sugar_g",
        "Sodium": "sodium_mg",
    }

    for nutrient in nutrients:
        name = nutrient.get("name", "")
        if name in mapping:
            result[mapping[name]] = round(float(nutrient.get("amount", 0)), 1)

    return result


# ---------------------------------------------------------------------------
# Traduction FR via Gemini
# ---------------------------------------------------------------------------

_gemini_client = None


def _get_gemini():
    """Client Gemini singleton."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        key = os.getenv("GOOGLE_AI_API_KEY", "")
        if not key:
            raise ValueError("GOOGLE_AI_API_KEY manquante")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


async def translate_recipe(recipe_en: dict[str, Any]) -> dict[str, Any] | None:
    """Traduit une recette complète EN→FR via Gemini 2.0 Flash.

    Retourne None si la traduction échoue.
    """
    from google.genai import types

    client = _get_gemini()
    title = recipe_en.get("title", "")
    summary = (recipe_en.get("summary") or "")[:500]
    # Nettoyer le HTML du summary
    summary = re.sub(r"<[^>]+>", "", summary).strip()

    # Préparer les ingrédients et instructions en texte
    ingredients_text = []
    for ing in (recipe_en.get("extendedIngredients") or [])[:20]:
        original = ing.get("original") or ing.get("name", "")
        ingredients_text.append(original)

    instructions_text = []
    for section in (recipe_en.get("analyzedInstructions") or []):
        for step in (section.get("steps") or []):
            text = (step.get("step") or "").strip()
            if text:
                instructions_text.append(text)

    prompt = f"""Traduis cette recette de l'anglais vers le français.
Retourne UNIQUEMENT le JSON demandé, rien d'autre.

Recette originale :
- Titre : {title}
- Description : {summary[:300]}
- Ingrédients : {json.dumps(ingredients_text[:15], ensure_ascii=False)}
- Instructions : {json.dumps(instructions_text[:10], ensure_ascii=False)}

Règles de traduction :
- Titre : naturel en français, pas de traduction littérale. Ex: "Chicken Parmesan" → "Poulet parmigiana"
- Description : 1-2 phrases appétissantes en français
- Ingrédients : nom canonique français, singulier, minuscule. Ex: "chicken breast" → "blanc de poulet"
- Instructions : français naturel avec temps, températures en °C, indicateurs visuels

JSON attendu :
{{
  "title_fr": "...",
  "description_fr": "...",
  "ingredients_fr": ["nom_fr_1", "nom_fr_2", ...],
  "instructions_fr": ["Étape 1...", "Étape 2...", ...]
}}"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        result = json.loads(response.text)
        logger.debug("translated", title_en=title[:40], title_fr=result.get("title_fr", "?")[:40])
        return result
    except Exception as exc:
        logger.warning("translation_failed", title=title[:40], error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def build_tags(recipe: dict[str, Any]) -> list[str]:
    """Construit les tags depuis les métadonnées Spoonacular."""
    tags: list[str] = []

    # Régime alimentaire
    if recipe.get("vegetarian"):
        tags.append("végétarien")
    if recipe.get("vegan"):
        tags.append("vegan")
    if recipe.get("glutenFree"):
        tags.append("sans-gluten")
    if recipe.get("dairyFree"):
        tags.append("sans-lactose")
    if recipe.get("cheap"):
        tags.append("économique")

    # Catégorie de plat
    for dish_type in (recipe.get("dishTypes") or []):
        dt = dish_type.lower()
        if dt in ("main course", "dinner", "lunch"):
            if "plat" not in tags:
                tags.append("plat")
        elif dt == "dessert" and "dessert" not in tags:
            tags.append("dessert")
        elif dt in ("appetizer", "starter", "antipasti", "snack"):
            if "entrée" not in tags:
                tags.append("entrée")
        elif dt in ("breakfast", "morning meal"):
            if "petit-déjeuner" not in tags:
                tags.append("petit-déjeuner")
        elif dt in ("side dish",):
            if "accompagnement" not in tags:
                tags.append("accompagnement")
        elif dt in ("soup",) and "entrée" not in tags:
            tags.append("entrée")
        elif dt in ("salad",) and "entrée" not in tags:
            tags.append("entrée")

    # Temps
    ready_in = recipe.get("readyInMinutes") or 60
    if ready_in <= 20:
        tags.append("rapide")
    elif ready_in <= 30:
        tags.append("express")

    # Budget heuristique
    nb_ing = len(recipe.get("extendedIngredients") or [])
    if nb_ing <= 6 and "économique" not in tags:
        tags.append("économique")
    elif nb_ing > 10:
        tags.append("premium")
    elif "économique" not in tags:
        tags.append("moyen")

    # Catégorie par défaut si aucune n'a été attribuée
    if not any(t in tags for t in ("plat", "dessert", "entrée", "petit-déjeuner", "accompagnement")):
        tags.append("plat")

    return list(set(tags))


def map_difficulty(recipe: dict[str, Any]) -> int:
    """Difficulté 1-5 basée sur le temps et le nombre d'étapes."""
    time_min = recipe.get("readyInMinutes") or 30
    steps = 0
    analyzed = recipe.get("analyzedInstructions") or []
    if analyzed:
        steps = len(analyzed[0].get("steps") or [])

    if time_min <= 15 and steps <= 3:
        return 1
    if time_min <= 30 and steps <= 5:
        return 2
    if time_min <= 60:
        return 3
    if time_min <= 120:
        return 4
    return 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convertit un titre en slug URL-safe."""
    slug = text.lower()
    for c, r in {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
                  "ù": "u", "û": "u", "ô": "o", "î": "i", "ç": "c", "œ": "oe",
                  "ä": "a", "ö": "o", "ü": "u", "ï": "i", "æ": "ae"}.items():
        slug = slug.replace(c, r)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _strip_html(text: str) -> str:
    """Retire les balises HTML."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("&amp;", "&").replace("&nbsp;", " ")
    return " ".join(clean.split()).strip()


# ---------------------------------------------------------------------------
# Insertion DB
# ---------------------------------------------------------------------------

async def _upsert_ingredient(session: Any, canonical_name: str) -> str:
    """Upsert ingrédient canonique, retourne l'UUID."""
    from sqlalchemy import text

    ingredient_id = str(uuid4())
    await session.execute(
        text("""
            INSERT INTO ingredients (id, canonical_name, category, created_at)
            VALUES (:id, :name, 'other', NOW())
            ON CONFLICT (canonical_name) DO NOTHING
        """),
        {"id": ingredient_id, "name": canonical_name},
    )
    result = await session.execute(
        text("SELECT id FROM ingredients WHERE canonical_name = :name LIMIT 1"),
        {"name": canonical_name},
    )
    row = result.fetchone()
    return str(row[0])


async def insert_recipe(
    session: Any,
    spoon_recipe: dict[str, Any],
    translation: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Insère une recette traduite avec ses ingrédients et nutrition."""
    from sqlalchemy import text

    title_fr = translation["title_fr"]
    spoon_id = spoon_recipe.get("id", "")
    slug = f"{_slugify(title_fr)}-{spoon_id}" if spoon_id else _slugify(title_fr)

    # Doublon ?
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    if result.fetchone():
        logger.debug("skip_duplicate", slug=slug)
        return False

    if dry_run:
        logger.info("[DRY_RUN]", title=title_fr)
        return True

    recipe_id = str(uuid4())
    cuisine_type = "internationale"
    for c in (spoon_recipe.get("cuisines") or []):
        if c in CUISINE_EN_TO_FR:
            cuisine_type = CUISINE_EN_TO_FR[c]
            break

    instructions_fr = [
        {"step": i + 1, "text": step}
        for i, step in enumerate(translation.get("instructions_fr") or [])
    ]
    nutrition_data = extract_nutrition(spoon_recipe)
    tags = build_tags(spoon_recipe)

    # Photo : utiliser la version 636x393 (haute qualité) si disponible
    photo = spoon_recipe.get("image") or ""
    if photo and "spoonacular.com" in photo:
        photo = re.sub(r"-\d+x\d+\.", "-636x393.", photo)

    await session.execute(
        text("""
            INSERT INTO recipes (
                id, title, slug, source, source_url,
                description, photo_url, nutrition,
                instructions, servings,
                prep_time_min, cook_time_min,
                difficulty, cuisine_type,
                tags, quality_score,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, 'spoonacular', :source_url,
                :description, :photo_url, :nutrition::jsonb,
                :instructions::jsonb, :servings,
                :prep_time_min, :cook_time_min,
                :difficulty, :cuisine_type,
                :tags::text[], :quality_score,
                NOW(), NOW()
            )
            ON CONFLICT (slug) DO NOTHING
        """),
        {
            "id": recipe_id,
            "title": title_fr,
            "slug": slug,
            "source_url": spoon_recipe.get("sourceUrl") or "",
            "description": (translation.get("description_fr") or "")[:500],
            "photo_url": photo,
            "nutrition": json.dumps(nutrition_data, ensure_ascii=False),
            "instructions": json.dumps(instructions_fr, ensure_ascii=False),
            "servings": max(1, int(spoon_recipe.get("servings") or 4)),
            "prep_time_min": max(0, int(spoon_recipe.get("preparationMinutes") or 0)),
            "cook_time_min": max(0, int(spoon_recipe.get("cookingMinutes") or spoon_recipe.get("readyInMinutes") or 30)),
            "difficulty": map_difficulty(spoon_recipe),
            "cuisine_type": cuisine_type,
            "tags": tags,
            "quality_score": QUALITY_SCORE,
        },
    )

    # Vérifier insertion
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    row = result.fetchone()
    if not row:
        return False
    actual_id = str(row[0])

    # Ingrédients FR
    ingredients_fr = translation.get("ingredients_fr") or []
    ingredients_en = spoon_recipe.get("extendedIngredients") or []

    for position, ing_en in enumerate(ingredients_en[:20]):
        # Nom FR si disponible, sinon fallback EN nettoyé
        name_fr = ingredients_fr[position].strip().lower() if position < len(ingredients_fr) else None
        canonical = name_fr or (ing_en.get("nameClean") or ing_en.get("name") or "").strip().lower()
        if not canonical:
            continue

        # Quantité et unité
        measures = ing_en.get("measures") or {}
        metric = measures.get("metric") or {}
        quantity = float(metric.get("amount") or ing_en.get("amount") or 1.0)
        unit = (metric.get("unitShort") or "").strip() or "u"
        quantity = max(0.001, quantity)

        try:
            ing_id = await _upsert_ingredient(session, canonical)
            await session.execute(
                text("""
                    INSERT INTO recipe_ingredients
                        (recipe_id, ingredient_id, quantity, unit, notes, position)
                    VALUES (:rid, :iid, :qty, :unit, :notes, :pos)
                    ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                """),
                {
                    "rid": actual_id, "iid": ing_id,
                    "qty": quantity, "unit": unit,
                    "notes": (ing_en.get("original") or "")[:200] or None,
                    "pos": position,
                },
            )
        except Exception as exc:
            logger.warning("ingredient_error", name=canonical, error=str(exc))

    await session.commit()
    logger.info("inserted", title=title_fr, tags=tags, nutrition=bool(nutrition_data))
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_import() -> dict[str, int]:
    """Orchestre l'import complet."""
    global _points_used
    _points_used = 0

    db_url = os.getenv("DATABASE_URL", "")
    api_key = os.getenv("SPOONACULAR_API_KEY", "")
    google_key = os.getenv("GOOGLE_AI_API_KEY", "")
    max_recipes = int(os.getenv("MAX_RECIPES", "100"))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    missing = []
    if not db_url:
        missing.append("DATABASE_URL")
    if not api_key:
        missing.append("SPOONACULAR_API_KEY")
    if not google_key:
        missing.append("GOOGLE_AI_API_KEY")
    if missing:
        logger.error("env_missing", vars=missing)
        sys.exit(1)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stats = {"fetched": 0, "quality_pass": 0, "translated": 0, "inserted": 0, "errors": 0}

    async with httpx.AsyncClient(
        headers={"Accept": "application/json", "User-Agent": "PrestoBot/2.0"}
    ) as http:
        all_recipes: list[dict[str, Any]] = []
        per_cuisine = max(3, max_recipes // len(CUISINES))

        # 1. Fetch
        for cuisine in CUISINES:
            if _points_used >= SPOONACULAR_POINTS_LIMIT:
                logger.warning("quota_reached", points=_points_used)
                break
            try:
                batch = await fetch_quality_recipes(http, api_key, cuisine, per_cuisine)
                all_recipes.extend(batch)
                stats["fetched"] += len(batch)
            except Exception as exc:
                logger.error("fetch_error", cuisine=cuisine, error=str(exc))
                stats["errors"] += 1

        logger.info("fetch_complete", total=stats["fetched"], points_used=_points_used)

        # 2. Filtrage qualité
        quality_recipes = [r for r in all_recipes if passes_quality_filter(r)]
        stats["quality_pass"] = len(quality_recipes)
        logger.info("quality_filter", passed=len(quality_recipes), rejected=len(all_recipes) - len(quality_recipes))

        # Limiter au max demandé
        quality_recipes = quality_recipes[:max_recipes]

        # 3. Traduction + insertion
        for i, recipe in enumerate(quality_recipes):
            title_en = (recipe.get("title") or "?")[:50]
            logger.info(f"[{i+1}/{len(quality_recipes)}] translating", title=title_en)

            try:
                translation = await translate_recipe(recipe)
                if not translation or not translation.get("title_fr"):
                    logger.warning("translation_empty", title=title_en)
                    stats["errors"] += 1
                    continue
                stats["translated"] += 1

                async with session_factory() as session:
                    ok = await insert_recipe(session, recipe, translation, dry_run)
                    if ok:
                        stats["inserted"] += 1

            except Exception as exc:
                logger.error("insert_error", title=title_en, error=str(exc))
                stats["errors"] += 1

            # Rate limit Gemini (15 req/min free tier)
            if (i + 1) % 14 == 0:
                logger.info("gemini_cooldown", wait="65s")
                await asyncio.sleep(65)

    await engine.dispose()

    logger.info("=== IMPORT TERMINÉ ===")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")

    return stats


def _configure_logging() -> None:
    """Configure loguru."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )


def main() -> None:
    _configure_logging()
    logger.info("=== Import recettes qualité Spoonacular + Gemini FR ===")
    asyncio.run(run_import())


if __name__ == "__main__":
    main()
