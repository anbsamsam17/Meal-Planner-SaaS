"""
Configuration du logging centralisé avec loguru.

Règles ROADMAP :
- Logs structurés JSON en production (parsables par Sentry, Datadog)
- Logs colorés en développement pour la lisibilité locale
- Correlation ID propagé via contextvars pour tracer les requêtes de bout en bout
- Interception du logger stdlib pour capturer les logs Uvicorn, SQLAlchemy, etc.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from loguru import logger

# Variable de contexte pour le correlation ID.
# Chaque requête HTTP reçoit un ID unique injecté par le middleware correlation.
# Le même ID est propagé dans tous les logs de la requête, y compris les tâches Celery.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retourne le correlation ID du contexte courant, ou une chaîne vide."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Définit le correlation ID pour le contexte courant (appelé par le middleware)."""
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """Génère un nouveau correlation ID UUID4 court (8 premiers caractères)."""
    return uuid4().hex[:8]


class InterceptHandler(logging.Handler):
    """
    Handler qui redirige les logs stdlib vers loguru.

    Capte les logs de : uvicorn, uvicorn.access, uvicorn.error,
    sqlalchemy.engine, httpx, celery, etc.
    Ceci centralise tous les logs dans le même format JSON en production.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Récupère le niveau loguru correspondant au niveau stdlib
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Remonter dans la stack pour trouver l'appelant original
        # (évite que loguru affiche "InterceptHandler" comme source)
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _json_formatter(record: dict[str, Any]) -> str:
    """
    Formatte un log record en JSON structuré pour la production.

    Inclut le correlation_id du contexte courant pour le tracing distribué.
    Ce format est compatible avec Sentry, Datadog et Loki.
    """
    import json

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "correlation_id": get_correlation_id() or None,
    }

    # Ajoute les champs extra s'ils existent (ex: user_id, household_id)
    if record.get("extra"):
        log_entry.update(record["extra"])

    # Ajoute les informations d'exception si présentes
    if record.get("exception"):
        log_entry["exception"] = str(record["exception"])

    return json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"


def setup_logging(log_level: str = "INFO", env: str = "dev") -> None:
    """
    Configure loguru selon l'environnement.

    À appeler une seule fois au démarrage de l'application (dans lifespan).
    En prod : JSON structuré vers stdout (capté par Railway/Sentry).
    En dev  : format coloré humain pour la lisibilité terminal.

    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR).
        env: Environnement d'exécution (dev, staging, prod).
    """
    # Supprimer le handler par défaut de loguru
    logger.remove()

    if env == "prod" or env == "staging":
        # Format JSON pour les environnements cloud
        logger.add(
            sys.stdout,
            level=log_level,
            format=_json_formatter,  # type: ignore[arg-type]
            backtrace=False,  # Ne pas exposer les traces complètes en prod
            diagnose=False,  # Désactive les valeurs de variables dans les traces
            enqueue=True,  # Thread-safe pour les workers Celery
        )
    else:
        # Format coloré pour le développement local.
        # Le filtre injecte un default "startup" pour les logs émis avant le middleware
        # HTTP (lifespan, imports), qui n'ont pas encore de correlation_id dans extra.
        def _dev_correlation_filter(record: dict[str, Any]) -> bool:
            record["extra"].setdefault("correlation_id", "startup")
            return True

        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<white>[{extra[correlation_id]}]</white> "
                "- {message}"
            ),
            filter=_dev_correlation_filter,
            backtrace=True,
            diagnose=True,
            enqueue=False,
        )

    # Intercepter tous les loggers stdlib pour centraliser les logs
    # Niveau WARNING minimum pour éviter le bruit des librairies tierces
    stdlib_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "httpx",
        "httpcore",
        "celery",
        "celery.worker",
        "celery.task",
    ]

    for name in stdlib_loggers:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    # Root logger : capture tout ce qui n'est pas géré explicitement
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
