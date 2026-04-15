"""Rapport qualite et couverture du pipeline d'import de recettes.

Analyse la base de donnees PostgreSQL et genere un rapport complet sur :
- Vue d'ensemble (totaux, par source, par langue)
- Qualite (quality_score, completude des champs)
- Couverture des tags
- Traduction (repartition par langue)
- Embeddings (couverture)
- Ingredients (diversite, mapping OFF)
- Diversite culinaire (cuisine, difficulte, temps)

Le rapport est affiche en terminal (stdout) ET sauvegarde en JSON.

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://user:pass@host/db \\
    uv run python -m src.scripts.pipeline_report

Variables d'environnement :
    DATABASE_URL     Obligatoire - connexion PostgreSQL async (asyncpg).
    OUTPUT_FILE      Optionnel - chemin du rapport JSON (defaut : pipeline_report.json).
    LOG_LEVEL        Optionnel - DEBUG/INFO/WARNING (defaut : INFO).
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

BAR_WIDTH = 10
REPORT_SEPARATOR = "\u2550" * 60  # ══════...

TAG_CATEGORIES: dict[str, list[str]] = {
    "cuisine": [
        "francaise",
        "française",
        "italienne",
        "japonaise",
        "mexicaine",
        "indienne",
        "thaïlandaise",
        "chinoise",
        "méditerranéenne",
        "coréenne",
        "vietnamienne",
        "américaine",
        "grecque",
        "espagnole",
        "libanaise",
        "marocaine",
        "internationale",
        "européenne",
        "allemande",
        "britannique",
        "cajun",
        "caraïbéenne",
        "moyen-orientale",
        "est-européenne",
    ],
    "diet": [
        "végétarien",
        "vegan",
        "sans-gluten",
        "sans-lactose",
        "healthy",
        "low-carb",
        "keto",
        "paléo",
        "halal",
        "casher",
    ],
    "saison": [
        "printemps",
        "été",
        "automne",
        "hiver",
        "toute-saison",
    ],
    "budget": [
        "économique",
        "budget",
        "premium",
    ],
    "temps": [
        "express",
        "rapide",
        "long",
    ],
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Configure loguru avec sortie console structuree."""
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
    """Verifie que DATABASE_URL est definie.

    Returns:
        La chaine DATABASE_URL.

    Raises:
        SystemExit si la variable est manquante.
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
# Requetes SQL — chaque fonction retourne un dict de metriques
# ---------------------------------------------------------------------------


async def _query_overview(engine: AsyncEngine) -> dict[str, Any]:
    """Vue d'ensemble : totaux recettes, ingredients, embeddings."""
    async with engine.connect() as conn:
        # Total recettes
        row = (await conn.execute(text("SELECT COUNT(*) FROM recipes"))).scalar_one()
        total_recipes = int(row)

        # Par source
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(source, 'unknown') AS src, COUNT(*) AS cnt "
                    "FROM recipes GROUP BY source ORDER BY cnt DESC"
                )
            )
        ).fetchall()
        by_source: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Par langue
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(language, 'NULL') AS lang, COUNT(*) AS cnt "
                    "FROM recipes GROUP BY language ORDER BY cnt DESC"
                )
            )
        ).fetchall()
        by_language: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Total ingredients uniques
        row = (await conn.execute(text("SELECT COUNT(*) FROM ingredients"))).scalar_one()
        total_ingredients = int(row)

        # Total recipe_ingredients liens
        row = (await conn.execute(text("SELECT COUNT(*) FROM recipe_ingredients"))).scalar_one()
        total_recipe_ingredients = int(row)

        # Total embeddings
        row = (await conn.execute(text("SELECT COUNT(*) FROM recipe_embeddings"))).scalar_one()
        total_embeddings = int(row)

    return {
        "total_recipes": total_recipes,
        "by_source": by_source,
        "by_language": by_language,
        "total_ingredients": total_ingredients,
        "total_recipe_ingredients": total_recipe_ingredients,
        "total_embeddings": total_embeddings,
    }


async def _query_quality(engine: AsyncEngine) -> dict[str, Any]:
    """Metriques de qualite : distribution quality_score, completude."""
    async with engine.connect() as conn:
        # Distribution quality_score par tranches
        rows = (
            await conn.execute(
                text(
                    """
            SELECT
                CASE
                    WHEN quality_score < 0.6 THEN '<0.6'
                    WHEN quality_score < 0.7 THEN '0.6-0.7'
                    WHEN quality_score < 0.8 THEN '0.7-0.8'
                    WHEN quality_score < 0.9 THEN '0.8-0.9'
                    ELSE '0.9-1.0'
                END AS bucket,
                COUNT(*) AS cnt
            FROM recipes
            WHERE quality_score IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
            """
                )
            )
        ).fetchall()
        score_distribution: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Score moyen global
        row = (
            await conn.execute(
                text(
                    "SELECT ROUND(AVG(quality_score)::numeric, 3) FROM recipes "
                    "WHERE quality_score IS NOT NULL"
                )
            )
        ).scalar_one_or_none()
        avg_score = float(row) if row is not None else 0.0

        # Score moyen par source
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(source, 'unknown'), ROUND(AVG(quality_score)::numeric, 3) "
                    "FROM recipes WHERE quality_score IS NOT NULL "
                    "GROUP BY source ORDER BY source"
                )
            )
        ).fetchall()
        avg_by_source: dict[str, float] = {str(r[0]): float(r[1]) for r in rows}

        # Total recettes (pour les pourcentages)
        total = int((await conn.execute(text("SELECT COUNT(*) FROM recipes"))).scalar_one())

        # Sans photo
        no_photo = int(
            (
                await conn.execute(
                    text("SELECT COUNT(*) FROM recipes WHERE photo_url IS NULL OR photo_url = ''")
                )
            ).scalar_one()
        )

        # Sans nutrition
        no_nutrition = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM recipes "
                        "WHERE nutrition IS NULL OR nutrition::text = '{}' OR nutrition::text = 'null'"
                    )
                )
            ).scalar_one()
        )

        # Sans description
        no_description = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM recipes WHERE description IS NULL OR description = ''"
                    )
                )
            ).scalar_one()
        )

        # Sans instructions detaillees (NULL, vide, ou moins de 2 etapes)
        no_instructions = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM recipes "
                        "WHERE instructions IS NULL "
                        "   OR instructions::text = '[]' "
                        "   OR instructions::text = 'null' "
                        "   OR jsonb_array_length(instructions) < 2"
                    )
                )
            ).scalar_one()
        )

    return {
        "avg_score": avg_score,
        "avg_by_source": avg_by_source,
        "score_distribution": score_distribution,
        "total": total,
        "no_photo": no_photo,
        "no_nutrition": no_nutrition,
        "no_description": no_description,
        "no_instructions": no_instructions,
    }


async def _query_tags(engine: AsyncEngine) -> dict[str, Any]:
    """Couverture et distribution des tags."""
    async with engine.connect() as conn:
        total = int((await conn.execute(text("SELECT COUNT(*) FROM recipes"))).scalar_one())

        # Recettes sans aucun tag
        no_tags = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM recipes "
                        "WHERE tags IS NULL OR tags = '[]'::jsonb OR jsonb_array_length(tags) = 0"
                    )
                )
            ).scalar_one()
        )

        # Explosion de tous les tags avec comptage
        rows = (
            await conn.execute(
                text(
                    "SELECT tag, COUNT(*) AS cnt "
                    "FROM recipes, jsonb_array_elements_text(tags) AS tag "
                    "GROUP BY tag ORDER BY cnt DESC"
                )
            )
        ).fetchall()
        tag_counts: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Calculer la couverture par categorie de tag
        coverage: dict[str, int] = {}
        for category, keywords in TAG_CATEGORIES.items():
            # Construire un filtre : au moins un tag de la categorie
            keyword_conditions = " OR ".join(f"tag = '{kw}'" for kw in keywords)
            if not keyword_conditions:
                coverage[category] = 0
                continue
            query = text(
                f"SELECT COUNT(DISTINCT r.id) FROM recipes r, "
                f"jsonb_array_elements_text(r.tags) AS tag "
                f"WHERE {keyword_conditions}"
            )
            row = (await conn.execute(query)).scalar_one()
            coverage[category] = int(row)

    return {
        "total": total,
        "no_tags": no_tags,
        "tag_counts": tag_counts,
        "coverage": coverage,
    }


async def _query_translation(engine: AsyncEngine) -> dict[str, Any]:
    """Repartition par langue."""
    async with engine.connect() as conn:
        total = int((await conn.execute(text("SELECT COUNT(*) FROM recipes"))).scalar_one())

        fr_count = int(
            (
                await conn.execute(text("SELECT COUNT(*) FROM recipes WHERE language = 'fr'"))
            ).scalar_one()
        )

        en_count = int(
            (
                await conn.execute(text("SELECT COUNT(*) FROM recipes WHERE language = 'en'"))
            ).scalar_one()
        )

        null_count = int(
            (
                await conn.execute(text("SELECT COUNT(*) FROM recipes WHERE language IS NULL"))
            ).scalar_one()
        )

        # Autres langues
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(language, 'NULL') AS lang, COUNT(*) AS cnt "
                    "FROM recipes WHERE language NOT IN ('fr', 'en') OR language IS NULL "
                    "GROUP BY language ORDER BY cnt DESC"
                )
            )
        ).fetchall()
        other_languages: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

    return {
        "total": total,
        "fr": fr_count,
        "en": en_count,
        "null": null_count,
        "other": other_languages,
    }


async def _query_embeddings(engine: AsyncEngine) -> dict[str, Any]:
    """Couverture des embeddings."""
    async with engine.connect() as conn:
        total_recipes = int((await conn.execute(text("SELECT COUNT(*) FROM recipes"))).scalar_one())
        total_embeddings = int(
            (await conn.execute(text("SELECT COUNT(*) FROM recipe_embeddings"))).scalar_one()
        )
        # Recettes sans embedding (orphelines)
        orphan_count = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM recipes r "
                        "WHERE NOT EXISTS ("
                        "  SELECT 1 FROM recipe_embeddings re WHERE re.recipe_id = r.id"
                        ")"
                    )
                )
            ).scalar_one()
        )

    return {
        "total_recipes": total_recipes,
        "total_embeddings": total_embeddings,
        "orphan_count": orphan_count,
    }


async def _query_ingredients(engine: AsyncEngine) -> dict[str, Any]:
    """Statistiques sur les ingredients."""
    async with engine.connect() as conn:
        total = int((await conn.execute(text("SELECT COUNT(*) FROM ingredients"))).scalar_one())

        # Distribution par categorie
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(category, 'unknown') AS cat, COUNT(*) AS cnt "
                    "FROM ingredients GROUP BY category ORDER BY cnt DESC"
                )
            )
        ).fetchall()
        by_category: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Top 20 ingredients les plus utilises
        rows = (
            await conn.execute(
                text(
                    "SELECT i.canonical_name, COUNT(ri.recipe_id) AS cnt "
                    "FROM recipe_ingredients ri "
                    "JOIN ingredients i ON i.id = ri.ingredient_id "
                    "GROUP BY i.canonical_name "
                    "ORDER BY cnt DESC LIMIT 20"
                )
            )
        ).fetchall()
        top_ingredients: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Mapping Open Food Facts
        mapped_off = int(
            (
                await conn.execute(
                    text("SELECT COUNT(*) FROM ingredients WHERE off_id IS NOT NULL")
                )
            ).scalar_one()
        )

        # Distribution off_match_confidence
        rows = (
            await conn.execute(
                text(
                    """
            SELECT
                CASE
                    WHEN off_match_confidence < 0.5 THEN '<0.5'
                    WHEN off_match_confidence < 0.7 THEN '0.5-0.7'
                    WHEN off_match_confidence < 0.9 THEN '0.7-0.9'
                    ELSE '0.9-1.0'
                END AS bucket,
                COUNT(*) AS cnt
            FROM ingredients
            WHERE off_match_confidence IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
            """
                )
            )
        ).fetchall()
        off_confidence_dist: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

    return {
        "total": total,
        "by_category": by_category,
        "top_ingredients": top_ingredients,
        "mapped_off": mapped_off,
        "off_confidence_distribution": off_confidence_dist,
    }


async def _query_diversity(engine: AsyncEngine) -> dict[str, Any]:
    """Diversite : cuisine, difficulte, temps, creation par mois."""
    async with engine.connect() as conn:
        # Distribution par cuisine_type (top 15)
        rows = (
            await conn.execute(
                text(
                    "SELECT COALESCE(cuisine_type, 'non defini') AS ct, COUNT(*) AS cnt "
                    "FROM recipes GROUP BY cuisine_type ORDER BY cnt DESC LIMIT 15"
                )
            )
        ).fetchall()
        by_cuisine: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Distribution par difficulte
        rows = (
            await conn.execute(
                text(
                    "SELECT difficulty, COUNT(*) AS cnt "
                    "FROM recipes WHERE difficulty IS NOT NULL "
                    "GROUP BY difficulty ORDER BY difficulty"
                )
            )
        ).fetchall()
        by_difficulty: dict[int, int] = {int(r[0]): int(r[1]) for r in rows}

        # Distribution par tranche de temps total
        rows = (
            await conn.execute(
                text(
                    """
            SELECT
                CASE
                    WHEN total_time_min IS NULL THEN 'inconnu'
                    WHEN total_time_min < 30 THEN 'rapide (<30 min)'
                    WHEN total_time_min <= 60 THEN 'normal (30-60 min)'
                    ELSE 'long (>60 min)'
                END AS bucket,
                COUNT(*) AS cnt
            FROM recipes
            GROUP BY bucket
            ORDER BY bucket
            """
                )
            )
        ).fetchall()
        by_time: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

        # Recettes par mois de creation
        rows = (
            await conn.execute(
                text(
                    "SELECT TO_CHAR(created_at, 'YYYY-MM') AS month, COUNT(*) AS cnt "
                    "FROM recipes WHERE created_at IS NOT NULL "
                    "GROUP BY month ORDER BY month"
                )
            )
        ).fetchall()
        by_month: dict[str, int] = {str(r[0]): int(r[1]) for r in rows}

    return {
        "by_cuisine": by_cuisine,
        "by_difficulty": by_difficulty,
        "by_time": by_time,
        "by_month": by_month,
    }


# ---------------------------------------------------------------------------
# Formatage terminal
# ---------------------------------------------------------------------------


def _pct(value: int, total: int) -> str:
    """Formatte un pourcentage. Retourne '0.0%' si total == 0."""
    if total == 0:
        return "0.0%"
    return f"{value / total * 100:.1f}%"


def _bar(value: int, total: int, width: int = BAR_WIDTH) -> str:
    """Genere une barre de progression texte avec caracteres pleins et vides."""
    if total == 0:
        return "\u2591" * width
    filled = round(value / total * width)
    filled = min(filled, width)
    return "\u2593" * filled + "\u2591" * (width - filled)


def _fmt_num(n: int) -> str:
    """Formatte un nombre avec separateur de milliers."""
    return f"{n:,}".replace(",", "\u202f")


DIFFICULTY_LABELS: dict[int, str] = {
    1: "tres facile",
    2: "facile",
    3: "moyen",
    4: "difficile",
    5: "tres difficile",
}


def _render_terminal(report: dict[str, Any]) -> str:
    """Construit le rapport texte pour affichage terminal."""
    lines: list[str] = []
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("")
    lines.append(REPORT_SEPARATOR)
    lines.append(f"       PIPELINE QUALITY REPORT — {now_str}")
    lines.append(REPORT_SEPARATOR)

    # --- Vue d'ensemble ---
    ov = report["overview"]
    total = ov["total_recipes"]
    lines.append("")
    lines.append("  VUE D'ENSEMBLE")
    lines.append(f"  Recettes totales:          {_fmt_num(total)}")
    lines.append("  Par source:")
    for src, cnt in ov["by_source"].items():
        lines.append(f"    {src:<24} {_fmt_num(cnt):>6}  ({_pct(cnt, total)})")
    lines.append("  Par langue:")
    for lang, cnt in ov["by_language"].items():
        lines.append(f"    {lang:<24} {_fmt_num(cnt):>6}  ({_pct(cnt, total)})")
    lines.append(f"  Ingredients uniques:       {_fmt_num(ov['total_ingredients'])}")
    lines.append(f"  Liens recette-ingredient:  {_fmt_num(ov['total_recipe_ingredients'])}")
    lines.append(
        f"  Embeddings:                {_fmt_num(ov['total_embeddings'])}  "
        f"({_pct(ov['total_embeddings'], total)})"
    )

    # --- Qualite ---
    q = report["quality"]
    lines.append("")
    lines.append("  QUALITE")
    lines.append(f"  Quality score moyen:       {q['avg_score']:.3f}")
    lines.append("  Score moyen par source:")
    for src, avg in q["avg_by_source"].items():
        lines.append(f"    {src:<24} {avg:.3f}")
    lines.append("  Distribution:")
    # Ordre stable des buckets
    bucket_order = ["<0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
    for bucket in bucket_order:
        cnt = q["score_distribution"].get(bucket, 0)
        bar = _bar(cnt, q["total"])
        lines.append(f"    [{bucket:<7}]  {bar}  {_fmt_num(cnt):>6} ({_pct(cnt, q['total'])})")
    lines.append("")
    lines.append(
        f"  Sans photo:                {_fmt_num(q['no_photo']):>6}  "
        f"({_pct(q['no_photo'], q['total'])})"
    )
    lines.append(
        f"  Sans nutrition:            {_fmt_num(q['no_nutrition']):>6}  "
        f"({_pct(q['no_nutrition'], q['total'])})"
    )
    lines.append(
        f"  Sans description:          {_fmt_num(q['no_description']):>6}  "
        f"({_pct(q['no_description'], q['total'])})"
    )
    lines.append(
        f"  Sans instructions (<2):    {_fmt_num(q['no_instructions']):>6}  "
        f"({_pct(q['no_instructions'], q['total'])})"
    )

    # --- Tags ---
    t = report["tags"]
    lines.append("")
    lines.append("  TAGS")
    for category, cnt in t["coverage"].items():
        lines.append(f"  Avec tags {category:<12}  {_fmt_num(cnt):>6}  ({_pct(cnt, t['total'])})")
    lines.append(
        f"  Sans aucun tag:            {_fmt_num(t['no_tags']):>6}  "
        f"({_pct(t['no_tags'], t['total'])})"
    )
    lines.append("")
    lines.append("  Top 20 tags:")
    for tag, cnt in list(t["tag_counts"].items())[:20]:
        lines.append(f"    {tag:<24} {_fmt_num(cnt):>6}")

    # --- Traduction ---
    tr = report["translation"]
    lines.append("")
    lines.append("  TRADUCTION")
    lines.append(
        f"  Francais (fr):             {_fmt_num(tr['fr']):>6}  ({_pct(tr['fr'], tr['total'])})"
    )
    lines.append(
        f"  Anglais (en):              {_fmt_num(tr['en']):>6}  ({_pct(tr['en'], tr['total'])})"
    )
    lines.append(
        f"  Non defini (NULL):         {_fmt_num(tr['null']):>6}  ({_pct(tr['null'], tr['total'])})"
    )
    other_count = sum(cnt for lang, cnt in tr["other"].items() if lang != "NULL")
    if other_count > 0:
        lines.append(f"  Autres langues:            {_fmt_num(other_count):>6}")

    # --- Embeddings ---
    emb = report["embeddings"]
    lines.append("")
    lines.append("  EMBEDDINGS")
    lines.append(
        f"  Avec embedding:            {_fmt_num(emb['total_embeddings']):>6}  "
        f"({_pct(emb['total_embeddings'], emb['total_recipes'])})"
    )
    lines.append(
        f"  Sans embedding:            {_fmt_num(emb['orphan_count']):>6}  "
        f"({_pct(emb['orphan_count'], emb['total_recipes'])})"
    )

    # --- Ingredients ---
    ing = report["ingredients"]
    lines.append("")
    lines.append("  INGREDIENTS")
    lines.append(f"  Total uniques:             {_fmt_num(ing['total'])}")
    lines.append("  Top categories:")
    for cat, cnt in list(ing["by_category"].items())[:10]:
        lines.append(f"    {cat:<24} {_fmt_num(cnt):>6}")
    lines.append("")
    lines.append("  Top 20 ingredients:")
    for name, cnt in list(ing["top_ingredients"].items())[:20]:
        lines.append(f"    {name:<30} {_fmt_num(cnt):>6}")
    lines.append("")
    lines.append(
        f"  Mappes OFF:                "
        f"{_fmt_num(ing['mapped_off'])}/{_fmt_num(ing['total'])} "
        f"({_pct(ing['mapped_off'], ing['total'])})"
    )
    if ing["off_confidence_distribution"]:
        lines.append("  Distribution OFF confidence:")
        for bucket, cnt in ing["off_confidence_distribution"].items():
            lines.append(f"    [{bucket:<7}]  {_fmt_num(cnt):>6}")

    # --- Diversite ---
    div = report["diversity"]
    lines.append("")
    lines.append("  DIVERSITE")
    lines.append("  Top cuisines:")
    for cuisine, cnt in list(div["by_cuisine"].items())[:15]:
        lines.append(f"    {cuisine:<24} {_fmt_num(cnt):>6}")
    lines.append("")
    lines.append("  Par difficulte:")
    for diff in range(1, 6):
        cnt = div["by_difficulty"].get(diff, 0)
        label = DIFFICULTY_LABELS.get(diff, "?")
        lines.append(f"    {diff} ({label:<14}) {_fmt_num(cnt):>6}")
    lines.append("")
    lines.append("  Par temps total:")
    for bucket, cnt in div["by_time"].items():
        lines.append(f"    {bucket:<24} {_fmt_num(cnt):>6}")
    lines.append("")
    lines.append("  Par mois de creation:")
    for month, cnt in div["by_month"].items():
        lines.append(f"    {month}  {_fmt_num(cnt):>6}")

    lines.append("")
    lines.append(REPORT_SEPARATOR)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fonction principale exposee (appelable depuis run_pipeline.py)
# ---------------------------------------------------------------------------


async def run_report(engine: AsyncEngine) -> dict[str, Any]:
    """Execute toutes les requetes d'analyse et retourne le rapport complet.

    Args:
        engine: moteur SQLAlchemy async connecte a la base.

    Returns:
        Dict complet du rapport, pret pour serialisation JSON et affichage.
    """
    logger.info("pipeline_report_start")

    overview = await _query_overview(engine)
    quality = await _query_quality(engine)
    tags = await _query_tags(engine)
    translation = await _query_translation(engine)
    embeddings = await _query_embeddings(engine)
    ingredients = await _query_ingredients(engine)
    diversity = await _query_diversity(engine)

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "overview": overview,
        "quality": quality,
        "tags": tags,
        "translation": translation,
        "embeddings": embeddings,
        "ingredients": ingredients,
        "diversity": diversity,
    }

    logger.info(
        "pipeline_report_done",
        total_recipes=overview["total_recipes"],
        avg_score=quality["avg_score"],
        embedding_coverage=_pct(embeddings["total_embeddings"], embeddings["total_recipes"]),
    )

    return report


# ---------------------------------------------------------------------------
# Serialisation JSON — gestion des types non-standards
# ---------------------------------------------------------------------------


def _json_serializer(obj: Any) -> Any:
    """Convertit les types non JSON-natifs pour json.dumps."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    # Les cles dict doivent etre des strings pour JSON
    if isinstance(obj, int):
        return obj
    raise TypeError(f"Type non serialisable : {type(obj)}")


def _normalize_dict_keys(data: Any) -> Any:
    """Convertit recursivement les cles de dict en strings pour la serialisation JSON.

    Les cles de type int (ex : difficulty) doivent etre converties en string
    pour etre compatibles avec json.dumps.
    """
    if isinstance(data, dict):
        return {str(k): _normalize_dict_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_normalize_dict_keys(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# Point d'entree CLI
# ---------------------------------------------------------------------------


async def main() -> None:
    """Point d'entree CLI : connecte a la base, genere le rapport, ecrit le JSON."""
    _configure_logging()
    database_url = _validate_env()
    output_file = os.getenv("OUTPUT_FILE", "pipeline_report.json")

    engine = create_async_engine(database_url, echo=False)

    try:
        report = await run_report(engine)

        # Affichage terminal
        terminal_output = _render_terminal(report)
        print(terminal_output)

        # Sauvegarde JSON
        serializable = _normalize_dict_keys(report)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2, default=_json_serializer)
        logger.info("pipeline_report_saved", path=output_file)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
