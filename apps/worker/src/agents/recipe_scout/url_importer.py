"""Import d'une recette depuis une URL arbitraire (user-import).

Pipeline :
1. Fetch la page via httpx (timeout 15s, user-agent Chrome)
2. Extraction JSON-LD schema.org Recipe (universel — marche sur tout site)
3. Fallback HTML basique si pas de JSON-LD (h1 titre, meta description, listes)
4. Mapping vers le format DB interne (slug, instructions JSONB, nutrition)
5. Insertion idempotente (ON CONFLICT slug DO NOTHING)
6. Retourne le recipe_id pour chainage vers embed_recipe

Reuse depuis scrape_marmiton.py :
- extract_json_ld_recipe() — extraction JSON-LD universelle
- map_json_ld_to_recipe() — mapping JSON-LD → format DB (adapte pour source parametrable)
- parse_iso8601_duration() — PT30M → 30
- parse_ingredient_line() — parsing ingredients FR
- _upsert_ingredient() / _insert_recipe_with_ingredients() — insertion DB

Usage (via Celery task) :
    from src.agents.recipe_scout.url_importer import import_recipe_from_url
    recipe_id = await import_recipe_from_url(url, household_id, user_id, session)
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from slugify import slugify

# Reutilisation des fonctions existantes de scrape_marmiton
from src.scripts.scrape_marmiton import (
    _upsert_ingredient,
    extract_json_ld_recipe,
    parse_ingredient_line,
    parse_iso8601_duration,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

IMPORT_QUALITY_SCORE = 0.7
INGREDIENT_CATEGORY_DEFAULT = "other"
MIN_TITLE_LENGTH = 3
MAX_INGREDIENTS = 50


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


async def _fetch_page(url: str) -> str:
    """Fetch une page web avec timeout et user-agent realiste.

    Raises:
        httpx.HTTPStatusError: si le serveur retourne un code >= 400.
        httpx.TimeoutException: si le timeout de 15s est depasse.
    """
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# Fallback HTML (pas de JSON-LD)
# ---------------------------------------------------------------------------


def _extract_fallback_html(html: str, source_url: str) -> dict[str, Any] | None:
    """Extraction basique depuis le HTML quand JSON-LD est absent.

    Extrait :
    - Titre : <h1> ou <title>
    - Description : <meta name="description">
    - Ingredients : premier <ul> ou <ol> avec >= 3 items
    - Photo : premiere <img> avec src contenant un chemin d'image significatif

    Returns:
        Dict au format DB ou None si les donnees minimales manquent.
    """
    soup = BeautifulSoup(html, "lxml")

    # Titre
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
    if len(title) < MIN_TITLE_LENGTH:
        logger.debug("fallback_skip_no_title", url=source_url)
        return None

    # Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = ""
    if meta_desc and meta_desc.get("content"):
        description = str(meta_desc["content"]).strip()[:500]

    # Ingredients — chercher les listes qui ressemblent a des ingredients
    raw_ingredients: list[str] = []
    for list_tag in soup.find_all(["ul", "ol"]):
        items = list_tag.find_all("li")
        texts = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]
        # Heuristique : une liste d'ingredients a entre 3 et 50 items
        # et les items font entre 3 et 200 caracteres
        if 3 <= len(texts) <= MAX_INGREDIENTS:
            valid = [t for t in texts if MIN_TITLE_LENGTH <= len(t) <= 200]
            if len(valid) >= 3:
                raw_ingredients = valid[:MAX_INGREDIENTS]
                break

    if len(raw_ingredients) < 2:
        logger.debug("fallback_skip_few_ingredients", url=source_url, count=len(raw_ingredients))
        return None

    # Photo
    photo_url = None
    for img in soup.find_all("img", src=True):
        src = str(img["src"])
        if (
            any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])
            and len(src) > 10
            and "icon" not in src.lower()
            and "logo" not in src.lower()
        ):
            photo_url = src if src.startswith("http") else None
            if photo_url:
                break

    # Slug
    slug = slugify(title, max_length=200)
    if not slug:
        slug = f"import-{uuid4().hex[:8]}"

    return {
        "title": title,
        "slug": slug,
        "source": "user-import",
        "source_url": source_url,
        "description": description,
        "photo_url": photo_url,
        "instructions": [],
        "servings": 4,
        "prep_time_min": None,
        "cook_time_min": None,
        "difficulty": 2,
        "cuisine_type": None,
        "nutrition": {},
        "tags": ["import-utilisateur"],
        "quality_score": IMPORT_QUALITY_SCORE,
        "raw_ingredients": raw_ingredients,
    }


# ---------------------------------------------------------------------------
# Mapping JSON-LD → format DB (adapte de map_json_ld_to_recipe)
# ---------------------------------------------------------------------------


def _extract_photo(json_ld: dict[str, Any]) -> str | None:
    """Extrait l'URL de la photo depuis le JSON-LD."""
    image = json_ld.get("image")
    if not image:
        return None
    if isinstance(image, str):
        return image
    if isinstance(image, list):
        for img in reversed(image):
            if isinstance(img, str):
                return img
            if isinstance(img, dict):
                return img.get("url") or img.get("contentUrl")
        return None
    if isinstance(image, dict):
        return image.get("url") or image.get("contentUrl")
    return None


def _extract_instructions(json_ld: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrait les instructions depuis le JSON-LD."""
    raw = json_ld.get("recipeInstructions")
    if not raw:
        return []

    steps: list[dict[str, Any]] = []

    if isinstance(raw, str):
        sentences = re.split(r"\.\s+|\n", raw)
        for i, sentence in enumerate(sentences):
            text = sentence.strip(" .")
            if text and len(text) > 5:
                steps.append({"step": i + 1, "text": text})
        return steps[:20]

    if not isinstance(raw, list):
        return []

    step_num = 0
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text and len(text) > 5:
                step_num += 1
                steps.append({"step": step_num, "text": text})
        elif isinstance(item, dict):
            item_type = item.get("@type", "")
            if item_type == "HowToSection":
                for sub in item.get("itemListElement", []):
                    if isinstance(sub, dict):
                        text = (sub.get("text") or sub.get("name") or "").strip()
                        if text and len(text) > 5:
                            step_num += 1
                            steps.append({"step": step_num, "text": text})
            else:
                text = (item.get("text") or item.get("name") or "").strip()
                if text and len(text) > 5:
                    step_num += 1
                    steps.append({"step": step_num, "text": text})

    return steps[:30]


def _parse_servings(recipe_yield: Any) -> int:
    """Parse le nombre de portions depuis recipeYield."""
    if recipe_yield is None:
        return 4
    if isinstance(recipe_yield, int):
        return max(1, min(recipe_yield, 50))
    if isinstance(recipe_yield, list):
        recipe_yield = recipe_yield[0] if recipe_yield else "4"
    text = str(recipe_yield).strip()
    match = re.search(r"(\d+)", text)
    if match:
        return max(1, min(int(match.group(1)), 50))
    return 4


def _extract_nutrition(json_ld: dict[str, Any]) -> dict[str, Any]:
    """Extrait les informations nutritionnelles du JSON-LD."""
    nutrition = json_ld.get("nutrition")
    if not nutrition or not isinstance(nutrition, dict):
        return {}

    def _parse_num(val: Any) -> float | None:
        if val is None:
            return None
        text = str(val).strip()
        match = re.search(r"([\d.]+)", text)
        return float(match.group(1)) if match else None

    return {
        k: v
        for k, v in {
            "calories": _parse_num(nutrition.get("calories")),
            "proteins_g": _parse_num(nutrition.get("proteinContent")),
            "carbs_g": _parse_num(nutrition.get("carbohydrateContent")),
            "fat_g": _parse_num(nutrition.get("fatContent")),
            "fiber_g": _parse_num(nutrition.get("fiberContent")),
        }.items()
        if v is not None
    }


def map_json_ld_to_import(
    json_ld: dict[str, Any],
    source_url: str,
) -> dict[str, Any] | None:
    """Mappe un objet JSON-LD Recipe vers le format DB pour un import utilisateur.

    Moins strict que map_json_ld_to_recipe() du scraper :
    - Photo optionnelle (pas de rejet si absente)
    - Minimum 1 ingredient (au lieu de 3)
    - Instructions optionnelles

    Returns:
        Dict pret pour l'insertion, ou None si le titre est absent.
    """
    title = (json_ld.get("name") or "").strip()
    if not title or len(title) < MIN_TITLE_LENGTH:
        logger.debug("import_skip_no_title", url=source_url)
        return None

    photo_url = _extract_photo(json_ld)
    instructions = _extract_instructions(json_ld)
    raw_ingredients: list[str] = json_ld.get("recipeIngredient") or []
    description = (json_ld.get("description") or "").strip()[:500]
    servings = _parse_servings(json_ld.get("recipeYield"))

    prep_time = parse_iso8601_duration(json_ld.get("prepTime"))
    cook_time = parse_iso8601_duration(json_ld.get("cookTime"))
    total_time_raw = parse_iso8601_duration(json_ld.get("totalTime"))

    if total_time_raw and not prep_time and not cook_time:
        prep_time = max(0, total_time_raw // 3)
        cook_time = max(0, total_time_raw - prep_time)

    prep_time = max(0, prep_time) if prep_time is not None else None
    cook_time = max(0, cook_time) if cook_time is not None else None

    nutrition = _extract_nutrition(json_ld)

    # Cuisine type depuis le JSON-LD
    cuisine_type = None
    cuisine_raw = json_ld.get("recipeCuisine")
    if isinstance(cuisine_raw, list) and cuisine_raw:
        cuisine_type = str(cuisine_raw[0]).strip().lower()
    elif isinstance(cuisine_raw, str) and cuisine_raw.strip():
        cuisine_type = cuisine_raw.strip().lower()

    # Tags
    tags = ["import-utilisateur"]
    category = json_ld.get("recipeCategory")
    if isinstance(category, str) and category.strip():
        tags.append(slugify(category.strip()))
    elif isinstance(category, list):
        for cat in category[:3]:
            if isinstance(cat, str) and cat.strip():
                tags.append(slugify(cat.strip()))

    # Slug
    slug = slugify(title, max_length=200)
    if not slug:
        slug = f"import-{uuid4().hex[:8]}"

    # Detecter la source depuis le domaine
    domain = urlparse(source_url).netloc.lower().replace("www.", "")

    return {
        "title": title,
        "slug": slug,
        "source": "user-import",
        "source_url": source_url,
        "source_domain": domain,
        "description": description,
        "photo_url": photo_url,
        "instructions": instructions,
        "servings": servings,
        "prep_time_min": prep_time,
        "cook_time_min": cook_time,
        "difficulty": 2,
        "cuisine_type": cuisine_type,
        "nutrition": nutrition,
        "tags": tags,
        "quality_score": IMPORT_QUALITY_SCORE,
        "raw_ingredients": raw_ingredients,
    }


# ---------------------------------------------------------------------------
# Insertion DB (adapte de _insert_recipe_with_ingredients)
# ---------------------------------------------------------------------------


async def _insert_imported_recipe(
    session: Any,
    recipe_data: dict[str, Any],
) -> str | None:
    """Insere une recette importee et ses ingredients en base.

    Returns:
        recipe_id (str) si insere, None si doublon.
    """
    from sqlalchemy import text

    title = recipe_data["title"]
    slug = recipe_data["slug"]
    source_url = recipe_data.get("source_url") or ""

    # Verification doublon par source_url OU slug
    result = await session.execute(
        text(
            """
            SELECT id FROM recipes
            WHERE slug = :slug OR (source_url != '' AND source_url = :source_url)
            LIMIT 1
            """
        ),
        {"slug": slug, "source_url": source_url},
    )
    existing = result.fetchone()
    if existing:
        # La recette existe deja — retourner son ID (pas un echec)
        logger.info("import_recipe_already_exists", title=title, slug=slug)
        return str(existing[0])

    raw_ingredients: list[str] = recipe_data.pop("raw_ingredients", [])
    recipe_data.pop("source_domain", None)

    recipe_id = str(uuid4())
    instructions_json = json.dumps(recipe_data["instructions"], ensure_ascii=False)
    nutrition_json = json.dumps(recipe_data.get("nutrition") or {}, ensure_ascii=False)

    await session.execute(
        text(
            """
            INSERT INTO recipes (
                id, title, slug, source, source_url,
                description, photo_url, nutrition,
                instructions, servings,
                prep_time_min, cook_time_min,
                difficulty, cuisine_type,
                tags, quality_score, language,
                created_at, updated_at
            ) VALUES (
                :id, :title, :slug, :source, :source_url,
                :description, :photo_url, CAST(:nutrition AS jsonb),
                CAST(:instructions AS jsonb), :servings,
                :prep_time_min, :cook_time_min,
                :difficulty, :cuisine_type,
                CAST(:tags AS text[]), :quality_score, 'fr',
                NOW(), NOW()
            )
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {
            "id": recipe_id,
            "title": title,
            "slug": slug,
            "source": recipe_data.get("source", "user-import"),
            "source_url": source_url,
            "description": recipe_data.get("description") or "",
            "photo_url": recipe_data.get("photo_url") or "",
            "nutrition": nutrition_json,
            "instructions": instructions_json,
            "servings": recipe_data["servings"],
            "prep_time_min": recipe_data.get("prep_time_min"),
            "cook_time_min": recipe_data.get("cook_time_min"),
            "difficulty": recipe_data.get("difficulty") or 2,
            "cuisine_type": recipe_data.get("cuisine_type"),
            "tags": recipe_data["tags"],
            "quality_score": recipe_data.get("quality_score", IMPORT_QUALITY_SCORE),
        },
    )

    # Verifier que la recette a bien ete inseree (pas de conflit slug)
    result = await session.execute(
        text("SELECT id FROM recipes WHERE slug = :slug LIMIT 1"),
        {"slug": slug},
    )
    row = result.fetchone()
    if not row:
        logger.warning("import_recipe_insert_conflict", slug=slug)
        return None

    actual_recipe_id = str(row[0])

    # Parser et inserer les ingredients
    for position, ingredient_line in enumerate(raw_ingredients[:MAX_INGREDIENTS]):
        parsed_items = parse_ingredient_line(ingredient_line)
        for quantity, unit, canonical_name in parsed_items:
            if not canonical_name:
                continue
            try:
                ingredient_id = await _upsert_ingredient(session, canonical_name)
                await session.execute(
                    text(
                        """
                        INSERT INTO recipe_ingredients
                            (recipe_id, ingredient_id, quantity, unit, notes, position)
                        VALUES (:rid, :iid, :qty, :unit, :notes, :pos)
                        ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                        """
                    ),
                    {
                        "rid": actual_recipe_id,
                        "iid": ingredient_id,
                        "qty": quantity,
                        "unit": unit,
                        "notes": ingredient_line[:200],
                        "pos": position,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "import_ingredient_error",
                    name=canonical_name[:30],
                    line=ingredient_line[:50],
                    error=str(exc),
                )

    await session.commit()
    logger.info(
        "import_recipe_inserted",
        title=title,
        recipe_id=actual_recipe_id,
        ingredients_count=len(raw_ingredients),
    )
    return actual_recipe_id


# ---------------------------------------------------------------------------
# Tracking ownership (user_imported_recipes)
# ---------------------------------------------------------------------------


async def _track_import(
    session: Any,
    recipe_id: str,
    household_id: str,
    user_id: str,
) -> None:
    """Enregistre l'import dans user_imported_recipes pour le tracking."""
    from sqlalchemy import text

    await session.execute(
        text(
            """
            INSERT INTO user_imported_recipes (recipe_id, household_id, imported_by)
            VALUES (:recipe_id, :household_id, :imported_by)
            ON CONFLICT (recipe_id, household_id) DO NOTHING
            """
        ),
        {
            "recipe_id": recipe_id,
            "household_id": household_id,
            "imported_by": user_id,
        },
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------


async def import_recipe_from_url(
    url: str,
    household_id: str,
    user_id: str,
    session_factory: Any,
) -> dict[str, Any]:
    """Importe une recette depuis une URL dans la base de donnees.

    Pipeline :
    1. Fetch la page
    2. Extraire JSON-LD Recipe (ou fallback HTML)
    3. Mapper vers format DB
    4. Inserer recette + ingredients
    5. Tracker l'import (user_imported_recipes)

    Args:
        url: URL de la page contenant la recette.
        household_id: UUID du foyer de l'utilisateur.
        user_id: UUID Supabase de l'utilisateur.
        session_factory: AsyncSessionLocal factory.

    Returns:
        Dict avec recipe_id, title, status, is_new.

    Raises:
        ValueError: si l'URL est invalide ou la page ne contient pas de recette.
        httpx.HTTPStatusError: si le serveur retourne un code >= 400.
    """
    # Validation URL basique
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"URL invalide : {url}")

    logger.info("import_recipe_start", url=url, household_id=household_id)

    # 1. Fetch
    html = await _fetch_page(url)

    # 2. Extraction JSON-LD
    json_ld = extract_json_ld_recipe(html)
    recipe_data: dict[str, Any] | None = None

    if json_ld:
        recipe_data = map_json_ld_to_import(json_ld, url)
        logger.info("import_json_ld_found", url=url, has_data=recipe_data is not None)

    # 3. Fallback HTML si pas de JSON-LD ou mapping echoue
    if not recipe_data:
        recipe_data = _extract_fallback_html(html, url)
        if recipe_data:
            logger.info("import_fallback_html_used", url=url)

    if not recipe_data:
        raise ValueError(
            "Impossible d'extraire une recette depuis cette URL. "
            "La page ne contient pas de donnees structurees (JSON-LD) "
            "ni de contenu HTML exploitable."
        )

    # 4. Insertion DB
    async with session_factory() as session:
        recipe_id = await _insert_imported_recipe(session, recipe_data)

        if not recipe_id:
            raise ValueError("Echec de l'insertion en base (conflit slug inattendu).")

        # 5. Tracker l'import
        try:
            await _track_import(session, recipe_id, household_id, user_id)
        except Exception as exc:
            # Ne pas bloquer si la table n'existe pas encore (migration pas jouee)
            logger.warning("import_track_error", error=str(exc), recipe_id=recipe_id)

    logger.info(
        "import_recipe_complete",
        recipe_id=recipe_id,
        title=recipe_data["title"],
        url=url,
    )

    return {
        "recipe_id": recipe_id,
        "title": recipe_data["title"],
        "source_url": url,
        "status": "imported",
    }
