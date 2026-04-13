"""
Instance Celery legere pour l'API -- envoie des taches au worker sans importer ses modules.

Utilise send_task() pour envoyer des taches par nom (string) au broker Redis.
Le worker n'a PAS besoin d'etre importe -- seule la connexion Redis est requise.

Reutilisable dans tous les endpoints qui declenchent des taches asynchrones :
- POST /plans/generate  (weekly_planner.generate_plan)
- POST /books/generate  (book_generator.generate_book)   -- Phase 2
"""

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Normalisation : retirer un eventuel trailing slash avant d'ajouter le numero de DB
_redis_base = REDIS_URL.rstrip("/")

celery_sender = Celery(
    "presto_api_sender",
    broker=f"{_redis_base}/0",
    backend=f"{_redis_base}/2",
)
