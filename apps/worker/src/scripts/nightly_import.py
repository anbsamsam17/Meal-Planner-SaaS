"""Protocole nightly d'import de recettes — script autonome et idempotent.

Execute en sequence :
  1. Scraping Marmiton (incremental — ON CONFLICT slug DO NOTHING)
  2. Scraping 750g (incremental)
  3. Nettoyage des tags ingredients parasites
  4. Classification cuisine (francaise / monde)
  5. Tags saisonniers (hiver, printemps, ete, automne)
  6. Tags regime (vegetarien, vegan, sans-porc, halal)
  7. Tags budget (economique, moyen, premium)
  8. Tags style dashboard (gourmand, leger-healthy, proteine)
  9. Backfill embeddings pgvector (recettes sans embedding)
  10. Rapport final

Chaque etape est idempotente — le script peut etre relance sans risque.
Aucune dependance Celery : executable directement via cron ou task scheduler.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db \
    uv run python -m src.scripts.nightly_import

    # Options via variables d'environnement :
    MAX_RECIPES=200          # max par source (defaut: 200)
    SCRAPE_DELAY=2.0         # delai entre requetes HTTP (defaut: 2.0)
    DRY_RUN=true             # simuler sans ecriture (defaut: false)
    LOG_LEVEL=DEBUG           # DEBUG/INFO/WARNING (defaut: INFO)

Scheduling (cron Linux/macOS) :
    0 2 * * * cd /path/to/apps/worker && DATABASE_URL=... uv run python -m src.scripts.nightly_import >> /var/log/nightly_import.log 2>&1

Scheduling (Windows Task Scheduler) :
    Action: uv run python -m src.scripts.nightly_import
    Start in: C:\\path\\to\\apps\\worker
    Trigger: Daily at 02:00
"""

import asyncio
import os
import sys
import time
from typing import Any

from loguru import logger


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>nightly</cyan> — {message}"
        ),
    )


def _get_config() -> dict[str, Any]:
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL manquante")
        sys.exit(1)

    return {
        "database_url": db_url,
        "max_recipes": int(os.getenv("MAX_RECIPES", "200")),
        "scrape_delay": float(os.getenv("SCRAPE_DELAY", "2.0")),
        "dry_run": os.getenv("DRY_RUN", "false").lower() == "true",
    }


# ---------------------------------------------------------------------------
# Etape 1-2 : Scraping (Marmiton + 750g)
# ---------------------------------------------------------------------------

async def _step_scrape_marmiton(config: dict) -> dict[str, int]:
    """Scrape incrementalement Marmiton — seules les nouvelles recettes sont inserees."""
    from src.scripts.scrape_marmiton import run_scrape

    logger.info("step_1_marmiton_start")
    try:
        result = await run_scrape(
            database_url=config["database_url"],
            max_recipes=config["max_recipes"],
            max_pages_per_category=15,
            scrape_delay=config["scrape_delay"],
            dry_run=config["dry_run"],
        )
        stats = result if isinstance(result, dict) else {"inserted": 0, "errors": 0}
        logger.info("step_1_marmiton_done", **stats)
        return stats
    except Exception as exc:
        logger.error(f"step_1_marmiton_error: {exc}")
        return {"inserted": 0, "errors": 1, "error_detail": str(exc)}


async def _step_scrape_750g(config: dict) -> dict[str, int]:
    """Scrape incrementalement 750g — seules les nouvelles recettes sont inserees."""
    from src.scripts.scrape_750g import run_scrape

    logger.info("step_2_750g_start")
    try:
        result = await run_scrape(
            database_url=config["database_url"],
            source_sites=["750g"],
            max_recipes=config["max_recipes"],
            scrape_delay=config["scrape_delay"],
            dry_run=config["dry_run"],
        )
        stats = result if isinstance(result, dict) else {"inserted": 0, "errors": 0}
        logger.info("step_2_750g_done", **stats)
        return stats
    except Exception as exc:
        logger.error(f"step_2_750g_error: {exc}")
        return {"inserted": 0, "errors": 1, "error_detail": str(exc)}


# ---------------------------------------------------------------------------
# Etape 3-8 : Enrichissement SQL (tags, cuisine, nettoyage)
# ---------------------------------------------------------------------------

CLEAN_INGREDIENT_TAGS = """
-- Retirer les tags qui sont des ingredients generiques (parasites)
DO $$
DECLARE
    bad_tag TEXT;
BEGIN
    FOREACH bad_tag IN ARRAY ARRAY[
        'sel', 'poivre', 'oeuf', 'oeufs', 'beurre', 'huile', 'farine',
        'sucre', 'lait', 'creme', 'crème', 'eau', 'ail', 'oignon',
        'persil', 'citron', 'tomate', 'carotte', 'pomme-de-terre',
        'chocolat', 'vanille', 'moutarde', 'vinaigre', 'huile-d-olive',
        'sel-fin', 'poivre-noir', 'beurre-doux'
    ] LOOP
        UPDATE recipes SET tags = array_remove(tags, bad_tag)
        WHERE bad_tag = ANY(tags);
    END LOOP;
END $$;
"""

CLASSIFY_CUISINE = """
-- Cuisine type par defaut pour les recettes sans classification
UPDATE recipes SET cuisine_type = 'française'
WHERE cuisine_type IS NULL AND source IN ('marmiton', '750g');

-- Reclassifier en 'monde' les recettes avec indices internationaux
UPDATE recipes r SET cuisine_type = 'monde'
WHERE cuisine_type = 'française'
  AND (
    r.title ILIKE ANY (ARRAY[
      '%couscous%','%tajine%','%tagine%','%curry%','%tikka%','%masala%',
      '%tandoori%','%naan%','%dal%','%wok%','%chow mein%','%pad thai%',
      '%nems%','%nem%','%bo bun%','%sushi%','%maki%','%ramen%','%miso%',
      '%gyoza%','%tempura%','%tacos%','%burrito%','%guacamole%','%fajitas%',
      '%enchilada%','%pizza%','%risotto%','%pesto%','%carbonara%',
      '%bolognaise%','%paella%','%gazpacho%','%kebab%','%falafel%',
      '%houmous%','%hummus%','%pho%','%spring roll%',
      '%rouleaux de printemps%','%bibimbap%','%kimchi%','%chili con carne%'
    ])
    OR EXISTS (
      SELECT 1 FROM recipe_ingredients ri
      JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id
        AND i.canonical_name ILIKE ANY (ARRAY[
          '%sauce soja%','%gingembre%','%lait de coco%','%curry%',
          '%citronnelle%','%wasabi%','%nori%','%tortilla%','%harissa%',
          '%nuoc mam%','%tahini%','%pâte de curry%'
        ])
    )
  );
"""

TAG_SEASONAL = """
-- HIVER
UPDATE recipes r SET tags = array_append(tags, 'hiver'), updated_at = now()
WHERE NOT ('hiver' = ANY(tags))
  AND (
    EXISTS (
      SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%agneau%','%lamb%','%chou%','%cabbage%','%poireau%','%leek%',
        '%navet%','%turnip%','%panais%','%parsnip%','%kale%','%betterave%',
        '%lentille%','%lentil%','%raclette%','%fondue%'
      ])
    )
    OR r.title ILIKE ANY (ARRAY[
      '%soupe%','%soup%','%potage%','%ragoût%','%stew%','%raclette%',
      '%fondue%','%hotpot%','%chili%'
    ])
  );

-- PRINTEMPS
UPDATE recipes r SET tags = array_append(tags, 'printemps'), updated_at = now()
WHERE NOT ('printemps' = ANY(tags))
  AND (
    EXISTS (
      SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%asperge%','%asparagus%','%petit pois%','%pea%','%fraise%',
        '%strawberr%','%radis%','%radish%','%artichaut%','%artichoke%',
        '%épinard%','%spinach%','%rhubarbe%','%rhubarb%','%fève%','%fenouil%'
      ])
    )
    OR r.title ILIKE ANY (ARRAY['%primavera%','%asperge%','%asparagus%'])
  );

-- ETE
UPDATE recipes r SET tags = array_append(tags, 'ete'), updated_at = now()
WHERE NOT ('ete' = ANY(tags))
  AND (
    EXISTS (
      SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%tomate%','%tomato%','%courgette%','%zucchini%','%aubergine%',
        '%eggplant%','%melon%','%pastèque%','%pêche%','%peach%','%maïs%',
        '%corn%','%concombre%','%cucumber%','%poivron%','%pepper%',
        '%basilic%','%basil%','%menthe%','%mint%','%abricot%','%cerise%',
        '%framboise%'
      ])
    )
    OR r.title ILIKE ANY (ARRAY[
      '%barbecue%','%bbq%','%salade%','%salad%','%gazpacho%','%grillé%',
      '%grilled%'
    ])
  );

-- AUTOMNE
UPDATE recipes r SET tags = array_append(tags, 'automne'), updated_at = now()
WHERE NOT ('automne' = ANY(tags))
  AND (
    EXISTS (
      SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%potiron%','%pumpkin%','%courge%','%squash%','%butternut%',
        '%champignon%','%mushroom%','%châtaigne%','%chestnut%','%pomme%',
        '%apple%','%poire%','%pear%','%figue%','%fig%','%noix%','%walnut%',
        '%noisette%','%hazelnut%','%patate douce%','%sweet potato%',
        '%truffe%','%truffle%'
      ])
    )
    OR r.title ILIKE ANY (ARRAY[
      '%potiron%','%pumpkin%','%champignon%','%mushroom%','%butternut%'
    ])
  );
"""

TAG_DIET = """
-- VEGETARIEN
UPDATE recipes r SET tags = array_append(tags, 'végétarien'), updated_at = now()
WHERE NOT ('végétarien' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
      '%beef%','%boeuf%','%veal%','%veau%','%pork%','%porc%',
      '%lamb%','%agneau%','%chicken%','%poulet%','%turkey%','%dinde%',
      '%duck%','%canard%','%rabbit%','%lapin%','%ham%','%jambon%',
      '%bacon%','%lard%','%sausage%','%saucisse%','%salami%','%chorizo%',
      '%haché%','%steak%','%prosciutto%','%pancetta%','%foie%','%liver%',
      '%fish%','%poisson%','%salmon%','%saumon%','%tuna%','%thon%',
      '%cod%','%cabillaud%','%shrimp%','%crevette%','%lobster%','%homard%',
      '%crab%','%crabe%','%oyster%','%huître%','%mussel%','%moule%',
      '%anchois%','%anchovy%','%sardine%','%squid%','%calmar%',
      '%bouillon de boeuf%','%bouillon de poulet%','%gélatine%','%gelatin%',
      '%merguez%','%lardon%'
    ])
  );

-- VEGAN
UPDATE recipes r SET tags = array_append(tags, 'vegan'), updated_at = now()
WHERE NOT ('vegan' = ANY(tags)) AND 'végétarien' = ANY(tags)
  AND NOT EXISTS (
    SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
      '%egg%','%oeuf%','%milk%','%lait%','%butter%','%beurre%',
      '%cream%','%crème%','%cheese%','%fromage%','%yogurt%','%yaourt%',
      '%ghee%','%honey%','%miel%','%parmesan%','%ricotta%','%mascarpone%',
      '%feta%','%mozzarella%','%cheddar%','%gruyère%','%gruyere%'
    ])
  );

-- SANS-PORC
UPDATE recipes r SET tags = array_append(tags, 'sans-porc'), updated_at = now()
WHERE NOT ('sans-porc' = ANY(tags))
  AND NOT EXISTS (
    SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
      '%pork%','%porc%','%bacon%','%ham%','%jambon%','%lard%','%lardon%',
      '%sausage%','%saucisse%','%chorizo%','%salami%','%pancetta%',
      '%prosciutto%','%mortadella%','%merguez%'
    ])
  );

-- HALAL (sans-porc + sans alcool)
UPDATE recipes r SET tags = array_append(tags, 'halal'), updated_at = now()
WHERE NOT ('halal' = ANY(tags)) AND 'sans-porc' = ANY(tags)
  AND NOT EXISTS (
    SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
      '%wine%','%vin%','%beer%','%bière%','%rum%','%rhum%','%vodka%',
      '%whisky%','%brandy%','%cognac%','%champagne%','%cidre%','%cider%',
      '%sherry%','%porto%','%liqueur%','%kirsch%','%calvados%',
      '%marsala%','%mirin%'
    ])
  );
"""

TAG_BUDGET = """
-- ECONOMIQUE : <= 6 ingredients ET difficulty <= 2
UPDATE recipes r SET tags = array_append(tags, 'économique'), updated_at = now()
WHERE NOT ('économique' = ANY(tags))
  AND COALESCE(r.difficulty, 2) <= 2
  AND (SELECT COUNT(*) FROM recipe_ingredients ri WHERE ri.recipe_id = r.id) <= 6;

-- MOYEN : 7 a 10 ingredients
UPDATE recipes r SET tags = array_append(tags, 'moyen'), updated_at = now()
WHERE NOT ('moyen' = ANY(tags))
  AND (SELECT COUNT(*) FROM recipe_ingredients ri WHERE ri.recipe_id = r.id) BETWEEN 7 AND 10;

-- PREMIUM : > 10 ingredients OU difficulty >= 4
UPDATE recipes r SET tags = array_append(tags, 'premium'), updated_at = now()
WHERE NOT ('premium' = ANY(tags))
  AND (COALESCE(r.difficulty, 1) >= 4
    OR (SELECT COUNT(*) FROM recipe_ingredients ri WHERE ri.recipe_id = r.id) > 10);
"""

TAG_STYLE = """
-- GOURMAND
UPDATE recipes r SET tags = array_append(tags, 'gourmand'), updated_at = now()
WHERE NOT ('gourmand' = ANY(tags))
  AND (
    EXISTS (
      SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%beurre%','%butter%','%crème%','%cream%','%creme%','%fromage%',
        '%cheese%','%chocolat%','%chocolate%','%mascarpone%','%caramel%',
        '%foie gras%','%truffe%'
      ])
    )
    OR r.title ILIKE ANY (ARRAY[
      '%fondant%','%moelleux%','%gratin%','%brownie%','%tiramisu%',
      '%tarte%','%gâteau%','%gateau%','%cake%','%burger%','%lasagne%',
      '%crumble%','%crème brûlée%'
    ])
  );

-- LEGER & HEALTHY
UPDATE recipes r SET tags = array_append(tags, 'léger-healthy'), updated_at = now()
WHERE NOT ('léger-healthy' = ANY(tags))
  AND (
    r.title ILIKE ANY (ARRAY[
      '%salade%','%salad%','%vapeur%','%steam%','%soupe%','%velouté%',
      '%smoothie%','%light%','%léger%','%healthy%','%wrap%','%bowl%',
      '%crudité%','%poké%'
    ])
    OR ('végétarien' = ANY(tags) AND (
      SELECT COUNT(*) FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
      WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
        '%courgette%','%tomate%','%salade%','%laitue%','%concombre%',
        '%épinard%','%brocoli%','%haricot vert%','%carotte%','%poivron%',
        '%avocat%'
      ])
    ) >= 2)
  );

-- PROTEINE
UPDATE recipes r SET tags = array_append(tags, 'protéiné'), updated_at = now()
WHERE NOT ('protéiné' = ANY(tags))
  AND EXISTS (
    SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id = ri.ingredient_id
    WHERE ri.recipe_id = r.id AND i.canonical_name ILIKE ANY (ARRAY[
      '%poulet%','%chicken%','%dinde%','%turkey%','%boeuf%','%beef%',
      '%veau%','%veal%','%agneau%','%lamb%','%canard%','%duck%',
      '%saumon%','%salmon%','%thon%','%tuna%','%cabillaud%','%cod%',
      '%crevette%','%shrimp%','%poisson%','%fish%','%oeuf%','%egg%',
      '%lentille%','%lentil%','%pois chiche%','%chickpea%','%tofu%',
      '%tempeh%','%steak%','%filet%'
    ])
  );
"""


async def _step_enrich_tags(config: dict) -> dict[str, int]:
    """Execute toutes les requetes SQL de tagging en une seule transaction."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    logger.info("step_3_enrichment_start")

    if config["dry_run"]:
        logger.info("[DRY_RUN] skip SQL enrichment")
        return {"tags_applied": 0}

    engine = create_async_engine(config["database_url"])
    total_updated = 0

    sql_blocks = [
        ("clean_ingredient_tags", CLEAN_INGREDIENT_TAGS),
        ("classify_cuisine", CLASSIFY_CUISINE),
        ("tag_seasonal", TAG_SEASONAL),
        ("tag_diet", TAG_DIET),
        ("tag_budget", TAG_BUDGET),
        ("tag_style", TAG_STYLE),
    ]

    try:
        for block_name, sql in sql_blocks:
            async with engine.begin() as conn:
                # Les blocs DO $$ ... END $$ contiennent des ; internes
                # → on les execute en une seule fois, pas de split
                if "$$" in sql:
                    try:
                        await conn.execute(text(sql))
                    except Exception as exc:
                        logger.warning(f"sql_skip: {block_name}: {exc}")
                else:
                    for statement in sql.split(";"):
                        statement = statement.strip()
                        if not statement or statement.startswith("--"):
                            continue
                        try:
                            await conn.execute(text(statement))
                        except Exception as exc:
                            logger.warning(f"sql_skip: {block_name}: {exc}")

            logger.info(f"step_3_{block_name}_done")
    finally:
        await engine.dispose()

    logger.info("step_3_enrichment_done")
    return {"enrichment": "ok"}


# ---------------------------------------------------------------------------
# Etape 9 : Backfill embeddings
# ---------------------------------------------------------------------------

async def _step_backfill_embeddings(config: dict) -> dict[str, int]:
    """Genere les embeddings pgvector pour les recettes qui n'en ont pas."""
    logger.info("step_4_embeddings_start")

    try:
        from src.agents.recipe_scout.embedder import RecipeEmbedder
    except ImportError:
        logger.warning("sentence-transformers non installe — skip embeddings")
        return {"embeddings_inserted": 0, "skipped": True}

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(config["database_url"], pool_size=5)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    embedder = RecipeEmbedder.get_instance()
    embedder.embed_text("init")

    inserted = 0
    errors = 0

    try:
        async with session_factory() as session:
            # Recettes sans embedding
            result = await session.execute(text("""
                SELECT r.id::text, r.title, r.cuisine_type, r.tags,
                       r.prep_time_min, r.cook_time_min
                FROM recipes r
                LEFT JOIN recipe_embeddings re ON re.recipe_id = r.id
                WHERE re.recipe_id IS NULL
                ORDER BY r.created_at ASC
            """))
            recipes = result.mappings().all()

            if not recipes:
                logger.info("step_4_nothing_to_embed")
                await engine.dispose()
                return {"embeddings_inserted": 0}

            logger.info(f"step_4_recipes_to_embed: {len(recipes)}")

            if config["dry_run"]:
                logger.info(f"[DRY_RUN] would embed {len(recipes)} recipes")
                await engine.dispose()
                return {"embeddings_would_insert": len(recipes)}

            batch_size = 32
            for batch_start in range(0, len(recipes), batch_size):
                batch = list(recipes[batch_start:batch_start + batch_size])

                for recipe in batch:
                    try:
                        # Recuperer les ingredients
                        ing_result = await session.execute(
                            text("""
                                SELECT i.canonical_name
                                FROM recipe_ingredients ri
                                JOIN ingredients i ON i.id = ri.ingredient_id
                                WHERE ri.recipe_id = :rid ORDER BY ri.position LIMIT 10
                            """),
                            {"rid": recipe["id"]},
                        )
                        ingredient_names = [r[0] for r in ing_result.fetchall()]

                        tags_raw = recipe.get("tags") or []

                        embed_text = embedder.build_recipe_text(
                            title=recipe["title"],
                            ingredients=ingredient_names,
                            cuisine_type=recipe.get("cuisine_type"),
                            tags=tags_raw[:5] if tags_raw else [],
                        )

                        embedding = embedder.embed_text(embed_text)
                        embedding_str = "[" + ",".join(str(round(v, 6)) for v in embedding) + "]"

                        total_time = (recipe.get("prep_time_min") or 0) + (recipe.get("cook_time_min") or 0) or None

                        await session.execute(
                            text("""
                                INSERT INTO recipe_embeddings (
                                    recipe_id, embedding, tags, total_time_min, cuisine_type
                                ) VALUES (
                                    :recipe_id, CAST(:embedding AS vector),
                                    CAST(:tags AS text[]), :total_time_min, :cuisine_type
                                )
                                ON CONFLICT (recipe_id) DO UPDATE SET
                                    embedding = EXCLUDED.embedding,
                                    tags = EXCLUDED.tags,
                                    total_time_min = EXCLUDED.total_time_min,
                                    cuisine_type = EXCLUDED.cuisine_type,
                                    updated_at = NOW()
                            """),
                            {
                                "recipe_id": recipe["id"],
                                "embedding": embedding_str,
                                "tags": tags_raw if isinstance(tags_raw, list) else [],
                                "total_time_min": total_time,
                                "cuisine_type": recipe.get("cuisine_type"),
                            },
                        )
                        inserted += 1
                    except Exception as exc:
                        logger.warning(f"embed_error: {recipe['title']}: {exc}")
                        errors += 1

                await session.commit()
                logger.info(f"step_4_batch_done: {min(batch_start + batch_size, len(recipes))}/{len(recipes)}")

    finally:
        await engine.dispose()

    logger.info(f"step_4_embeddings_done: inserted={inserted}, errors={errors}")
    return {"embeddings_inserted": inserted, "embeddings_errors": errors}


# ---------------------------------------------------------------------------
# Etape 10 : Rapport
# ---------------------------------------------------------------------------

async def _step_report(config: dict) -> dict[str, Any]:
    """Genere un rapport final avec les comptages."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(config["database_url"])
    report: dict[str, Any] = {}

    try:
        async with engine.begin() as conn:
            # Total recettes par source
            r = await conn.execute(text(
                "SELECT source, COUNT(*) FROM recipes GROUP BY source ORDER BY COUNT(*) DESC"
            ))
            report["sources"] = {row[0]: row[1] for row in r.fetchall()}
            report["total_recipes"] = sum(report["sources"].values())

            # Embeddings
            r = await conn.execute(text("SELECT COUNT(*) FROM recipe_embeddings"))
            report["total_embeddings"] = r.scalar()

            # Cuisine
            r = await conn.execute(text(
                "SELECT cuisine_type, COUNT(*) FROM recipes GROUP BY cuisine_type ORDER BY COUNT(*) DESC"
            ))
            report["cuisine"] = {row[0]: row[1] for row in r.fetchall()}

            # Tags dashboard
            r = await conn.execute(text("""
                SELECT tag, COUNT(*) FROM recipes, UNNEST(tags) AS tag
                WHERE tag IN (
                    'gourmand','léger-healthy','protéiné','végétarien','vegan',
                    'économique','moyen','premium',
                    'hiver','printemps','ete','automne',
                    'halal','sans-porc'
                ) GROUP BY tag ORDER BY COUNT(*) DESC
            """))
            report["tags"] = {row[0]: row[1] for row in r.fetchall()}

            # Temps de preparation
            r = await conn.execute(text("""
                SELECT
                  CASE
                    WHEN COALESCE(prep_time_min,0)+COALESCE(cook_time_min,0) < 20 THEN 'express'
                    WHEN COALESCE(prep_time_min,0)+COALESCE(cook_time_min,0) < 30 THEN 'rapide'
                    WHEN COALESCE(prep_time_min,0)+COALESCE(cook_time_min,0) < 45 THEN 'normal'
                    ELSE 'long'
                  END AS tranche, COUNT(*)
                FROM recipes GROUP BY tranche
            """))
            report["temps"] = {row[0]: row[1] for row in r.fetchall()}

    finally:
        await engine.dispose()

    return report


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------

async def run_nightly(config: dict | None = None) -> dict[str, Any]:
    """Point d'entree principal — execute toutes les etapes en sequence.

    Retourne un dict avec les resultats de chaque etape.
    Peut etre appele depuis Celery, cron, ou directement.
    """
    if config is None:
        config = _get_config()

    start = time.monotonic()
    results: dict[str, Any] = {"dry_run": config["dry_run"]}

    logger.info("=" * 60)
    logger.info("NIGHTLY IMPORT — DEBUT")
    logger.info("=" * 60)

    # Etape 1 : Marmiton
    results["marmiton"] = await _step_scrape_marmiton(config)

    # Etape 2 : 750g
    results["750g"] = await _step_scrape_750g(config)

    # Etape 3-8 : Tags SQL
    results["enrichment"] = await _step_enrich_tags(config)

    # Etape 9 : Embeddings
    results["embeddings"] = await _step_backfill_embeddings(config)

    # Etape 10 : Rapport
    report = await _step_report(config)
    results["report"] = report

    duration = round(time.monotonic() - start, 1)
    results["duration_seconds"] = duration

    # Affichage du rapport
    logger.info("=" * 60)
    logger.info("NIGHTLY IMPORT — RAPPORT FINAL")
    logger.info("=" * 60)
    logger.info(f"  Duree totale        : {duration}s")
    logger.info(f"  Recettes totales    : {report['total_recipes']}")
    for src, cnt in report["sources"].items():
        logger.info(f"    {src}: {cnt}")
    logger.info(f"  Embeddings          : {report['total_embeddings']}")
    logger.info(f"  Cuisine francaise   : {report['cuisine'].get('française', 0)}")
    logger.info(f"  Cuisine du monde    : {report['cuisine'].get('monde', 0)}")
    logger.info(f"  --- Tags dashboard ---")
    for tag, cnt in sorted(report["tags"].items()):
        logger.info(f"    {tag}: {cnt}")
    logger.info(f"  --- Temps ---")
    for tranche, cnt in sorted(report["temps"].items()):
        logger.info(f"    {tranche}: {cnt}")
    logger.info("=" * 60)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _configure_logging()
    asyncio.run(run_nightly())
