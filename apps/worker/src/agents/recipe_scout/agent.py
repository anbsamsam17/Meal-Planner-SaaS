"""
Agent RECIPE_SCOUT — orchestrateur principal du pipeline de collecte.

Classe principale qui orchestre les étapes dans l'ordre :
1. Scraping (Marmiton, Spoonacular, Edamam)
2. Normalisation des ingrédients
3. Déduplication par cosine similarity (pgvector)
4. Validation qualité LLM (Claude)
5. Tagging automatique LLM
6. Embedding (sentence-transformers)
7. Insertion en PostgreSQL

Architecture :
- La méthode `run()` est le point d'entrée unique (convention ROADMAP)
- Chaque étape peut échouer indépendamment sans bloquer les suivantes
- Les erreurs sont loggées et comptabilisées dans les statistiques de run
- Le service_role Supabase est utilisé pour bypass RLS (agents IA)

TODO Phase 1 mature :
- Intégration des statistiques dans une table de monitoring
- Support LangGraph pour l'orchestration avancée
- Retry par recette avec circuit breaker Claude
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.recipe_scout.connectors.edamam import EdamamClient
from src.agents.recipe_scout.connectors.spoonacular import SpoonacularClient
from src.agents.recipe_scout.dedup import compute_batch_dedup, is_recipe_duplicate
from src.agents.recipe_scout.normalizer import normalize_recipe_ingredients
from src.agents.recipe_scout.scrapers.base import RawRecipe
from src.agents.recipe_scout.scrapers.marmiton import MarmitonScraper
from src.agents.recipe_scout.tagger import merge_tags_to_list, tag_recipe
from src.agents.recipe_scout.validator import validate_recipe_quality


@dataclass
class ScoutRunStats:
    """Statistiques d'un run du RECIPE_SCOUT."""

    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    total_scraped: int = 0
    total_normalized: int = 0
    total_deduplicated: int = 0
    total_validated: int = 0
    total_rejected_quality: int = 0
    total_inserted: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Durée totale du run en secondes."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Taux de recettes insérées par rapport au total scrapé."""
        if self.total_scraped == 0:
            return 0.0
        return self.total_inserted / self.total_scraped


def _gemini_available() -> bool:
    """
    Vérifie si la clé API Gemini est disponible et non-factice.

    Retourne False si GOOGLE_AI_API_KEY est absente, vide, ou égale à
    des valeurs placeholder connues ("dummy", "placeholder").
    Utilisé pour activer le mode dégradé sans crash.
    """
    key = os.getenv("GOOGLE_AI_API_KEY", "").strip()
    return bool(key) and key.lower() not in ("dummy", "placeholder", "your_key")


class RecipeScoutAgent:
    """
    Agent RECIPE_SCOUT — collecte, enrichit et stocke les recettes.

    Chaque instance est créée par une tâche Celery et utilisée pour
    un seul run complet. L'instance n'est pas réutilisée entre les runs.

    Usage :
        agent = RecipeScoutAgent(
            db_url=settings.DATABASE_URL,
            marmiton_urls=["https://www.marmiton.org/recettes/..."],
            sources=["marmiton", "spoonacular"],
        )
        stats = await agent.run()

    Mode dégradé (sans Gemini) :
        Si GOOGLE_AI_API_KEY est absente ou invalide, la validation et le
        tagging LLM sont skippés gracieusement :
        - quality_score = 0.7 attribué par défaut (seuil d'acceptation dépassé)
        - tags basiques extraits depuis les données brutes du scraping
        - Un log WARNING est émis au démarrage (pas de crash)
    """

    def __init__(
        self,
        db_url: str | None = None,
        marmiton_urls: list[str] | None = None,
        max_recipes_per_source: int = 100,
        sources: list[str] | None = None,
    ) -> None:
        """
        Initialise l'agent RECIPE_SCOUT.

        Args:
            db_url: URL de connexion PostgreSQL (service_role pour bypass RLS).
            marmiton_urls: URLs Marmiton à scraper. Si None, les URLs sont
                          générées par le spider (pages de listing).
            max_recipes_per_source: Limite de recettes par source par run.
            sources: Sources à activer (par défaut : toutes disponibles).
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "")
        self.marmiton_urls = marmiton_urls or []
        self.max_recipes_per_source = max_recipes_per_source
        self.sources = sources or ["marmiton", "spoonacular", "edamam"]
        # Lazy import — sentence-transformers est optionnel (trop lourd pour Railway)
        try:
            from src.agents.recipe_scout.embedder import RecipeEmbedder
            self.embedder = RecipeEmbedder.get_instance()
        except ImportError:
            self.embedder = None
            logger.warning("embedder_unavailable", hint="sentence-transformers non installé — embeddings désactivés")
        # Flag dry_run : les recettes sont scrapées/validées mais pas insérées en DB.
        # Positionné depuis le script manuel ou les tests d'intégration.
        self._dry_run: bool = False
        # Mode dégradé : Gemini non disponible → skip validation + tagging LLM
        self._gemini_available: bool = _gemini_available()
        if not self._gemini_available:
            logger.warning(
                "recipe_scout_degraded_mode",
                reason="GOOGLE_AI_API_KEY absente ou invalide",
                behavior=(
                    "Validation Gemini skippée — quality_score=0.7 par défaut. "
                    "Tags basiques extraits depuis les données brutes."
                ),
            )

    async def run(self) -> ScoutRunStats:
        """
        Exécute le pipeline complet RECIPE_SCOUT.

        Orchestre toutes les étapes dans l'ordre et retourne les statistiques.

        Returns:
            ScoutRunStats avec le bilan du run.
        """
        stats = ScoutRunStats()
        logger.info(
            "recipe_scout_run_start",
            sources=self.sources,
            max_per_source=self.max_recipes_per_source,
        )

        # Connexion DB avec service_role (bypass RLS pour les agents IA)
        engine = create_async_engine(self.db_url, pool_size=5)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            # ---- Étape 1 : Collecte depuis toutes les sources ----
            raw_recipes = await self._collect_all_sources(stats)

            if not raw_recipes:
                logger.warning("recipe_scout_no_recipes_collected")
                return stats

            # ---- Étape 2 : Normalisation ----
            normalized_recipes = self._normalize_recipes(raw_recipes, stats)

            # ---- Étape 3 : Déduplication intra-batch ----
            unique_recipes = await self._dedup_batch(normalized_recipes, stats)

            # ---- Étape 4 → 7 : Validation, tagging, embedding, insertion ----
            async with session_factory() as session:
                for recipe_data in unique_recipes:
                    await self._process_single_recipe(recipe_data, session, stats)

            stats.finished_at = datetime.now()

        except Exception as exc:
            stats.errors.append(f"Erreur fatale du pipeline : {exc}")
            logger.exception("recipe_scout_run_fatal_error")
            stats.finished_at = datetime.now()
        finally:
            await engine.dispose()

        logger.info(
            "recipe_scout_run_complete",
            total_scraped=stats.total_scraped,
            total_inserted=stats.total_inserted,
            rejected_quality=stats.total_rejected_quality,
            deduplicated=stats.total_deduplicated,
            duration_seconds=stats.duration_seconds,
            success_rate=round(stats.success_rate, 3),
            errors_count=len(stats.errors),
        )

        return stats

    async def _collect_all_sources(self, stats: ScoutRunStats) -> list[RawRecipe]:
        """
        Collecte les recettes depuis toutes les sources activées.

        Args:
            stats: Statistiques du run (modifiées en place).

        Returns:
            Liste de toutes les recettes brutes collectées.
        """
        all_recipes: list[RawRecipe] = []

        if "marmiton" in self.sources:
            marmiton_recipes = await self._collect_marmiton()
            all_recipes.extend(marmiton_recipes)
            logger.info("recipe_scout_marmiton", count=len(marmiton_recipes))

        if "spoonacular" in self.sources:
            spoonacular_recipes = await self._collect_spoonacular()
            all_recipes.extend(spoonacular_recipes)
            logger.info("recipe_scout_spoonacular", count=len(spoonacular_recipes))

        if "edamam" in self.sources:
            edamam_recipes = await self._collect_edamam()
            all_recipes.extend(edamam_recipes)
            logger.info("recipe_scout_edamam", count=len(edamam_recipes))

        stats.total_scraped = len(all_recipes)
        return all_recipes

    async def _collect_marmiton(self) -> list[RawRecipe]:
        """Collecte les recettes Marmiton depuis les URLs configurées."""
        scraper = MarmitonScraper()
        recipes: list[RawRecipe] = []

        urls = self.marmiton_urls
        if not urls:
            # Générer des URLs depuis les pages de listing
            urls = scraper.get_listing_urls(
                max_pages=max(1, self.max_recipes_per_source // 10)
            )

        for url in urls[: self.max_recipes_per_source]:
            recipe = scraper.scrape_url(url)
            if recipe and scraper.is_valid_raw_recipe(recipe):
                recipes.append(recipe)
            await asyncio.sleep(0)  # Cède le contrôle entre les URLs

        return recipes

    async def _collect_spoonacular(self) -> list[RawRecipe]:
        """Collecte les recettes depuis l'API Spoonacular."""
        api_key = os.getenv("SPOONACULAR_API_KEY")
        if not api_key:
            logger.warning("recipe_scout_spoonacular_no_key")
            return []

        recipes: list[RawRecipe] = []
        search_terms = ["poulet", "légumes", "pasta", "soupe", "salade", "poisson"]

        try:
            async with SpoonacularClient(api_key=api_key) as client:
                per_term = max(1, self.max_recipes_per_source // len(search_terms))
                for term in search_terms:
                    results = await client.search_recipes(term, max_results=per_term)
                    for result in results:
                        recipe = client.convert_to_raw_recipe(result)
                        recipes.append(recipe)
                    await asyncio.sleep(0.5)  # Throttling Spoonacular
        except Exception as exc:
            logger.error("recipe_scout_spoonacular_error", error=str(exc))

        return recipes[: self.max_recipes_per_source]

    async def _collect_edamam(self) -> list[RawRecipe]:
        """Collecte les recettes depuis l'API Edamam."""
        app_id = os.getenv("EDAMAM_APP_ID")
        app_key = os.getenv("EDAMAM_APP_KEY")
        if not app_id or not app_key:
            logger.warning("recipe_scout_edamam_no_key")
            return []

        recipes: list[RawRecipe] = []
        search_terms = ["chicken", "vegetables", "pasta", "fish", "soup"]

        try:
            async with EdamamClient(app_id=app_id, app_key=app_key) as client:
                per_term = max(1, self.max_recipes_per_source // len(search_terms))
                for term in search_terms:
                    results = await client.search_recipes(term, max_results=per_term)
                    for result in results:
                        recipe = client.convert_to_raw_recipe(result)
                        # Edamam sans instructions → skip (nécessite scraping source)
                        if not recipe.extra.get("requires_scraping"):
                            recipes.append(recipe)
                    await asyncio.sleep(1.0)  # Throttling Edamam
        except Exception as exc:
            logger.error("recipe_scout_edamam_error", error=str(exc))

        return recipes[: self.max_recipes_per_source]

    def _normalize_recipes(
        self, raw_recipes: list[RawRecipe], stats: ScoutRunStats
    ) -> list[dict[str, Any]]:
        """
        Normalise les ingrédients de toutes les recettes.

        Args:
            raw_recipes: Recettes brutes.
            stats: Statistiques (modifiées en place).

        Returns:
            Liste de dicts avec les données normalisées.
        """
        normalized: list[dict[str, Any]] = []

        for recipe in raw_recipes:
            try:
                normalized_ingredients = normalize_recipe_ingredients(
                    recipe.ingredients_raw
                )
                normalized.append(
                    {
                        "raw": recipe,
                        "normalized_ingredients": normalized_ingredients,
                    }
                )
            except Exception as exc:
                logger.warning(
                    "recipe_scout_normalize_error",
                    title=recipe.title[:50],
                    error=str(exc),
                )
                stats.errors.append(f"Normalisation : {recipe.title[:30]} — {exc}")

        stats.total_normalized = len(normalized)
        return normalized

    async def _dedup_batch(
        self,
        normalized_recipes: list[dict[str, Any]],
        stats: ScoutRunStats,
    ) -> list[dict[str, Any]]:
        """
        Déduplique le batch en mémoire avant la déduplication pgvector.

        Phase 1 : déduplication intra-batch (local, sans DB)
        Phase 2 (dans _process_single_recipe) : déduplication inter-batches (pgvector)

        Args:
            normalized_recipes: Recettes normalisées.
            stats: Statistiques.

        Returns:
            Recettes uniques du batch.
        """
        if not normalized_recipes:
            return []

        # Construire les textes pour l'embedding
        texts = []
        for recipe_data in normalized_recipes:
            raw = recipe_data["raw"]
            ingredient_names = [
                ing.canonical_name
                for ing in recipe_data["normalized_ingredients"][:10]
            ]
            text = self.embedder.build_recipe_text(
                title=raw.title,
                ingredients=ingredient_names,
                cuisine_type=raw.cuisine_type,
                tags=raw.tags_raw,
            )
            texts.append(text)

        # Calcul des embeddings en batch
        embeddings = self.embedder.embed_batch(texts)

        # Déduplication locale (O(n²) mais batch < 1000)
        unique_indices = compute_batch_dedup(embeddings)

        # Ajouter les embeddings aux données
        for i, recipe_data in enumerate(normalized_recipes):
            recipe_data["embedding"] = embeddings[i]

        unique_recipes = [normalized_recipes[i] for i in unique_indices]

        dedup_count = len(normalized_recipes) - len(unique_recipes)
        stats.total_deduplicated = dedup_count

        if dedup_count > 0:
            logger.info(
                "recipe_scout_dedup_batch",
                removed=dedup_count,
                remaining=len(unique_recipes),
            )

        return unique_recipes

    async def _process_single_recipe(
        self,
        recipe_data: dict[str, Any],
        session: AsyncSession,
        stats: ScoutRunStats,
    ) -> None:
        """
        Traite une seule recette : validation → tagging → insertion DB.

        Args:
            recipe_data: Dict avec raw, normalized_ingredients, embedding.
            session: Session DB async (service_role).
            stats: Statistiques.
        """
        raw: RawRecipe = recipe_data["raw"]
        embedding: list[float] = recipe_data["embedding"]

        try:
            # ---- Déduplication DB (pgvector) ----
            is_dup = await is_recipe_duplicate(embedding, session, title=raw.title)
            if is_dup:
                stats.total_deduplicated += 1
                return

            # ---- Validation qualité LLM (ou mode dégradé) ----
            if self._gemini_available:
                validation = await validate_recipe_quality(
                    title=raw.title,
                    ingredients=raw.ingredients_raw,
                    instructions=raw.instructions_raw,
                    prep_time_min=raw.prep_time_min,
                    cook_time_min=raw.cook_time_min,
                )
                stats.total_validated += 1

                if not validation.is_valid:
                    stats.total_rejected_quality += 1
                    logger.info(
                        "recipe_scout_rejected",
                        title=raw.title[:50],
                        score=validation.quality_score,
                        reason=validation.rejection_reason,
                    )
                    return

                quality_score = validation.quality_score
            else:
                # Mode dégradé : score par défaut (passe le seuil 0.6)
                quality_score = 0.7
                stats.total_validated += 1
                logger.debug(
                    "recipe_scout_degraded_validation",
                    title=raw.title[:50],
                    quality_score=quality_score,
                )

            # ---- Tagging LLM (ou mode dégradé) ----
            if self._gemini_available:
                tags = await tag_recipe(
                    title=raw.title,
                    ingredients=raw.ingredients_raw,
                    instructions=raw.instructions_raw,
                    prep_time_min=raw.prep_time_min,
                    cook_time_min=raw.cook_time_min,
                    existing_tags=raw.tags_raw,
                )
                tags_list = merge_tags_to_list(tags)
                cuisine_type = tags.cuisine
            else:
                # Mode dégradé : tags basiques depuis les données brutes
                tags_list, cuisine_type = self._build_fallback_tags(raw)

            # ---- Insertion en DB (ou skip si dry_run) ----
            if self._dry_run:
                logger.info(
                    "recipe_scout_dry_run_skip",
                    title=raw.title[:50],
                    quality_score=round(quality_score, 3),
                    tags_count=len(tags_list),
                )
                stats.total_inserted += 1
                return

            await self._insert_recipe(
                session=session,
                raw=raw,
                normalized_ingredients=recipe_data["normalized_ingredients"],
                embedding=embedding,
                quality_score=quality_score,
                cuisine_type=cuisine_type,
                tags=tags_list,
            )
            stats.total_inserted += 1

        except Exception as exc:
            error_msg = f"Traitement recette '{raw.title[:30]}' : {exc}"
            stats.errors.append(error_msg)
            logger.error(
                "recipe_scout_process_error",
                title=raw.title[:50],
                error=str(exc),
            )

    def _build_fallback_tags(self, raw: RawRecipe) -> tuple[list[str], str]:
        """
        Construit des tags basiques depuis les données brutes sans LLM.

        Utilisé en mode dégradé quand GOOGLE_AI_API_KEY est absente.
        Extrait la catégorie de temps depuis prep_time + cook_time,
        et réutilise les tags bruts de la source (ex: tags Marmiton).

        Args:
            raw: Recette brute avec les métadonnées de la source.

        Returns:
            Tuple (tags_list, cuisine_type) prêt pour l'insertion DB.
        """
        total_time = (raw.prep_time_min or 0) + (raw.cook_time_min or 0)

        if total_time < 30:
            time_tag = "temps:rapide"
        elif total_time <= 60:
            time_tag = "temps:normal"
        else:
            time_tag = "temps:long"

        cuisine_type = raw.cuisine_type or "internationale"

        tags_list: list[str] = [
            f"cuisine:{cuisine_type}",
            time_tag,
            "difficulte:moyen",
            "budget:moyen",
        ]
        # Réintégrer les tags bruts de la source (max 5)
        tags_list.extend(raw.tags_raw[:5])

        logger.debug(
            "recipe_scout_fallback_tags",
            title=raw.title[:50],
            cuisine=cuisine_type,
            time_tag=time_tag,
            source_tags_count=len(raw.tags_raw),
        )

        return tags_list, cuisine_type

    async def _insert_recipe(
        self,
        session: AsyncSession,
        raw: RawRecipe,
        normalized_ingredients: list,
        embedding: list[float],
        quality_score: float,
        cuisine_type: str,
        tags: list[str],
    ) -> None:
        """
        Insère une recette et ses embeddings en base PostgreSQL.

        Utilise le service_role (bypass RLS) — les agents IA ont accès total.
        L'insertion est atomique (BEGIN/COMMIT implicite dans la session).

        Tables modifiées :
        - recipes : métadonnées principales
        - recipe_ingredients : ingrédients normalisés
        - recipe_embeddings : vecteur 384 dims

        Args:
            session: Session SQLAlchemy async.
            raw: Recette brute.
            normalized_ingredients: Ingrédients normalisés.
            embedding: Vecteur 384 dims.
            quality_score: Score de qualité LLM.
            cuisine_type: Type de cuisine taggué.
            tags: Tags en liste plate.
        """
        from slugify import slugify
        from sqlalchemy import text

        slug = slugify(raw.title, separator="-", max_length=150)
        total_time = (raw.prep_time_min or 0) + (raw.cook_time_min or 0) or None

        # Embedding au format pgvector
        embedding_str = "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"

        # Insertion dans recipes
        recipe_result = await session.execute(
            text(
                """
                INSERT INTO recipes (
                    title, slug, source, source_url, servings,
                    prep_time_min, cook_time_min,
                    difficulty, cuisine_type, tags, quality_score,
                    instructions
                ) VALUES (
                    :title, :slug, :source, :source_url, :servings,
                    :prep_time_min, :cook_time_min,
                    :difficulty, :cuisine_type, :tags, :quality_score,
                    :instructions
                )
                ON CONFLICT (slug) DO NOTHING
                RETURNING id
                """
            ),
            {
                "title": raw.title,
                "slug": slug,
                "source": raw.source_name,
                "source_url": raw.source_url,
                "servings": raw.servings,
                "prep_time_min": raw.prep_time_min,
                "cook_time_min": raw.cook_time_min,
                # FIX #13 (review Phase 1 2026-04-12) : aligner le mapping sur l'échelle 1-5
                # Anciennement "very_easy":1 → conflit avec CHECK BETWEEN 1 AND 3 du modèle.
                # La DBA doit passer la contrainte à CHECK BETWEEN 1 AND 5 (voir rapport).
                "difficulty": 3 if not raw.difficulty else {
                    "very_easy": 1, "easy": 2, "medium": 3, "hard": 4, "very_hard": 5
                }.get(raw.difficulty, 3),
                "cuisine_type": cuisine_type,
                "tags": tags,
                "quality_score": quality_score,
                "instructions": [
                    {"step": i + 1, "text": step}
                    for i, step in enumerate(raw.instructions_raw)
                ],
            },
        )

        row = recipe_result.mappings().one_or_none()
        if row is None:
            # ON CONFLICT : recette déjà présente (même slug)
            logger.debug("recipe_scout_slug_conflict", slug=slug)
            return

        recipe_id = str(row["id"])

        # FIX #5 (review Phase 1 2026-04-12) : INSERT manquant dans recipe_ingredients
        # Les ingrédients normalisés étaient calculés puis jetés silencieusement.
        # Lookup ou création des ingrédients canoniques, puis INSERT batch dans recipe_ingredients.
        ingredients_inserted = 0
        for position, norm_ing in enumerate(normalized_ingredients):
            canonical_name: str = norm_ing.canonical_name

            # Lookup de l'ingrédient canonique ou création si absent
            ingredient_result = await session.execute(
                text(
                    """
                    INSERT INTO ingredients (canonical_name)
                    VALUES (:canonical_name)
                    ON CONFLICT (canonical_name) DO UPDATE SET canonical_name = EXCLUDED.canonical_name
                    RETURNING id
                    """
                ),
                {"canonical_name": canonical_name},
            )
            ing_row = ingredient_result.mappings().one_or_none()
            if ing_row is None:
                continue

            ingredient_id = str(ing_row["id"])

            # Extraction des champs optionnels selon le modèle NormalizedIngredient
            quantity: float | None = getattr(norm_ing, "quantity", None)
            unit: str | None = getattr(norm_ing, "unit", None)
            notes: str | None = getattr(norm_ing, "notes", None)

            await session.execute(
                text(
                    """
                    INSERT INTO recipe_ingredients (
                        recipe_id, ingredient_id, quantity, unit, notes, position
                    ) VALUES (
                        :recipe_id, :ingredient_id, :quantity, :unit, :notes, :position
                    )
                    ON CONFLICT (recipe_id, position) DO NOTHING
                    """
                ),
                {
                    "recipe_id": recipe_id,
                    "ingredient_id": ingredient_id,
                    "quantity": quantity,
                    "unit": unit,
                    "notes": notes,
                    "position": position,
                },
            )
            ingredients_inserted += 1

        # Insertion dans recipe_embeddings
        # Note OPT #1 : renseigner les colonnes dénormalisées explicitement
        await session.execute(
            text(
                """
                INSERT INTO recipe_embeddings (
                    recipe_id, embedding, tags, total_time_min, cuisine_type
                ) VALUES (
                    :recipe_id, :embedding::vector, :tags, :total_time_min, :cuisine_type
                )
                ON CONFLICT (recipe_id) DO NOTHING
                """
            ),
            {
                "recipe_id": recipe_id,
                "embedding": embedding_str,
                "tags": tags,
                "total_time_min": total_time,
                "cuisine_type": cuisine_type,
            },
        )

        # Transaction unique pour cohérence : rollback si l'une des insertions échoue
        await session.commit()

        logger.info(
            "recipe_scout_inserted",
            recipe_id=recipe_id,
            title=raw.title[:50],
            source=raw.source_name,
            quality_score=round(quality_score, 3),
            ingredients_inserted=ingredients_inserted,
        )
