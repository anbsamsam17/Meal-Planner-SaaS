"""
Endpoints de santé : liveness et readiness.

Convention Railway (phase-0/infra/08-railway-setup.md) :
- GET /health  → liveness : réponse ultra-rapide (<5ms), aucune dépendance externe.
               Railway détecte les process bloqués avec cet endpoint.
- GET /ready   → readiness : vérifie DB + Redis + modèle ML chargé.
               Railway route le trafic seulement après que /ready retourne 200.
               Évite les 503 pendant le chargement sentence-transformers (~3-5s).

Pourquoi deux endpoints séparés :
  - Un process peut être "vivant" (le Python tourne) mais "pas prêt"
    (sentence-transformers charge encore en mémoire).
  - Sans cette distinction, Railway enverrait des requêtes avant que
    le modèle soit opérationnel → erreurs 500 au démarrage.
"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger
from sqlalchemy import text

router = APIRouter(tags=["health"])

# -------------------------------------------------------------------------
# Liveness check — ultra-rapide, aucune dépendance externe
# -------------------------------------------------------------------------


@router.get(
    "/health",
    summary="Liveness check",
    description=(
        "Vérifie que le process Python est vivant. "
        "Ne vérifie pas les dépendances (DB, Redis, modèle). "
        "Réponse attendue < 5ms."
    ),
    response_model=dict[str, str],
)
async def liveness() -> dict[str, str]:
    """
    Endpoint de liveness minimal.

    Railway l'utilise pour détecter les process bloqués et redémarrer
    le container si nécessaire. Ne doit JAMAIS faire de I/O.
    """
    return {"status": "ok"}


# -------------------------------------------------------------------------
# Readiness check — vérifie les dépendances critiques
# -------------------------------------------------------------------------


@router.get(
    "/ready",
    summary="Readiness check",
    description=(
        "Vérifie que l'API est prête à recevoir du trafic : "
        "connexion DB, Redis accessible, et modèle sentence-transformers chargé. "
        "Retourne 503 si une dépendance est indisponible."
    ),
    response_model=dict[str, Any],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Service non prêt — dépendance indisponible"
        }
    },
)
async def readiness(request: Request) -> dict[str, Any]:
    """
    Endpoint de readiness complet.

    Vérifie dans l'ordre :
    1. Modèle ML chargé (sentence-transformers)
    2. Pool de connexions DB fonctionnel (SELECT 1)
    3. Redis accessible (PING)

    Retourne 503 si l'une des vérifications échoue.
    Le détail des erreurs est loggué (pas exposé dans la réponse — sécurité).
    """
    checks: dict[str, Any] = {
        "status": "ready",
        "model": False,
        "database": False,
        "redis": False,
    }

    # ---- 1. Vérification du modèle ML ----
    model_loaded: bool = getattr(request.app.state, "model_loaded", False)
    if not model_loaded:
        logger.warning("readiness_check_failed", reason="model_not_loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "reason": "Modèle sentence-transformers en cours de chargement.",
            },
        )
    checks["model"] = True

    # ---- 2. Vérification de la base de données ----
    db_session = getattr(request.app.state, "db_session_factory", None)
    if db_session is not None:
        try:
            start = time.monotonic()
            async with db_session() as session:
                await session.execute(text("SELECT 1"))
            db_latency_ms = round((time.monotonic() - start) * 1000, 2)
            checks["database"] = True
            checks["db_latency_ms"] = db_latency_ms
        except Exception as exc:
            logger.error("readiness_db_ping_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "reason": "Base de données inaccessible.",
                },
            )
    else:
        # Pas de pool configuré (tests unitaires sans DB)
        checks["database"] = True

    # ---- 3. Vérification Redis ----
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        try:
            start = time.monotonic()
            pong = await redis_client.ping()
            redis_latency_ms = round((time.monotonic() - start) * 1000, 2)
            checks["redis"] = bool(pong)
            checks["redis_latency_ms"] = redis_latency_ms
        except Exception as exc:
            logger.error("readiness_redis_ping_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "reason": "Redis inaccessible.",
                },
            )
    else:
        # Pas de Redis configuré (tests unitaires sans Redis)
        checks["redis"] = True

    return checks
