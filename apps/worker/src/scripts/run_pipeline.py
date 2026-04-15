"""Orchestrateur du pipeline complet d'import et d'enrichissement de recettes.

Exécute les scripts d'import, d'enrichissement et de mapping dans le bon ordre,
avec gestion d'état persistante, reprise sur erreur et rapport final.

Architecture du pipeline :
    Phase 1 — CLEANUP       : purge des recettes basse qualité
    Phase 2 — IMPORT        : scraping + imports API (parallélisable)
    Phase 3 — ENRICHMENT    : traduction, tags saisonniers, tags régime/budget
    Phase 4 — DEDUP & EMBED : déduplication SQL + génération embeddings
    Phase 5 — MAPPING       : correspondance Open Food Facts
    Phase 6 — REPORT        : métriques finales

Usage :
    cd apps/worker
    DATABASE_URL=postgresql+asyncpg://... \\
    uv run python -m src.scripts.run_pipeline

    # Reprendre un pipeline échoué
    uv run python -m src.scripts.run_pipeline --resume

    # Import API uniquement (pas de scraping)
    uv run python -m src.scripts.run_pipeline --skip-scraping

    # Phases spécifiques
    uv run python -m src.scripts.run_pipeline --phases 1,3,4

    # Simulation sans écriture
    uv run python -m src.scripts.run_pipeline --dry-run

Variables d'environnement :
    DATABASE_URL              Obligatoire — connexion PostgreSQL async (asyncpg).
    GOOGLE_AI_API_KEY         Recommandé  — traduction Gemini (Phase 3).
    SPOONACULAR_API_KEY       Optionnel   — skip automatique si absent.
    EDAMAM_APP_ID             Optionnel   — skip automatique si absent.
    EDAMAM_APP_KEY            Optionnel   — requis si EDAMAM_APP_ID présent.
    PIPELINE_STATE_FILE       Optionnel   — chemin du fichier d'état JSON
                                            (défaut : pipeline_state.json).
    LOG_LEVEL                 Optionnel   — DEBUG/INFO/WARNING (défaut : INFO).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_STATE_FILE = "pipeline_state.json"

# Statuts possibles pour chaque step du pipeline
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# Largeur du tableau récapitulatif final
REPORT_WIDTH = 68


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Résultat d'un step de pipeline avec son statut et ses statistiques."""

    step_id: str
    status: str
    started_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0
    stats: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def duration_human(self) -> str:
        """Retourne la durée sous forme lisible (ex: 1h23m, 45m, 12s)."""
        secs = int(self.duration_s)
        if secs >= 3600:
            h = secs // 3600
            m = (secs % 3600) // 60
            return f"{h}h{m:02d}m"
        if secs >= 60:
            m = secs // 60
            s = secs % 60
            return f"{m}m{s:02d}s"
        return f"{secs}s"


@dataclass
class PipelineState:
    """État complet du pipeline, persisté en JSON entre les exécutions."""

    run_id: str
    started_at: str
    finished_at: str = ""
    steps: dict[str, StepResult] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Sérialise l'état en dict JSON-serialisable."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": {k: asdict(v) for k, v in self.steps.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        """Désérialise l'état depuis un dict (chargé du fichier JSON)."""
        steps = {
            k: StepResult(**v)
            for k, v in data.get("steps", {}).items()
        }
        return cls(
            run_id=data["run_id"],
            started_at=data["started_at"],
            finished_at=data.get("finished_at", ""),
            steps=steps,
        )


# ---------------------------------------------------------------------------
# Définition du pipeline
# ---------------------------------------------------------------------------


@dataclass
class StepDef:
    """Définition statique d'un step du pipeline."""

    step_id: str
    label: str
    # clé de stat principale à afficher dans le rapport (ex: "inserted")
    stat_key: str
    # libellé pour la valeur stat (ex: "importées", "traduites")
    stat_label: str
    # fonction async à appeler — None = SQL inline
    fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None = None
    # requête SQL à exécuter directement (si fn is None)
    sql_path: str | None = None
    # variables d'env requises pour activer ce step (skip si absentes)
    required_env: list[str] = field(default_factory=list)


@dataclass
class PhaseDef:
    """Définition statique d'une phase du pipeline."""

    phase_id: int
    name: str
    steps: list[StepDef]
    # True = les steps peuvent tourner en parallèle (asyncio.gather)
    parallel: bool = False


# La définition des phases est construite dynamiquement dans _build_phases()
# pour permettre les imports conditionnels des scripts.


# ---------------------------------------------------------------------------
# Gestion de l'état persistant
# ---------------------------------------------------------------------------


def _load_state(state_file: Path) -> PipelineState | None:
    """Charge l'état du pipeline depuis le fichier JSON.

    Retourne None si le fichier n'existe pas ou est corrompu.
    """
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return PipelineState.from_dict(data)
    except Exception as exc:
        logger.warning("pipeline_state_load_error", file=str(state_file), error=str(exc))
        return None


def _save_state(state: PipelineState, state_file: Path) -> None:
    """Persiste l'état du pipeline dans le fichier JSON (atomic write)."""
    tmp = state_file.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(state_file)
    except Exception as exc:
        logger.error("pipeline_state_save_error", file=str(state_file), error=str(exc))


def _init_state(state_file: Path, phases: list[PhaseDef]) -> PipelineState:
    """Crée un nouvel état pipeline avec tous les steps en statut pending."""
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    state = PipelineState(
        run_id=run_id,
        started_at=datetime.now(UTC).isoformat(),
    )
    for phase in phases:
        for step in phase.steps:
            state.steps[step.step_id] = StepResult(
                step_id=step.step_id,
                status=STATUS_PENDING,
            )
    _save_state(state, state_file)
    logger.info("pipeline_state_initialized", run_id=run_id, steps=len(state.steps))
    return state


# ---------------------------------------------------------------------------
# Wrappers pour les scripts existants
# ---------------------------------------------------------------------------


async def _wrap_translate_recipes(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Adapte translate_recipes.main() → dict stats pour le pipeline."""
    # translate_recipes.main() lit ses paramètres via os.environ
    # et ne retourne pas de stats — on intercepte via sys.exit patch
    if dry_run:
        os.environ["DRY_RUN"] = "true"
    else:
        os.environ.pop("DRY_RUN", None)

    try:
        from src.scripts.translate_recipes import main as translate_main
        await translate_main()
        # main() appelle sys.exit(1) en cas d'erreurs — si on arrive ici, succès
        return {"status": "ok"}
    except SystemExit as exc:
        if exc.code and int(exc.code) != 0:
            raise RuntimeError(f"translate_recipes a terminé avec code {exc.code}") from exc
        return {"status": "ok"}


async def _wrap_backfill_embeddings(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Adapte backfill_embeddings.main() → dict stats pour le pipeline."""
    if dry_run:
        os.environ["DRY_RUN"] = "true"
    else:
        os.environ.pop("DRY_RUN", None)

    try:
        from src.scripts.backfill_embeddings import main as backfill_main
        await backfill_main()
        return {"status": "ok"}
    except SystemExit as exc:
        if exc.code and int(exc.code) != 0:
            raise RuntimeError(f"backfill_embeddings a terminé avec code {exc.code}") from exc
        return {"status": "ok"}


async def _wrap_import_spoonacular(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Adapte import_spoonacular.run_import() → dict stats pour le pipeline."""
    from src.scripts.import_spoonacular import run_import as spoon_run

    db_url = os.environ["DATABASE_URL"]
    api_key = os.environ["SPOONACULAR_API_KEY"]
    max_recipes = int(os.getenv("MAX_RECIPES", "50"))

    stats = await spoon_run(
        database_url=db_url,
        api_key=api_key,
        max_recipes=max_recipes,
        dry_run=dry_run,
    )
    return stats


async def _wrap_import_edamam(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Adapte import_edamam_recipes.run_import() → dict stats pour le pipeline."""
    if dry_run:
        os.environ["DRY_RUN"] = "true"
    else:
        os.environ.pop("DRY_RUN", None)

    from src.scripts.import_edamam_recipes import run_import as edamam_run

    stats = await edamam_run()
    return stats


async def _wrap_import_quality(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Adapte import_quality_recipes.run_import() → dict stats pour le pipeline."""
    if dry_run:
        os.environ["DRY_RUN"] = "true"
    else:
        os.environ.pop("DRY_RUN", None)

    from src.scripts.import_quality_recipes import run_import as quality_run

    stats = await quality_run()
    return stats


# ---------------------------------------------------------------------------
# Exécution des étapes SQL
# ---------------------------------------------------------------------------


async def _run_sql_file(sql_path: str, dry_run: bool = False) -> dict[str, Any]:
    """Exécute un fichier SQL via SQLAlchemy async.

    En mode dry_run, lis le fichier mais ne l'exécute pas.
    Retourne le nombre de lignes affectées (rowcount).
    """
    sql_file = Path(sql_path)
    if not sql_file.exists():
        raise FileNotFoundError(f"Fichier SQL introuvable : {sql_path}")

    sql_content = sql_file.read_text(encoding="utf-8")

    if dry_run:
        logger.info("[DRY_RUN] sql_skipped", file=sql_path)
        return {"rows_affected": 0, "dry_run": True}

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, echo=False)

    total_rows = 0
    try:
        # Découper les statements (séparés par ;)
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        async with engine.begin() as conn:
            for stmt in statements:
                if not stmt or stmt.startswith("--"):
                    continue
                result = await conn.execute(text(stmt))
                # rowcount peut être -1 pour certains drivers si non supporté
                if result.rowcount and result.rowcount > 0:
                    total_rows += result.rowcount
    finally:
        await engine.dispose()

    logger.info("sql_executed", file=sql_path, rows_affected=total_rows)
    return {"rows_affected": total_rows}


async def _run_dedup_sql(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Supprime les doublons de recettes via SQL (même titre + même source).

    Stratégie : pour chaque groupe de recettes avec le même titre normalisé
    et la même source, garde le plus ancien (created_at MIN) et supprime les autres.
    """
    if dry_run:
        logger.info("[DRY_RUN] dedup_skipped")
        return {"deleted": 0, "dry_run": True}

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, echo=False)

    dedup_sql = """
    WITH duplicates AS (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY lower(trim(title)), source
                ORDER BY created_at ASC
            ) AS rn
        FROM recipes
        WHERE title IS NOT NULL AND title != ''
    )
    DELETE FROM recipes
    WHERE id IN (
        SELECT id FROM duplicates WHERE rn > 1
    )
    """

    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(dedup_sql))
            deleted = result.rowcount if result.rowcount and result.rowcount > 0 else 0
    finally:
        await engine.dispose()

    logger.info("dedup_completed", deleted=deleted)
    return {"deleted": deleted}


async def _run_pipeline_report(dry_run: bool = False, **_: Any) -> dict[str, Any]:
    """Interroge la DB pour générer les métriques finales du pipeline."""
    if dry_run:
        return {"total_recipes": 0, "avg_quality_score": 0.0, "dry_run": True}

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT
                        COUNT(*)                         AS total_recipes,
                        ROUND(AVG(quality_score)::numeric, 2) AS avg_quality_score,
                        COUNT(*) FILTER (WHERE language = 'fr') AS fr_count,
                        COUNT(DISTINCT source)           AS sources_count
                    FROM recipes
                """)
            )
            row = result.mappings().fetchone()
            if row:
                return {
                    "total_recipes": int(row["total_recipes"] or 0),
                    "avg_quality_score": float(row["avg_quality_score"] or 0.0),
                    "fr_count": int(row["fr_count"] or 0),
                    "sources_count": int(row["sources_count"] or 0),
                }
    finally:
        await engine.dispose()

    return {"total_recipes": 0, "avg_quality_score": 0.0}


# ---------------------------------------------------------------------------
# Construction du pipeline
# ---------------------------------------------------------------------------


def _build_phases(
    skip_scraping: bool = False,
    skip_api: bool = False,
) -> list[PhaseDef]:
    """Construit la liste des phases et steps du pipeline.

    Les scripts de scraping (Marmiton, 750g) ne font pas partie des modules
    listés dans le glob initial — ils sont référencés mais peuvent être absents.
    On les enregistre avec un fallback gracieux.
    """

    async def _stub_scrape_marmiton(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        """Stub pour scrape_marmiton — à implémenter quand le module est présent."""
        try:
            from src.scripts.scrape_marmiton import run_scrape  # type: ignore[import]

            db_url = os.environ["DATABASE_URL"]
            max_recipes = int(os.getenv("MAX_RECIPES", "2000"))
            max_pages = int(os.getenv("MAX_PAGES_PER_CATEGORY", "50"))
            return await run_scrape(
                database_url=db_url,
                max_recipes=max_recipes,
                max_pages_per_category=max_pages,
                dry_run=dry_run,
            )
        except ImportError:
            logger.warning("scrape_marmiton_not_found", hint="Module src.scripts.scrape_marmiton absent — step ignoré")
            return {"imported": 0, "skipped": 0, "module_missing": True}

    async def _stub_scrape_750g(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        """Stub pour scrape_750g — à implémenter quand le module est présent."""
        try:
            from src.scripts.scrape_750g import run_scrape  # type: ignore[import]

            db_url = os.environ["DATABASE_URL"]
            max_recipes = int(os.getenv("MAX_RECIPES", "2000"))
            sites = os.getenv("SOURCE_SITES", "750g").split(",")
            return await run_scrape(
                database_url=db_url,
                source_sites=sites,
                max_recipes=max_recipes,
                dry_run=dry_run,
            )
        except ImportError:
            logger.warning("scrape_750g_not_found", hint="Module src.scripts.scrape_750g absent — step ignoré")
            return {"imported": 0, "skipped": 0, "module_missing": True}

    async def _stub_map_off(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        """Stub pour map_off_ingredients — à implémenter quand le module est présent."""
        try:
            from src.scripts.map_off_ingredients import run_mapping  # type: ignore[import]

            db_url = os.environ["DATABASE_URL"]
            batch_size = int(os.getenv("BATCH_SIZE", "20"))
            return await run_mapping(
                database_url=db_url,
                dry_run=dry_run,
                batch_size=batch_size,
            )
        except ImportError:
            logger.warning("map_off_not_found", hint="Module src.scripts.map_off_ingredients absent — step ignoré")
            return {"mapped": 0, "total": 0, "module_missing": True}

    async def _stub_cleanup(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        """Stub pour cleanup_low_quality — à implémenter quand le module est présent."""
        try:
            from src.scripts.cleanup_low_quality import run_cleanup  # type: ignore[import]

            db_url = os.environ["DATABASE_URL"]
            threshold = int(os.getenv("QUALITY_THRESHOLD", "50"))
            return await run_cleanup(
                database_url=db_url,
                quality_threshold=threshold,
                dry_run=dry_run,
            )
        except ImportError:
            logger.warning("cleanup_not_found", hint="Module src.scripts.cleanup_low_quality absent — step ignoré")
            return {"deleted": 0, "analyzed": 0, "module_missing": True}

    # ------------------------------------------------------------------
    # Phase 1 : CLEANUP
    # ------------------------------------------------------------------
    phase1_steps = [
        StepDef(
            step_id="cleanup_low_quality",
            label="cleanup_low_quality",
            stat_key="deleted",
            stat_label="supprimées",
            fn=_stub_cleanup,
        ),
    ]

    # ------------------------------------------------------------------
    # Phase 2 : IMPORT (parallélisable)
    # ------------------------------------------------------------------
    phase2_steps: list[StepDef] = []

    if not skip_scraping:
        phase2_steps += [
            StepDef(
                step_id="scrape_marmiton",
                label="scrape_marmiton",
                stat_key="imported",
                stat_label="importées",
                fn=_stub_scrape_marmiton,
            ),
            StepDef(
                step_id="scrape_750g",
                label="scrape_750g",
                stat_key="imported",
                stat_label="importées",
                fn=_stub_scrape_750g,
            ),
        ]

    if not skip_api:
        phase2_steps.append(
            StepDef(
                step_id="import_spoonacular",
                label="import_spoonacular",
                stat_key="inserted",
                stat_label="importées",
                fn=_wrap_import_spoonacular,
                required_env=["SPOONACULAR_API_KEY"],
            )
        )
        phase2_steps.append(
            StepDef(
                step_id="import_edamam",
                label="import_edamam",
                stat_key="inserted",
                stat_label="importées",
                fn=_wrap_import_edamam,
                required_env=["EDAMAM_APP_ID", "EDAMAM_APP_KEY"],
            )
        )

    if not phase2_steps:
        # Garantir qu'une phase ne soit jamais vide
        phase2_steps.append(
            StepDef(
                step_id="import_noop",
                label="import (aucun actif)",
                stat_key="inserted",
                stat_label="importées",
                fn=lambda **_: asyncio.coroutine(lambda: {"inserted": 0})(),
            )
        )

    # ------------------------------------------------------------------
    # Phase 3 : ENRICHMENT (séquentiel)
    # ------------------------------------------------------------------
    # Résoudre les chemins SQL relatifs à la racine du repo
    _repo_root = Path(__file__).resolve().parents[4]  # scripts/ → src/ → worker/ → apps/ → repo root
    sql_seasonal = str(_repo_root / "scripts" / "add_seasonal_tags.sql")
    sql_diet = str(_repo_root / "scripts" / "add_diet_budget_tags.sql")

    async def _run_seasonal_tags(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        return await _run_sql_file(sql_seasonal, dry_run=dry_run)

    async def _run_diet_tags(dry_run: bool = False, **_: Any) -> dict[str, Any]:
        return await _run_sql_file(sql_diet, dry_run=dry_run)

    phase3_steps = [
        StepDef(
            step_id="translate_recipes",
            label="translate_recipes",
            stat_key="translated",
            stat_label="traduites",
            fn=_wrap_translate_recipes,
            required_env=["GOOGLE_AI_API_KEY"],
        ),
        StepDef(
            step_id="add_seasonal_tags",
            label="add_seasonal_tags",
            stat_key="rows_affected",
            stat_label="recettes taggées",
            fn=_run_seasonal_tags,
        ),
        StepDef(
            step_id="add_diet_budget_tags",
            label="add_diet_budget_tags",
            stat_key="rows_affected",
            stat_label="recettes taggées",
            fn=_run_diet_tags,
        ),
    ]

    # ------------------------------------------------------------------
    # Phase 4 : DEDUP & EMBED (séquentiel)
    # ------------------------------------------------------------------
    phase4_steps = [
        StepDef(
            step_id="deduplication",
            label="deduplication",
            stat_key="deleted",
            stat_label="doublons supprimés",
            fn=_run_dedup_sql,
        ),
        StepDef(
            step_id="backfill_embeddings",
            label="backfill_embeddings",
            stat_key="total_processed",
            stat_label="embeddings générés",
            fn=_wrap_backfill_embeddings,
        ),
    ]

    # ------------------------------------------------------------------
    # Phase 5 : MAPPING (séquentiel)
    # ------------------------------------------------------------------
    phase5_steps = [
        StepDef(
            step_id="map_off_ingredients",
            label="map_off_ingredients",
            stat_key="mapped",
            stat_label="ingrédients mappés",
            fn=_stub_map_off,
        ),
    ]

    # ------------------------------------------------------------------
    # Phase 6 : REPORT (séquentiel)
    # ------------------------------------------------------------------
    phase6_steps = [
        StepDef(
            step_id="pipeline_report",
            label="pipeline_report",
            stat_key="total_recipes",
            stat_label="recettes en base",
            fn=_run_pipeline_report,
        ),
    ]

    return [
        PhaseDef(phase_id=1, name="CLEANUP", steps=phase1_steps, parallel=False),
        PhaseDef(phase_id=2, name="IMPORT", steps=phase2_steps, parallel=True),
        PhaseDef(phase_id=3, name="ENRICHMENT", steps=phase3_steps, parallel=False),
        PhaseDef(phase_id=4, name="DEDUP & EMBED", steps=phase4_steps, parallel=False),
        PhaseDef(phase_id=5, name="MAPPING", steps=phase5_steps, parallel=False),
        PhaseDef(phase_id=6, name="REPORT", steps=phase6_steps, parallel=False),
    ]


# ---------------------------------------------------------------------------
# Logique d'exécution
# ---------------------------------------------------------------------------


def _should_skip_step(
    step: StepDef,
    step_result: StepResult | None,
    resume: bool,
) -> tuple[bool, str]:
    """Détermine si un step doit être ignoré et pourquoi.

    Returns:
        (should_skip, reason) — reason est la chaîne loggée/affichée.
    """
    # Variables d'env requises absentes
    for env_var in step.required_env:
        if not os.getenv(env_var):
            return True, f"env {env_var} absent"

    # Mode --resume : skip les steps déjà completés
    if resume and step_result and step_result.status == STATUS_COMPLETED:
        return True, "déjà completé (--resume)"

    return False, ""


async def _execute_step(
    step: StepDef,
    state: PipelineState,
    state_file: Path,
    dry_run: bool,
    resume: bool,
) -> StepResult:
    """Exécute un seul step, met à jour l'état et retourne le résultat."""
    result = state.steps.get(step.step_id) or StepResult(
        step_id=step.step_id,
        status=STATUS_PENDING,
    )

    should_skip, skip_reason = _should_skip_step(step, result, resume)
    if should_skip:
        result.status = STATUS_SKIPPED
        logger.info(
            "pipeline_step_skipped",
            step=step.step_id,
            reason=skip_reason,
        )
        state.steps[step.step_id] = result
        _save_state(state, state_file)
        return result

    # Marquer running
    result.status = STATUS_RUNNING
    result.started_at = datetime.now(UTC).isoformat()
    state.steps[step.step_id] = result
    _save_state(state, state_file)

    logger.info("pipeline_step_start", step=step.step_id)
    t0 = time.monotonic()

    try:
        if step.fn is not None:
            stats = await step.fn(dry_run=dry_run)
        else:
            stats = {}

        result.status = STATUS_COMPLETED
        result.stats = stats or {}
        result.error = ""

        elapsed = time.monotonic() - t0
        result.duration_s = elapsed
        result.finished_at = datetime.now(UTC).isoformat()

        logger.info(
            "pipeline_step_done",
            step=step.step_id,
            duration_s=round(elapsed, 1),
            stats=result.stats,
        )

    except Exception as exc:
        elapsed = time.monotonic() - t0
        result.status = STATUS_FAILED
        result.duration_s = elapsed
        result.finished_at = datetime.now(UTC).isoformat()
        result.error = str(exc)[:500]

        logger.error(
            "pipeline_step_failed",
            step=step.step_id,
            duration_s=round(elapsed, 1),
            error=result.error,
        )

    state.steps[step.step_id] = result
    _save_state(state, state_file)
    return result


async def _execute_phase(
    phase: PhaseDef,
    state: PipelineState,
    state_file: Path,
    dry_run: bool,
    resume: bool,
) -> list[StepResult]:
    """Exécute tous les steps d'une phase, en parallèle si phase.parallel=True."""
    logger.info(
        "pipeline_phase_start",
        phase=phase.phase_id,
        name=phase.name,
        steps=len(phase.steps),
        parallel=phase.parallel,
    )

    if phase.parallel:
        tasks = [
            _execute_step(step, state, state_file, dry_run, resume)
            for step in phase.steps
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    else:
        results = []
        for step in phase.steps:
            result = await _execute_step(step, state, state_file, dry_run, resume)
            results.append(result)
            # En mode séquentiel, continuer même si un step échoue
            # (le statut failed est tracké dans l'état)

    return list(results)


# ---------------------------------------------------------------------------
# Rapport final
# ---------------------------------------------------------------------------


def _format_stat_line(step: StepDef, result: StepResult) -> str:
    """Formate une ligne de résultat pour le rapport final (largeur fixe).

    Format : "  [status_icon] label  — valeur stat  durée"
    """
    status_icons = {
        STATUS_COMPLETED: "ok",
        STATUS_FAILED: "FAIL",
        STATUS_SKIPPED: "skip",
        STATUS_RUNNING: "...",
        STATUS_PENDING: "    ",
    }
    icon = status_icons.get(result.status, "?")

    # Valeur stat principale
    stat_val = result.stats.get(step.stat_key, "")
    if stat_val != "" and result.status == STATUS_COMPLETED:
        stat_str = f"{stat_val} {step.stat_label}"
    elif result.status == STATUS_SKIPPED:
        stat_str = f"ignoré — {result.error or 'step skippé'}"[:30]
    elif result.status == STATUS_FAILED:
        stat_str = f"ERREUR: {result.error[:25]}"
    else:
        stat_str = "—"

    duration = result.duration_human() if result.duration_s > 0 else ""

    # Aligner les colonnes : label 26 chars, stat 30 chars, durée 7 chars
    label_col = f"{step.label:<26}"
    stat_col = f"{stat_str:<30}"
    dur_col = f"{duration:>6}"

    icon_col = f"[{icon}]"
    line = f"  {icon_col:<6} {label_col} {stat_col} {dur_col}"
    return line


def _print_report(
    phases: list[PhaseDef],
    state: PipelineState,
    total_elapsed_s: float,
) -> None:
    """Affiche le rapport récapitulatif final dans le terminal."""

    def border(char: str = "=") -> str:
        return char * REPORT_WIDTH

    def pad(text: str) -> str:
        """Centre le texte dans la largeur du rapport."""
        return f"  {text}"

    lines: list[str] = []
    lines.append(border("="))
    title = "RECIPE PIPELINE — REPORT"
    lines.append(f"  {title:^{REPORT_WIDTH - 4}}")
    lines.append(border("="))

    for phase in phases:
        lines.append(f"  Phase {phase.phase_id}: {phase.name}")
        for step in phase.steps:
            result = state.steps.get(step.step_id)
            if result:
                lines.append(_format_stat_line(step, result))
        lines.append("")

    # Métriques finales depuis le step report
    report_result = state.steps.get("pipeline_report")
    if report_result and report_result.status == STATUS_COMPLETED:
        total = report_result.stats.get("total_recipes", "?")
        avg_qs = report_result.stats.get("avg_quality_score", 0.0)
        lines.append(f"  TOTAL: {total} recettes en base, quality_score moyen {avg_qs}")

    # Durée totale
    elapsed_h = int(total_elapsed_s) // 3600
    elapsed_m = (int(total_elapsed_s) % 3600) // 60
    elapsed_s_rem = int(total_elapsed_s) % 60
    if elapsed_h > 0:
        duration_str = f"{elapsed_h}h{elapsed_m:02d}m{elapsed_s_rem:02d}s"
    elif elapsed_m > 0:
        duration_str = f"{elapsed_m}m{elapsed_s_rem:02d}s"
    else:
        duration_str = f"{elapsed_s_rem}s"

    lines.append(f"  Durée totale: {duration_str}")
    lines.append(border("="))

    # Affichage dans les logs ET directement dans stdout
    print("\n" + "\n".join(lines) + "\n")
    logger.info("pipeline_report_printed", total_duration=duration_str)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse les arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Orchestrateur du pipeline d'import et d'enrichissement de recettes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  # Pipeline complet
  python -m src.scripts.run_pipeline

  # Reprendre après une erreur
  python -m src.scripts.run_pipeline --resume

  # Simulation complète
  python -m src.scripts.run_pipeline --dry-run

  # Phases spécifiques (ex: enrichissement + embeddings uniquement)
  python -m src.scripts.run_pipeline --phases 3,4

  # Import API uniquement, sans scraping
  python -m src.scripts.run_pipeline --skip-scraping

  # Rapport uniquement (pas d'import)
  python -m src.scripts.run_pipeline --report-only
""",
    )
    parser.add_argument(
        "--phases",
        default="all",
        help="Phases à exécuter : 'all' (défaut) ou liste séparée par virgules (ex: 1,2,3)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reprendre un pipeline échoué — les steps 'completed' sont ignorés",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler sans écriture en base — DRY_RUN=true pour tous les scripts",
    )
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Ignorer les scrapers Marmiton et 750g",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Ignorer les imports API (Spoonacular, Edamam)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Générer uniquement le rapport final (Phase 6)",
    )
    return parser.parse_args()


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


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------


async def run_pipeline(
    phases_filter: list[int] | None = None,
    resume: bool = False,
    dry_run: bool = False,
    skip_scraping: bool = False,
    skip_api: bool = False,
    report_only: bool = False,
    state_file: Path | None = None,
) -> PipelineState:
    """Orchestre l'exécution complète du pipeline.

    Appelable directement depuis une tâche Celery ou depuis main().

    Args:
        phases_filter : liste des numéros de phases à exécuter (None = toutes).
        resume        : True pour reprendre un pipeline échoué.
        dry_run       : True pour simuler sans écriture en base.
        skip_scraping : True pour ignorer les scrapers web.
        skip_api      : True pour ignorer les imports API.
        report_only   : True pour n'exécuter que la Phase 6 (rapport).
        state_file    : chemin du fichier d'état JSON.

    Returns:
        PipelineState final avec tous les résultats.
    """
    if state_file is None:
        state_file = Path(os.getenv("PIPELINE_STATE_FILE", DEFAULT_STATE_FILE))

    if report_only:
        phases_filter = [6]

    all_phases = _build_phases(skip_scraping=skip_scraping, skip_api=skip_api)

    # Filtrer les phases demandées
    if phases_filter:
        active_phases = [p for p in all_phases if p.phase_id in phases_filter]
    else:
        active_phases = all_phases

    if not active_phases:
        logger.error("pipeline_no_phases", requested=phases_filter)
        sys.exit(1)

    # Charger l'état existant en mode --resume, sinon créer un nouvel état
    if resume:
        state = _load_state(state_file)
        if state is None:
            logger.info("pipeline_resume_no_state", hint="Aucun état existant — démarrage complet")
            state = _init_state(state_file, active_phases)
        else:
            logger.info(
                "pipeline_resuming",
                run_id=state.run_id,
                completed=[k for k, v in state.steps.items() if v.status == STATUS_COMPLETED],
            )
            # S'assurer que les nouveaux steps (phases filtrées) sont dans l'état
            for phase in active_phases:
                for step in phase.steps:
                    if step.step_id not in state.steps:
                        state.steps[step.step_id] = StepResult(
                            step_id=step.step_id,
                            status=STATUS_PENDING,
                        )
    else:
        state = _init_state(state_file, active_phases)

    logger.info(
        "pipeline_start",
        phases=[p.name for p in active_phases],
        dry_run=dry_run,
        resume=resume,
        state_file=str(state_file),
    )

    pipeline_start = time.monotonic()

    for phase in active_phases:
        logger.info(
            "pipeline_phase_enter",
            phase_id=phase.phase_id,
            name=phase.name,
        )
        await _execute_phase(phase, state, state_file, dry_run, resume)

        # Vérifier si la phase a eu des échecs critiques
        failed_steps = [
            step.step_id
            for step in phase.steps
            if state.steps.get(step.step_id, StepResult("", STATUS_PENDING)).status == STATUS_FAILED
        ]
        if failed_steps:
            logger.warning(
                "pipeline_phase_partial_failure",
                phase=phase.name,
                failed=failed_steps,
                hint="Utiliser --resume pour relancer les steps échoués",
            )
        # On continue quand même vers les phases suivantes

    state.finished_at = datetime.now(UTC).isoformat()
    _save_state(state, state_file)

    total_elapsed = time.monotonic() - pipeline_start

    # Rapport final
    _print_report(active_phases, state, total_elapsed)

    return state


async def main() -> None:
    """Point d'entrée CLI du script."""
    _configure_logging()
    args = _parse_args()

    # Vérification de DATABASE_URL obligatoire
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error(
            "env_var_missing",
            var="DATABASE_URL",
            hint="Exemple : DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
        )
        sys.exit(1)

    # Parser les phases
    phases_filter: list[int] | None = None
    if args.phases != "all":
        try:
            phases_filter = [int(p.strip()) for p in args.phases.split(",") if p.strip()]
        except ValueError:
            logger.error("invalid_phases_arg", value=args.phases, hint="Format attendu : 1,2,3 ou 'all'")
            sys.exit(1)

    state = await run_pipeline(
        phases_filter=phases_filter,
        resume=args.resume,
        dry_run=args.dry_run,
        skip_scraping=args.skip_scraping,
        skip_api=args.skip_api,
        report_only=args.report_only,
        state_file=Path(os.getenv("PIPELINE_STATE_FILE", DEFAULT_STATE_FILE)),
    )

    # Code de sortie : 1 si au moins un step a échoué
    failed = [k for k, v in state.steps.items() if v.status == STATUS_FAILED]
    if failed:
        logger.error("pipeline_finished_with_errors", failed=failed)
        sys.exit(1)

    logger.info("pipeline_finished_ok")


if __name__ == "__main__":
    asyncio.run(main())
