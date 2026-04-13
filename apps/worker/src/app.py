"""
Application Celery — Presto Worker.

Configure le broker Redis (DB 0), le backend de résultats (DB 2),
les routes de tâches par queue, le schedule Celery Beat,
et les paramètres de performance (prefetch, time limits).

Architecture des queues :
  scraping   : tâches de scraping web (Scrapy, Playwright) — CPU/réseau intense
  embedding  : calcul des vecteurs sentence-transformers — GPU/CPU intense
  llm        : appels API Claude/Anthropic — I/O intense, coûteux
  pdf_high   : génération PDF prioritaire (déclenché par validation utilisateur)
  pdf_low    : génération PDF batch (dimanche soir, retardataires)

Décision prefetch_multiplier=1 :
  Les appels LLM et le scraping peuvent durer 10-60s.
  Un prefetch multiplier > 1 ferait qu'un worker "volerait" des tâches
  sans pouvoir les traiter immédiatement — dégradant la latence.
  Prefetch=1 : chaque worker prend exactement 1 tâche à la fois.
"""

import os

from celery import Celery
from celery.schedules import crontab
from loguru import logger

# ---- Configuration Redis ----
# DB 0 : broker Celery (messages de tâches)
# DB 2 : backend de résultats (états des tâches terminées)
# DB 1 : réservé au rate limiting de l'API (ne pas utiliser ici)
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
CELERY_BROKER_URL: str = f"{REDIS_URL.rstrip('/')}/0"
CELERY_RESULT_BACKEND: str = f"{REDIS_URL.rstrip('/')}/2"

# ---- Instance Celery ----
celery_app = Celery(
    "mealplanner_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        # Découverte automatique des tâches dans chaque module
        "src.agents.recipe_scout.tasks",
        "src.agents.weekly_planner.tasks",
        # TASTE_PROFILE v0 : mise à jour du vecteur de goût après chaque feedback
        "src.agents.taste_profile.tasks",
        # Phase 2 — BOOK_GENERATOR : génération PDF hebdomadaire
        "src.agents.book_generator.tasks",
        # Phase 2 — RETENTION_LOOP : analyse d'engagement toutes les 4h
        "src.agents.retention_loop.tasks",
    ],
)

# ---- Configuration Celery ----
celery_app.conf.update(
    # Sérialisation : JSON pour la compatibilité inter-services
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone francophone
    timezone="Europe/Paris",
    enable_utc=True,
    # Préfixe des clés Redis pour isoler les namespaces
    # Évite les collisions si plusieurs environnements partagent le même Redis
    task_default_queue="default",
    # ---- Routes par queue ----
    # Chaque famille de tâches est isolée dans sa propre queue
    # Permet de scaler indépendamment chaque type de worker
    task_routes={
        # Scraping web : Scrapy + Playwright
        "src.agents.recipe_scout.tasks.scrape_marmiton_batch": {
            "queue": "scraping"
        },
        # Embeddings : sentence-transformers batch
        "src.agents.recipe_scout.tasks.embed_recipe": {
            "queue": "embedding"
        },
        # Appels LLM : validation qualité + tagging Claude
        "src.agents.recipe_scout.tasks.validate_recipe_quality": {
            "queue": "llm"
        },
        "src.agents.recipe_scout.tasks.tag_recipe": {
            "queue": "llm"
        },
        # Orchestration RECIPE_SCOUT nocturne
        "src.agents.recipe_scout.tasks.run_recipe_scout_nightly": {
            "queue": "default"
        },
        # Mapping OFF : batch quotidien (embedding queue — CPU modéré)
        "recipe_scout.map_ingredients_to_off": {
            "queue": "embedding"
        },
        # Génération de plan WEEKLY_PLANNER
        "weekly_planner.generate_plan": {
            "queue": "llm"
        },
        # TASTE_PROFILE : mise à jour du vecteur de goût membre
        "taste_profile.update_member_taste": {
            "queue": "embedding"
        },
        # Phase 2 — BOOK_GENERATOR : génération PDF
        "book_generator.generate_book": {
            "queue": "pdf_high",
            "priority": 9,
        },
        "book_generator.batch_missing_books": {
            "queue": "pdf_low",
            "priority": 1,
        },
        # Phase 2 — RETENTION_LOOP : analyse d'engagement
        "retention_loop.check_engagement": {
            "queue": "default",
        },
    },
    # ---- Limites de temps par tâche ----
    # soft_time_limit : lève SoftTimeLimitExceeded → permet au worker de se terminer proprement
    # time_limit      : SIGKILL si le worker ignore la limite soft
    task_soft_time_limit=300,    # 5 minutes : limite douce (nettoyage)
    task_time_limit=360,         # 6 minutes : limite dure (SIGKILL)
    # Override par queue : le scraping peut prendre plus longtemps
    task_annotations={
        "src.agents.recipe_scout.tasks.scrape_marmiton_batch": {
            "soft_time_limit": 1800,  # 30 minutes pour le scraping batch
            "time_limit": 2100,       # 35 minutes limite dure
        },
        "src.agents.recipe_scout.tasks.embed_recipe": {
            "soft_time_limit": 120,   # 2 minutes pour l'embedding d'une recette
            "time_limit": 150,
        },
    },
    # ---- Performance ----
    # prefetch_multiplier=1 : essentiel pour les tâches LLM et scraping longues
    # Évite qu'un worker monopolise la queue pendant l'exécution d'une tâche lente
    worker_prefetch_multiplier=1,
    # Acks tardifs : la tâche est confirmée seulement après exécution (pas à la réception)
    # Si le worker crashe pendant l'exécution, la tâche est ré-exécutée automatiquement
    task_acks_late=True,
    # Reject on worker lost : si le worker est tué (OOM-kill Railway), la tâche
    # est remise en queue plutôt que perdue
    task_reject_on_worker_lost=True,
    # Résultats : conserver 24h (pour debug et monitoring)
    result_expires=86400,
    # ---- Retry par défaut ----
    task_max_retries=3,
    task_default_retry_delay=30,  # 30 secondes entre les retries
    # ---- Graceful shutdown ----
    # Délai pour que les tâches en cours se terminent avant SIGKILL
    worker_shutdown_timeout=30,
)

# ---- Celery Beat Schedule ----
# Tâches planifiées récurrentes.
# RECIPE_SCOUT nocturne : lance le pipeline complet chaque nuit à 2h00.
# Heure choisie pour minimiser la concurrence avec les utilisateurs actifs.
celery_app.conf.beat_schedule = {
    # Pipeline RECIPE_SCOUT : scraping + normalisation + validation + embedding
    "recipe-scout-nightly": {
        "task": "src.agents.recipe_scout.tasks.run_recipe_scout_nightly",
        "schedule": crontab(hour=2, minute=0),  # Chaque nuit à 02h00 Paris
        "options": {"queue": "default"},
        "kwargs": {},  # Pas de paramètres — utilise la config interne
    },
    # Mapping Open Food Facts : chaque nuit à 03h00 (après RECIPE_SCOUT à 02h00)
    # Mappe les ingrédients sans off_id vers les produits Open Food Facts
    "map-ingredients-to-off-nightly": {
        "task": "recipe_scout.map_ingredients_to_off",
        "schedule": crontab(hour=3, minute=0),  # Chaque nuit à 03h00 Paris
        "options": {"queue": "embedding"},
        "kwargs": {"batch_size": 50},
    },
    # Phase 2 — BOOK_GENERATOR : batch dimanche 22h (filet de sécurité PDFs manquants)
    "batch-missing-pdfs-sunday": {
        "task": "book_generator.batch_missing_books",
        "schedule": crontab(hour=22, minute=0, day_of_week=0),  # Dimanche 22h00 Paris
        "options": {"queue": "pdf_low"},
    },
    # Phase 2 — RETENTION_LOOP : analyse d'engagement toutes les 4 heures
    "retention-loop-check": {
        "task": "retention_loop.check_engagement",
        "schedule": crontab(minute=0, hour="*/4"),  # Toutes les 4 heures
        "options": {"queue": "default"},
    },
}


def configure_logging() -> None:
    """
    Configure loguru pour les workers Celery.

    Format JSON en production, coloré en développement.
    Même convention que l'API FastAPI pour la cohérence des logs centralisés.
    """
    import sys

    from loguru import logger

    env = os.getenv("ENV", "dev")
    log_level = os.getenv("CELERY_LOG_LEVEL", "INFO")

    logger.remove()
    if env in ("prod", "staging"):
        logger.add(sys.stdout, level=log_level, serialize=True)
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan> - {message}"
            ),
        )


# Configuration du logging au chargement du module
configure_logging()

logger.info(
    "celery_app_configured",
    broker=CELERY_BROKER_URL.replace(REDIS_URL, "redis://***"),
    backend=CELERY_RESULT_BACKEND.replace(REDIS_URL, "redis://***"),
)
