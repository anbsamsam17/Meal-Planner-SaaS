"""
Router agrégé v1 — rassemble tous les sous-routers de l'API v1.

Chaque domaine fonctionnel a son propre fichier de routes.
Ce fichier les inclut sous le préfixe /api/v1.

Conventions de nommage :
- Les endpoints retournent des erreurs en JSON (pas en HTML)
- Tous les endpoints sont versionnés via /api/v1/
- La documentation OpenAPI est générée automatiquement
"""

from fastapi import APIRouter

from src.api.v1 import admin, billing, book, feedbacks, fridge, health, households, plans, recipes, webhooks

# Router racine v1 — inclus dans l'app principale sous /api/v1
api_v1_router = APIRouter(prefix="/api/v1")

# Santé — sans préfixe supplémentaire (GET /api/v1/health, GET /api/v1/ready)
api_v1_router.include_router(health.router)

# Recettes — préfixe /recipes (+ filtres avancés Phase 2)
api_v1_router.include_router(recipes.router)

# Foyers — préfixe /households (multi-tenancy, onboarding)
api_v1_router.include_router(households.router)

# Plans — préfixe /plans (génération, validation, liste de courses)
api_v1_router.include_router(plans.router)

# Livre de recettes PDF — préfixe /plans/{plan_id}/book (BOOK_GENERATOR Phase 2)
api_v1_router.include_router(book.router)

# Feedbacks — préfixe /feedbacks (notations, historique, TASTE_PROFILE)
api_v1_router.include_router(feedbacks.router)

# Administration — préfixe /admin (déclenchement manuel des agents, ops)
api_v1_router.include_router(admin.router)

# Billing Stripe — préfixe /billing (checkout, portal, status) — Phase 2
api_v1_router.include_router(billing.router)

# Frigo — préfixe /fridge (gestion stock + suggestions) — Phase 2
api_v1_router.include_router(fridge.router)

# Webhooks Stripe — /webhooks/stripe (pas d'auth JWT, signature Stripe) — Phase 2
api_v1_router.include_router(webhooks.router)
