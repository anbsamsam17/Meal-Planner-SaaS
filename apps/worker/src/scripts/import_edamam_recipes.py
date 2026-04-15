"""Import de recettes de qualité depuis Edamam Recipe API v2.

Pipeline complet :
1. Fetch Edamam (photos HD 600x600, nutrition complète, labels régime)
2. Filtrage qualité (photo obligatoire, >= 4 ingrédients, nutrition présente)
3. Traduction intégrale FR via Gemini 2.0 Flash (titre, description, ingrédients)
4. Tags automatiques (régime, budget, catégorie — format plat, sans préfixe)
5. Insertion DB avec ingrédients canoniques FR

Usage :
    cd apps/worker
    set -a && source ../../.env.local && set +a
    python -m src.scripts.import_edamam_recipes

Variables d'environnement :
    EDAMAM_APP_ID           Obligatoire — Edamam application ID.
    EDAMAM_APP_KEY          Obligatoire — Edamam application key.
    GOOGLE_AI_API_KEY       Obligatoire — Gemini pour la traduction.
    DATABASE_URL            Obligatoire — PostgreSQL async.
    MAX_RECIPES             Optionnel — nombre cible (défaut : 100).
    DRY_RUN                 Optionnel — "true" pour simuler.
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

EDAMAM_BASE = "https://api.edamam.com/api/recipes/v2"
QUALITY_SCORE = 0.85
MIN_INGREDIENTS = 4

# Requêtes de recherche par cuisine — diversité maximale
SEARCH_QUERIES: list[dict[str, str]] = [
    # Française
    {"q": "boeuf bourguignon", "cuisineType": "French"},
    {"q": "coq au vin", "cuisineType": "French"},
    {"q": "quiche", "cuisineType": "French"},
    {"q": "gratin", "cuisineType": "French"},
    {"q": "tarte", "cuisineType": "French"},
    {"q": "soupe", "cuisineType": "French"},
    {"q": "poulet roti", "cuisineType": "French"},
    {"q": "crème brûlée", "cuisineType": "French"},
    {"q": "ratatouille", "cuisineType": "French"},
    {"q": "crêpes", "cuisineType": "French"},
    # Italienne
    {"q": "pasta", "cuisineType": "Italian"},
    {"q": "risotto", "cuisineType": "Italian"},
    {"q": "pizza", "cuisineType": "Italian"},
    {"q": "tiramisu", "cuisineType": "Italian"},
    {"q": "lasagna", "cuisineType": "Italian"},
    # Méditerranéenne
    {"q": "falafel", "cuisineType": "Mediterranean"},
    {"q": "hummus", "cuisineType": "Mediterranean"},
    {"q": "tabbouleh", "cuisineType": "Mediterranean"},
    {"q": "moussaka", "cuisineType": "Mediterranean"},
    # Japonaise
    {"q": "ramen", "cuisineType": "Japanese"},
    {"q": "sushi", "cuisineType": "Japanese"},
    {"q": "teriyaki", "cuisineType": "Japanese"},
    {"q": "tempura", "cuisineType": "Japanese"},
    # Mexicaine
    {"q": "tacos", "cuisineType": "Mexican"},
    {"q": "enchiladas", "cuisineType": "Mexican"},
    {"q": "guacamole", "cuisineType": "Mexican"},
    # Indienne
    {"q": "curry", "cuisineType": "Indian"},
    {"q": "tikka masala", "cuisineType": "Indian"},
    {"q": "biryani", "cuisineType": "Indian"},
    {"q": "naan", "cuisineType": "Indian"},
    # Thaïlandaise
    {"q": "pad thai", "cuisineType": "South East Asian"},
    {"q": "green curry", "cuisineType": "South East Asian"},
    {"q": "tom yum", "cuisineType": "South East Asian"},
    # Chinoise
    {"q": "fried rice", "cuisineType": "Chinese"},
    {"q": "dim sum", "cuisineType": "Chinese"},
    {"q": "kung pao", "cuisineType": "Chinese"},
    # Marocaine / Moyen-Orient
    {"q": "tagine", "cuisineType": "Middle Eastern"},
    {"q": "couscous", "cuisineType": "Middle Eastern"},
    {"q": "shawarma", "cuisineType": "Middle Eastern"},
    # Américaine
    {"q": "burger", "cuisineType": "American"},
    {"q": "mac and cheese", "cuisineType": "American"},
    # Coréenne
    {"q": "bibimbap", "cuisineType": "Korean"},
    {"q": "kimchi", "cuisineType": "Korean"},
    # Espagnole / Grecque
    {"q": "paella", "cuisineType": "Mediterranean"},
    {"q": "gazpacho", "cuisineType": "Mediterranean"},
]

CUISINE_EN_TO_FR: dict[str, str] = {
    "french": "française",
    "italian": "italienne",
    "japanese": "japonaise",
    "mexican": "mexicaine",
    "indian": "indienne",
    "south east asian": "thaïlandaise",
    "chinese": "chinoise",
    "mediterranean": "méditerranéenne",
    "korean": "coréenne",
    "american": "américaine",
    "middle eastern": "moyen-orientale",
    "british": "britannique",
    "caribbean": "caraïbéenne",
    "central europe": "européenne",
    "eastern europe": "européenne",
    "nordic": "européenne",
    "south american": "brésilienne",
}

# ---------------------------------------------------------------------------
# Edamam API
# ---------------------------------------------------------------------------

async def fetch_recipes(
    client: httpx.AsyncClient,
    app_id: str,
    app_key: str,
    query: dict[str, str],
    max_per_query: int = 5,
) -> list[dict[str, Any]]:
    """Fetch recettes Edamam avec nutrition + photos HD."""
    try:
        response = await client.get(
            EDAMAM_BASE,
            params={
                "type": "public",
                "q": query["q"],
                "cuisineType": query.get("cuisineType", ""),
                "imageSize": "LARGE",
            },
            auth=(app_id, app_key),
            headers={"Edamam-Account-User": app_id, "Accept": "application/json"},
            timeout=20,
        )

        if response.status_code == 429:
            logger.warning("rate_limited", query=query["q"])
            await asyncio.sleep(60)
            return []

        if response.status_code != 200:
            logger.error("fetch_error", query=query["q"], status=response.status_code, body=response.text[:200])
            return []

        data = response.json()
        hits = data.get("hits", [])
        recipes = [hit["recipe"] for hit in hits[:max_per_query]]
        logger.info("fetched", query=query["q"], cuisine=query.get("cuisineType", "?"), count=len(recipes))
        return recipes

    except Exception as exc:
        logger.error("fetch_exception", query=query["q"], error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Filtrage qualité
# ---------------------------------------------------------------------------

def passes_quality_filter(recipe: dict[str, Any]) -> bool:
    """Rejette les recettes qui ne respectent pas nos critères de qualité."""
    # Photo obligatoire
    image = recipe.get("image") or ""
    if not image:
        return False

    # Ingrédients suffisants
    ingredients = recipe.get("ingredientLines") or []
    if len(ingredients) < MIN_INGREDIENTS:
        return False

    # Titre pas trop court
    label = (recipe.get("label") or "").strip()
    if len(label) < 4:
        return False

    # Nutrition présente (calories > 0)
    if (recipe.get("calories") or 0) <= 0:
        return False

    return True


# ---------------------------------------------------------------------------
# Extraction nutrition
# ---------------------------------------------------------------------------

def extract_nutrition(recipe: dict[str, Any]) -> dict[str, float]:
    """Extrait les valeurs nutritionnelles depuis Edamam (par portion)."""
    servings = max(1, int(recipe.get("yield") or 4))
    nutrients = recipe.get("totalNutrients") or {}

    def per_serving(key: str) -> float:
        total = nutrients.get(key, {}).get("quantity", 0)
        return round(total / servings, 1)

    return {
        "calories": round((recipe.get("calories") or 0) / servings),
        "protein_g": per_serving("PROCNT"),
        "carbs_g": per_serving("CHOCDF"),
        "fat_g": per_serving("FAT"),
        "fiber_g": per_serving("FIBTG"),
        "sugar_g": per_serving("SUGAR"),
        "sodium_mg": per_serving("NA"),
    }


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


async def translate_recipe(recipe: dict[str, Any]) -> dict[str, Any] | None:
    """Traduit titre + ingrédients EN→FR via Gemini 2.0 Flash."""
    from google.genai import types

    client = _get_gemini()
    label = recipe.get("label", "")
    ingredients = recipe.get("ingredientLines", [])[:20]

    prompt = f"""Traduis cette recette de l'anglais vers le français.
Retourne UNIQUEMENT le JSON demandé.

Recette originale :
- Titre : {label}
- Ingrédients : {json.dumps(ingredients[:15], ensure_ascii=False)}

Règles :
- Titre : naturel en français, appétissant. Ex: "Chicken Parmesan" → "Poulet parmigiana"
- Description : 1-2 phrases décrivant le plat en français (appétissant, précis)
- Ingrédients : nom canonique français, quantités incluses. Ex: "2 cups flour" → "250g de farine"
- Instructions : génère 4-8 étapes logiques de préparation basées sur les ingrédients

JSON attendu :
{{
  "title_fr": "...",
  "description_fr": "...",
  "ingredients_fr": ["ingrédient 1", "ingrédient 2", ...],
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
        logger.debug("translated", title_en=label[:40], title_fr=result.get("title_fr", "?")[:40])
        return result
    except Exception as exc:
        logger.warning("translation_failed", title=label[:40], error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def build_tags(recipe: dict[str, Any]) -> list[str]:
    """Construit les tags depuis les métadonnées Edamam — format plat, sans préfixe."""
    tags: list[str] = []
    health = set(recipe.get("healthLabels") or [])
    diet = set(recipe.get("dietLabels") or [])

    # Régime alimentaire
    if "Vegan" in health:
        tags.append("vegan")
    if "Vegetarian" in health:
        tags.append("végétarien")
    if "Gluten-Free" in health:
        tags.append("sans-gluten")
    if "Dairy-Free" in health:
        tags.append("sans-lactose")
    if "Egg-Free" in health:
        tags.append("sans-oeufs")
    if "Peanut-Free" in health and "Tree-Nut-Free" in health:
        tags.append("sans-fruits-à-coque")
    if "Pork-Free" in health:
        tags.append("sans-porc")
    if "Shellfish-Free" in health and "Fish-Free" in health:
        tags.append("sans-fruits-de-mer")
    if "Pescatarian" in health:
        tags.append("pescatarien")
    if "Alcohol-Free" in health:
        pass  # pas de tag spécifique

    # Type de plat
    dish_types = recipe.get("dishType") or []
    meal_types = recipe.get("mealType") or []

    for dt in dish_types:
        dt_lower = dt.lower()
        if dt_lower in ("main course", "dinner", "lunch"):
            if "plat" not in tags:
                tags.append("plat")
        elif "dessert" in dt_lower and "dessert" not in tags:
            tags.append("dessert")
        elif dt_lower in ("starter", "appetizer", "antipasti", "snack"):
            if "entrée" not in tags:
                tags.append("entrée")
        elif "salad" in dt_lower and "entrée" not in tags:
            tags.append("entrée")
        elif "soup" in dt_lower and "entrée" not in tags:
            tags.append("entrée")
        elif "bread" in dt_lower and "accompagnement" not in tags:
            tags.append("accompagnement")
        elif "side" in dt_lower and "accompagnement" not in tags:
            tags.append("accompagnement")

    for mt in meal_types:
        mt_lower = mt.lower()
        if "breakfast" in mt_lower and "petit-déjeuner" not in tags:
            tags.append("petit-déjeuner")
        if "brunch" in mt_lower and "brunch" not in tags:
            tags.append("brunch")
        if "snack" in mt_lower and "apéritif" not in tags:
            tags.append("apéritif")

    # Budget heuristique basé sur le nombre d'ingrédients
    nb_ing = len(recipe.get("ingredientLines") or [])
    if nb_ing <= 6:
        tags.append("économique")
    elif nb_ing > 12:
        tags.append("premium")
    else:
        tags.append("moyen")

    # Temps
    total_time = recipe.get("totalTime") or 0
    if 0 < total_time <= 20:
        tags.append("rapide")

    # Catégorie par défaut
    if not any(t in tags for t in ("plat", "dessert", "entrée", "petit-déjeuner", "accompagnement")):
        tags.append("plat")

    # Occasion par défaut
    tags.append("quotidien")

    return list(set(tags))


def map_difficulty(recipe: dict[str, Any]) -> int:
    """Difficulté 1-5 basée sur le nombre d'ingrédients."""
    nb_ing = len(recipe.get("ingredientLines") or [])
    if nb_ing <= 4:
        return 1
    if nb_ing <= 7:
        return 2
    if nb_ing <= 10:
        return 3
    if nb_ing <= 15:
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
    return slug.strip("-")[:80]


def _extract_photo_url(recipe: dict[str, Any]) -> str:
    """Extrait la meilleure photo disponible (LARGE > REGULAR > image)."""
    images = recipe.get("images") or {}
    large = images.get("LARGE", {}).get("url", "")
    if large:
        return large
    regular = images.get("REGULAR", {}).get("url", "")
    if regular:
        return regular
    return recipe.get("image") or ""


def _extract_edamam_id(recipe: dict[str, Any]) -> str:
    """Extrait l'ID unique Edamam depuis l'URI."""
    uri = recipe.get("uri") or ""
    # Format: http://www.edamam.com/ontologies/edamam.owl#recipe_xxx
    if "#recipe_" in uri:
        return uri.split("#recipe_")[1][:20]
    return uuid4().hex[:12]


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
    edamam_recipe: dict[str, Any],
    translation: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Insère une recette traduite avec ses ingrédients et nutrition."""
    from sqlalchemy import text

    title_fr = translation["title_fr"]
    edamam_id = _extract_edamam_id(edamam_recipe)
    slug = f"{_slugify(title_fr)}-{edamam_id}"

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

    # Cuisine type
    cuisine_type = "internationale"
    for ct in (edamam_recipe.get("cuisineType") or []):
        mapped = CUISINE_EN_TO_FR.get(ct.lower())
        if mapped:
            cuisine_type = mapped
            break

    # Instructions FR depuis Gemini
    instructions_fr = [
        {"step": i + 1, "text": step}
        for i, step in enumerate(translation.get("instructions_fr") or [])
    ]

    nutrition_data = extract_nutrition(edamam_recipe)
    tags = build_tags(edamam_recipe)
    photo_url = _extract_photo_url(edamam_recipe)
    source_url = edamam_recipe.get("url") or ""
    servings = max(1, int(edamam_recipe.get("yield") or 4))
    total_time = int(edamam_recipe.get("totalTime") or 0)
    prep_time = max(0, total_time // 3) if total_time > 0 else 0
    cook_time = max(0, total_time - prep_time) if total_time > 0 else 30

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
                :id, :title, :slug, 'edamam', :source_url,
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
            "source_url": source_url,
            "description": (translation.get("description_fr") or "")[:500],
            "photo_url": photo_url,
            "nutrition": json.dumps(nutrition_data, ensure_ascii=False),
            "instructions": json.dumps(instructions_fr, ensure_ascii=False),
            "servings": servings,
            "prep_time_min": prep_time,
            "cook_time_min": cook_time,
            "difficulty": map_difficulty(edamam_recipe),
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
    ingredients_en = edamam_recipe.get("ingredientLines") or []

    for position, ing_text in enumerate(ingredients_en[:20]):
        # Nom FR si dispo
        name_fr = ingredients_fr[position].strip().lower() if position < len(ingredients_fr) else None
        # Extraire le nom canonique (sans quantité) — prendre les derniers mots
        canonical = name_fr or ing_text.strip().lower()
        # Tronquer à un nom raisonnable
        canonical = canonical[:100]
        if not canonical:
            continue

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
                    "rid": actual_id,
                    "iid": ing_id,
                    "qty": 1.0,
                    "unit": "u",
                    "notes": ing_text[:200],
                    "pos": position,
                },
            )
        except Exception as exc:
            logger.warning("ingredient_error", name=canonical[:30], error=str(exc))

    await session.commit()
    logger.info("inserted", title=title_fr, tags=tags, calories=nutrition_data.get("calories", 0))
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_import() -> dict[str, int]:
    """Orchestre l'import complet."""
    app_id = os.getenv("EDAMAM_APP_ID", "")
    app_key = os.getenv("EDAMAM_APP_KEY", "")
    db_url = os.getenv("DATABASE_URL", "")
    google_key = os.getenv("GOOGLE_AI_API_KEY", "")
    max_recipes = int(os.getenv("MAX_RECIPES", "100"))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    missing = []
    if not app_id:
        missing.append("EDAMAM_APP_ID")
    if not app_key:
        missing.append("EDAMAM_APP_KEY")
    if not db_url:
        missing.append("DATABASE_URL")
    if not google_key:
        missing.append("GOOGLE_AI_API_KEY")
    if missing:
        logger.error("env_missing", vars=missing)
        sys.exit(1)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stats = {"fetched": 0, "quality_pass": 0, "translated": 0, "inserted": 0, "skipped": 0, "errors": 0}
    seen_titles: set[str] = set()

    per_query = max(3, max_recipes // len(SEARCH_QUERIES))

    async with httpx.AsyncClient() as http:
        all_recipes: list[dict[str, Any]] = []

        # 1. Fetch toutes les cuisines
        for i, query in enumerate(SEARCH_QUERIES):
            if len(all_recipes) >= max_recipes * 2:
                break
            try:
                batch = await fetch_recipes(http, app_id, app_key, query, per_query)
                # Dédupliquer par titre
                for r in batch:
                    title = (r.get("label") or "").lower().strip()
                    if title not in seen_titles:
                        seen_titles.add(title)
                        all_recipes.append(r)
                stats["fetched"] += len(batch)
            except Exception as exc:
                logger.error("fetch_error", query=query["q"], error=str(exc))
                stats["errors"] += 1

            # Rate limit Edamam (10 req/min free tier)
            if (i + 1) % 9 == 0:
                logger.info("edamam_cooldown", wait="62s", progress=f"{i+1}/{len(SEARCH_QUERIES)}")
                await asyncio.sleep(62)

        logger.info("fetch_complete", total_fetched=stats["fetched"], unique=len(all_recipes))

        # 2. Filtrage qualité
        quality_recipes = [r for r in all_recipes if passes_quality_filter(r)]
        stats["quality_pass"] = len(quality_recipes)
        logger.info("quality_filter", passed=len(quality_recipes), rejected=len(all_recipes) - len(quality_recipes))

        # Limiter au max demandé
        quality_recipes = quality_recipes[:max_recipes]

        # 3. Traduction + insertion
        for i, recipe in enumerate(quality_recipes):
            title_en = (recipe.get("label") or "?")[:50]
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
                    else:
                        stats["skipped"] += 1

            except Exception as exc:
                logger.error("insert_error", title=title_en, error=str(exc))
                stats["errors"] += 1

            # Rate limit Gemini (15 req/min free tier)
            if (i + 1) % 14 == 0:
                logger.info("gemini_cooldown", wait="65s", progress=f"{i+1}/{len(quality_recipes)}")
                await asyncio.sleep(65)

    await engine.dispose()

    logger.info("=" * 50)
    logger.info("=== IMPORT EDAMAM TERMINÉ ===")
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
    logger.info("=== Import recettes qualité Edamam + Gemini FR ===")
    asyncio.run(run_import())


if __name__ == "__main__":
    main()
