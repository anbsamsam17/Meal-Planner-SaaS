"""
translate_recipes.py — Traduction EN → FR des recettes TheMealDB via Gemini 2.0 Flash.

Contexte (2026-04-14) :
  Les 591 recettes importées depuis TheMealDB ont leur titre et description
  en anglais. Ce script traduit les champs `title` et `description` en français.

  Les `instructions` ne sont PAS traduites : elles sont stockées en JSONB
  et leur traduction nécessiterait un budget API plus important (texte long).
  Priorité : title + description couvrent 100 % de l'expérience utilisateur
  visible dans les listes et les cartes de recettes.

Idempotence :
  - La colonne `language` (TEXT, nullable) est utilisée comme flag de tracking.
  - Si language = 'fr', la recette est ignorée.
  - Les recettes sans caractères accentués dans le titre sont considérées EN.
  - Une recette avec un titre contenant des voyelles accentuées est ignorée
    (supposée déjà en français ou multilingue).

Heuristique "anglais" :
  Titre dont aucun caractère appartient à l'ensemble {àâäéèêëîïôùûüç}
  ET qui ne contient pas de mots français courants (dans la liste FRENCH_HINTS).
  Cela évite de retraduire "Boeuf Bourguignon" ou "Crêpes" qui sont déjà FR.

Limites :
  - Gemini free tier : 15 req/min → throttle automatique (wait 4s entre batches)
  - En cas d'erreur sur une recette, elle est skippée et signalée en fin de run.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db \\
    GOOGLE_AI_API_KEY=your_key \\
    uv run python -m src.scripts.translate_recipes

Variables d'environnement :
    DATABASE_URL       Obligatoire — connexion PostgreSQL async (asyncpg).
    GOOGLE_AI_API_KEY  Obligatoire — clé API Google AI Studio.
    BATCH_SIZE         Optionnel — recettes par batch Gemini (défaut: 10).
    DRY_RUN            Optionnel — "true" pour simuler sans écrire en base.
    LOG_LEVEL          Optionnel — DEBUG/INFO/WARNING (défaut: INFO).
    GEMINI_MODEL       Optionnel — modèle Gemini (défaut: gemini-2.0-flash).
"""

import asyncio
import json
import os
import sys
import time
from typing import TypedDict

from google import genai
from google.genai import types
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_BATCH_SIZE = 10
GEMINI_MODEL_DEFAULT = "gemini-2.0-flash"

# Caractères accentués typiquement français — leur présence dans le titre
# signale que la recette est probablement déjà en français.
FRENCH_ACCENT_CHARS = set("àâäéèêëîïôùûüçœæÀÂÄÉÈÊËÎÏÔÙÛÜÇŒÆ")

# Mots français courants dans les titres de recettes — présence = déjà FR.
FRENCH_HINTS: frozenset[str] = frozenset(
    [
        "poulet", "boeuf", "agneau", "porc", "dinde", "canard",
        "saumon", "thon", "crevette", "moule",
        "soupe", "potage", "velouté", "gratin", "tarte", "quiche",
        "rôti", "braisé", "poêlé", "mijoté",
        "crème", "sauce", "vinaigrette",
        "salade", "légumes", "champignon",
        "fromage", "oeufs", "oeuf",
        "fraise", "pomme", "poire",
        "recette", "plat", "entrée",
        "façon", "style",
    ]
)

# Schema JSON attendu de Gemini pour la traduction structurée
TRANSLATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title_fr": {
            "type": "string",
            "description": "Titre de la recette traduit en français (naturel, sans guillemets).",
        },
        "description_fr": {
            "type": "string",
            "description": (
                "Description courte de la recette en français (1-3 phrases). "
                "Retourner une chaîne vide si la description originale est nulle ou absente."
            ),
        },
    },
    "required": ["title_fr", "description_fr"],
}

TRANSLATION_SYSTEM_PROMPT = (
    "Tu es un traducteur culinaire expert. "
    "Traduis les titres et descriptions de recettes de l'anglais vers le français. "
    "Conserve les noms propres des plats qui n'ont pas d'équivalent français "
    "(ex: Pad Thai, Shakshuka, Biryani). "
    "Pour les plats d'origine française ou avec un nom français connu, "
    "utilise le nom français canonique (ex: Beef Bourguignon → Bœuf Bourguignon). "
    "Réponds UNIQUEMENT avec le JSON structuré demandé, jamais en texte libre."
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class RecipeRow(TypedDict):
    id: str
    title: str
    description: str | None
    language: str | None


class TranslationResult(TypedDict):
    title_fr: str
    description_fr: str


# ---------------------------------------------------------------------------
# Configuration logging
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Validation des prérequis
# ---------------------------------------------------------------------------


def _validate_env() -> None:
    """Vérifie les variables d'environnement obligatoires avant de démarrer."""
    missing = []
    if not os.getenv("DATABASE_URL", "").strip():
        missing.append("DATABASE_URL")
    if not os.getenv("GOOGLE_AI_API_KEY", "").strip():
        missing.append("GOOGLE_AI_API_KEY")

    if missing:
        logger.error(
            "translate_env_missing",
            missing=missing,
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://... GOOGLE_AI_API_KEY=...",
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Heuristique : détecter si un titre est en anglais
# ---------------------------------------------------------------------------


def _is_english_title(title: str) -> bool:
    """
    Retourne True si le titre semble en anglais (candidat à la traduction).

    Critères :
    1. Aucun caractère accentué français dans le titre.
    2. Aucun mot-clé français courant dans le titre (insensible à la casse).

    Cette heuristique est intentionnellement conservatrice : en cas de doute,
    la recette est considérée EN et sera traduite (le LLM la préservera si
    elle est déjà en français).
    """
    title_lower = title.lower()

    # Critère 1 : pas d'accents français
    if any(char in FRENCH_ACCENT_CHARS for char in title):
        return False

    # Critère 2 : pas de mots-clés français
    words = set(title_lower.split())
    return not words & FRENCH_HINTS


# ---------------------------------------------------------------------------
# Lecture en base
# ---------------------------------------------------------------------------


async def _fetch_recipes_to_translate(session: AsyncSession) -> list[RecipeRow]:
    """
    Sélectionne les recettes qui doivent être traduites.

    Critères de sélection :
    - language IS NULL ou language != 'fr' (pas encore traduites)
    - source = 'themealdb' (uniquement les recettes importées EN)

    La colonne `language` peut ne pas exister si la migration n'a pas
    encore été appliquée — on la crée via ALTER TABLE si nécessaire.

    Returns:
        Liste de recettes avec id, title, description, language.
    """
    # Création de la colonne language si elle n'existe pas (idempotent)
    await session.execute(
        text(
            """
            ALTER TABLE recipes
            ADD COLUMN IF NOT EXISTS language TEXT DEFAULT NULL
            """
        )
    )
    await session.commit()

    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                title,
                description,
                language
            FROM recipes
            WHERE source = 'themealdb'
              AND (language IS NULL OR language != 'fr')
            ORDER BY created_at ASC
            """
        )
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Client Gemini (singleton)
# ---------------------------------------------------------------------------

_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    """Retourne le client Gemini singleton."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GOOGLE_AI_API_KEY", "").strip()
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ---------------------------------------------------------------------------
# Appel Gemini : traduction d'un batch de recettes
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _translate_single(
    title: str,
    description: str | None,
    model: str,
) -> TranslationResult:
    """
    Traduit title + description d'une seule recette via Gemini.

    Utilise le structured output (response_schema) pour éviter tout parsing fragile.
    Le retry tenacity gère les erreurs transitoires (rate limit, timeout réseau).

    Args:
        title: Titre EN de la recette.
        description: Description EN (peut être None).
        model: Identifiant du modèle Gemini.

    Returns:
        Dict avec title_fr et description_fr.
    """
    client = _get_gemini_client()

    desc_text = description or ""
    prompt = (
        f"Traduis cette recette de l'anglais vers le français.\n\n"
        f"<recipe_content_untrusted>\n"
        f"Titre : {title}\n"
        f"Description : {desc_text}\n"
        f"</recipe_content_untrusted>\n\n"
        "Retourne uniquement le JSON structuré."
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=TRANSLATION_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
            temperature=0.1,
            max_output_tokens=256,
        ),
    )

    raw_text = response.text
    parsed: TranslationResult = json.loads(raw_text)

    # Validation défensive : les champs obligatoires doivent être présents
    if not parsed.get("title_fr"):
        raise ValueError(f"title_fr manquant dans la réponse Gemini : {raw_text[:200]}")

    return parsed


# ---------------------------------------------------------------------------
# Écriture en base : mise à jour d'une recette traduite
# ---------------------------------------------------------------------------


async def _update_recipe_translation(
    session: AsyncSession,
    recipe_id: str,
    title_fr: str,
    description_fr: str,
    dry_run: bool,
) -> None:
    """
    Met à jour title, description et language='fr' pour une recette traduite.

    Idempotent : si la recette est déjà language='fr', l'UPDATE ne change rien.
    Le slug n'est PAS modifié pour éviter de casser les URLs existantes.

    Args:
        session: Session SQLAlchemy async.
        recipe_id: UUID de la recette.
        title_fr: Titre traduit en français.
        description_fr: Description traduite (peut être vide).
        dry_run: Si True, ne fait pas l'écriture.
    """
    if dry_run:
        return

    await session.execute(
        text(
            """
            UPDATE recipes
            SET
                title       = :title_fr,
                description = CASE WHEN :description_fr = '' THEN description
                                   ELSE :description_fr END,
                language    = 'fr',
                updated_at  = now()
            WHERE id = :recipe_id::uuid
              AND (language IS NULL OR language != 'fr')
            """
        ),
        {
            "recipe_id": recipe_id,
            "title_fr": title_fr,
            "description_fr": description_fr,
        },
    )


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


async def main() -> None:
    """Orchestre la traduction par batch de toutes les recettes EN non traduites."""
    _configure_logging()
    _validate_env()

    batch_size = int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    db_url = os.getenv("DATABASE_URL", "")
    model = os.getenv("GEMINI_MODEL", GEMINI_MODEL_DEFAULT)

    if dry_run:
        logger.info("translate_dry_run_mode", hint="Aucune écriture en base.")

    logger.info("translate_start", model=model, batch_size=batch_size)

    # Création de l'engine avec pool minimal (script one-shot)
    engine = create_async_engine(db_url, pool_size=3, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    start_time = time.monotonic()
    total_candidates = 0
    total_english = 0
    total_translated = 0
    total_skipped = 0
    total_errors = 0
    error_ids: list[str] = []

    async with session_factory() as session:
        # Lecture de toutes les recettes candidates
        candidates = await _fetch_recipes_to_translate(session)
        total_candidates = len(candidates)

        if not candidates:
            logger.info("translate_nothing_to_do", hint="Toutes les recettes TheMealDB sont déjà en français.")
            await engine.dispose()
            return

        logger.info(
            "translate_candidates_found",
            total=total_candidates,
        )

        # Filtrage heuristique : ne garder que les titres EN
        english_recipes = [r for r in candidates if _is_english_title(r["title"])]
        skipped_already_fr = total_candidates - len(english_recipes)
        total_english = len(english_recipes)
        total_skipped = skipped_already_fr

        logger.info(
            "translate_heuristic_result",
            english_detected=total_english,
            skipped_looks_french=skipped_already_fr,
        )

        if not english_recipes:
            logger.info("translate_nothing_english", hint="Aucun titre anglais détecté.")
            await engine.dispose()
            return

        # Traitement par batch
        for batch_start in range(0, len(english_recipes), batch_size):
            batch = english_recipes[batch_start : batch_start + batch_size]
            batch_end = min(batch_start + batch_size, len(english_recipes))

            logger.info(
                "translate_batch_start",
                batch=f"{batch_end}/{total_english}",
            )

            for recipe in batch:
                recipe_id: str = recipe["id"]
                title: str = recipe["title"]
                description: str | None = recipe.get("description")

                try:
                    result = await _translate_single(
                        title=title,
                        description=description,
                        model=model,
                    )

                    logger.debug(
                        "translate_recipe_ok",
                        id=recipe_id[:8],
                        title_en=title[:40],
                        title_fr=result["title_fr"][:40],
                    )

                    await _update_recipe_translation(
                        session=session,
                        recipe_id=recipe_id,
                        title_fr=result["title_fr"],
                        description_fr=result.get("description_fr", ""),
                        dry_run=dry_run,
                    )
                    total_translated += 1

                except Exception as exc:
                    logger.error(
                        "translate_recipe_error",
                        id=recipe_id[:8],
                        title=title[:40],
                        error=str(exc)[:120],
                    )
                    total_errors += 1
                    error_ids.append(recipe_id)

            # Commit par batch pour limiter la taille de transaction
            if not dry_run:
                await session.commit()
                logger.debug("translate_batch_committed", batch_end=batch_end)

            # Throttle : Gemini free tier = 15 req/min → 4s entre batches de 10
            # Évite le 429 ResourceExhausted sans attente inutile pour les petits batches
            if batch_end < total_english:
                await asyncio.sleep(4)

    await engine.dispose()

    # ---- Rapport final ----
    elapsed = time.monotonic() - start_time
    logger.info("=" * 60)
    logger.info("RAPPORT TRADUCTION RECETTES")
    logger.info(f"  Durée                 : {elapsed:.1f}s")
    logger.info(f"  Candidats lus (EN)    : {total_candidates}")
    logger.info(f"  Filtrés heuristique   : {total_skipped} (déjà FR ou accentués)")
    logger.info(f"  Recettes anglaises    : {total_english}")
    logger.info(f"  Traduites avec succès : {total_translated}")
    logger.info(f"  Erreurs               : {total_errors}")
    if dry_run:
        logger.info("  Mode DRY_RUN — aucune écriture en base.")
    if error_ids:
        logger.warning("translate_errors_detail", ids=error_ids[:20])
    logger.info("=" * 60)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
