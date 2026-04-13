"""Instance Celery légère pour l'API — envoie des tâches au worker via Redis."""

import os
from celery import Celery

_celery_instance: Celery | None = None


def get_celery_sender() -> Celery:
    """Retourne l'instance Celery (lazy init pour lire REDIS_URL au bon moment)."""
    global _celery_instance
    if _celery_instance is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379").rstrip("/")
        _celery_instance = Celery(
            "presto_api_sender",
            broker=f"{redis_url}/0",
            backend=f"{redis_url}/2",
        )
    return _celery_instance
