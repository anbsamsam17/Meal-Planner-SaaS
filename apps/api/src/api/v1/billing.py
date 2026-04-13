"""
Endpoints Stripe Billing — gestion des abonnements Presto.

Endpoints :
  POST /api/v1/billing/checkout  → crée une Checkout Session Stripe (rate limit 10/h)
  POST /api/v1/billing/portal    → crée une Customer Portal session (rate limit 10/h)
  GET  /api/v1/billing/status    → statut d'abonnement du foyer

Webhook (pas d'auth JWT, vérification signature Stripe) :
  POST /api/v1/webhooks/stripe   → traite les events Stripe

Sécurité :
- Mode test uniquement : STRIPE_SECRET_KEY = sk_test_...
- Signature webhook vérifiée via STRIPE_WEBHOOK_SECRET
- Isolation tenant : chaque opération est liée au household_id JWT
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

# Import conditionnel : stripe peut ne pas être installé en environnement de test
try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.rate_limit import LIMIT_LLM_PLAN_USER, get_user_key, limiter
from src.core.security import TokenPayload, get_current_user
from src.core.stripe_config import PLANS

router = APIRouter(prefix="/billing", tags=["billing"])

settings = get_settings()


def _check_stripe_configured() -> None:
    """
    Vérifie que Stripe est configuré avant tout appel API.

    Retourne HTTP 503 si STRIPE_SECRET_KEY est absente ou vide.
    Évite un crash ImportError/AttributeError si le package stripe n'est pas installé.
    """
    if stripe is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Package Stripe non installé. Installer : pip install stripe",
        )
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe non configuré (STRIPE_SECRET_KEY manquante).",
        )
    # Injection de la clé au moment de l'appel (pas au module load)
    stripe.api_key = settings.STRIPE_SECRET_KEY  # type: ignore[union-attr]


# ---- Helpers ----


def get_current_user_dep(request: Request) -> TokenPayload:
    """Dépendance FastAPI pour l'authentification JWT."""
    return get_current_user(request, settings.SUPABASE_ANON_KEY)


async def get_db(request: Request) -> AsyncSession:
    """Session DB depuis app.state."""
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Base de données non disponible.")
    async with factory() as session:
        yield session


async def _get_household_id(session: AsyncSession, user_id: str) -> str:
    """Récupère le household_id depuis household_members."""
    result = await session.execute(
        text(
            "SELECT household_id FROM household_members "
            "WHERE supabase_user_id = :user_id LIMIT 1"
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vous n'appartenez à aucun foyer.",
        )
    return str(row[0])


async def _get_or_create_stripe_customer(
    session: AsyncSession, household_id: str, user_email: str | None
) -> str:
    """
    Retourne le stripe_customer_id existant ou en crée un nouveau.

    Évite de créer plusieurs Customer Stripe pour le même foyer.
    Stocke le customer_id dans la table subscriptions.
    """
    result = await session.execute(
        text(
            "SELECT stripe_customer_id FROM subscriptions "
            "WHERE household_id = :hid LIMIT 1"
        ),
        {"hid": household_id},
    )
    row = result.fetchone()
    if row and row[0]:
        return row[0]

    # Création d'un nouveau Customer Stripe
    customer = stripe.Customer.create(
        metadata={"household_id": household_id},
        email=user_email,
    )
    customer_id = customer["id"]

    # Persistance dans subscriptions (upsert)
    await session.execute(
        text(
            """
            INSERT INTO subscriptions (household_id, stripe_customer_id, plan, status)
            VALUES (:hid, :cid, 'starter', 'inactive')
            ON CONFLICT (household_id)
            DO UPDATE SET stripe_customer_id = EXCLUDED.stripe_customer_id
            """
        ),
        {"hid": household_id, "cid": customer_id},
    )
    await session.commit()

    return customer_id


# ---- Schémas ----


class CheckoutRequest(BaseModel):
    """Corps de la requête pour créer une session de paiement."""

    plan: str = Field(
        ...,
        description="Plan cible : 'famille' ou 'coach'.",
        pattern="^(famille|coach)$",
    )


class CheckoutResponse(BaseModel):
    """Réponse contenant l'URL de la Checkout Session Stripe."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Réponse contenant l'URL du Customer Portal Stripe."""

    portal_url: str


class SubscriptionStatus(BaseModel):
    """Statut d'abonnement du foyer."""

    plan: str
    status: str
    current_period_end: str | None = None
    stripe_customer_id: str | None = None


# ---- Endpoints ----


@router.post(
    "/checkout",
    summary="Créer une session de paiement Stripe",
    description=(
        "Crée une Checkout Session Stripe pour souscrire au plan choisi. "
        "Retourne l'URL de paiement à ouvrir dans le navigateur. "
        "Rate limit : 10/heure par utilisateur."
    ),
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Plan invalide ou Price ID non configuré."},
        404: {"description": "Foyer introuvable."},
        429: {"description": "Rate limit dépassé (10/heure)."},
    },
)
@limiter.limit("10/hour", key_func=get_user_key)
async def create_checkout_session(
    request: Request,
    body: CheckoutRequest,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Crée une Stripe Checkout Session pour le plan demandé.

    La session expire après 30 minutes (Stripe default).
    L'utilisateur est redirigé vers /billing/success ou /billing/cancel.

    Args:
        request: Requête FastAPI (requis par slowapi).
        body: Plan sélectionné.
        session: Session DB.
        user: Payload JWT.

    Returns:
        CheckoutResponse avec l'URL Stripe.
    """
    _check_stripe_configured()

    plan_config = PLANS.get(body.plan)
    if plan_config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{body.plan}' invalide.",
        )

    price_id = plan_config.get("price_id")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le plan '{body.plan}' n'a pas de Price ID configuré. "
                "Vérifier STRIPE_PRICE_FAMILLE ou STRIPE_PRICE_COACH dans les variables d'env."
            ),
        )

    household_id = await _get_household_id(session, user.user_id)

    # Récupère ou crée le Customer Stripe (idempotent)
    customer_id = await _get_or_create_stripe_customer(
        session, household_id, getattr(user, "email", None)
    )

    # URLs de retour après paiement
    base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/billing/cancel"

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "household_id": household_id,
            "plan_name": body.plan,
        },
        # Collecte l'adresse de facturation (obligatoire en Europe)
        billing_address_collection="required",
        # Taxe automatique Stripe Tax (désactivé en mode test sans config)
        # automatic_tax={"enabled": True},
    )

    logger.info(
        "stripe_checkout_created",
        household_id=household_id,
        plan=body.plan,
        session_id=checkout_session["id"],
    )

    return CheckoutResponse(checkout_url=checkout_session["url"])


@router.post(
    "/portal",
    summary="Créer une session Customer Portal Stripe",
    description=(
        "Crée une session vers le portail client Stripe pour gérer l'abonnement "
        "(annuler, changer de plan, mettre à jour la CB). "
        "Rate limit : 10/heure par utilisateur."
    ),
    response_model=PortalResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Foyer sans abonnement Stripe."},
        429: {"description": "Rate limit dépassé (10/heure)."},
    },
)
@limiter.limit("10/hour", key_func=get_user_key)
async def create_customer_portal(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Redirige vers le Customer Portal Stripe pour la gestion de l'abonnement.

    Nécessite qu'un Customer Stripe existe déjà (au moins une Checkout effectuée).

    Args:
        request: Requête FastAPI.
        session: Session DB.
        user: Payload JWT.

    Returns:
        PortalResponse avec l'URL du portail.
    """
    _check_stripe_configured()

    household_id = await _get_household_id(session, user.user_id)

    # Récupère le customer_id (doit exister)
    result = await session.execute(
        text(
            "SELECT stripe_customer_id FROM subscriptions "
            "WHERE household_id = :hid LIMIT 1"
        ),
        {"hid": household_id},
    )
    row = result.fetchone()

    if row is None or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun abonnement Stripe associé à votre foyer. Effectuez d'abord un paiement.",
        )

    customer_id = row[0]
    base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    return_url = f"{base_url}/dashboard"

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )

    logger.info(
        "stripe_portal_created",
        household_id=household_id,
        customer_id=customer_id,
    )

    return PortalResponse(portal_url=portal_session["url"])


@router.get(
    "/status",
    summary="Statut d'abonnement du foyer",
    description="Retourne le plan actuel, le statut et la date de fin de période.",
    response_model=SubscriptionStatus,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("60/minute", key_func=get_user_key)
async def get_subscription_status(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user_dep),
) -> Any:
    """
    Retourne le statut d'abonnement du foyer.

    Si aucun abonnement trouvé → plan starter (free).

    Args:
        request: Requête FastAPI.
        session: Session DB.
        user: Payload JWT.

    Returns:
        SubscriptionStatus avec plan, status, current_period_end.
    """
    household_id = await _get_household_id(session, user.user_id)

    result = await session.execute(
        text(
            """
            SELECT plan, status, current_period_end, stripe_customer_id
            FROM subscriptions
            WHERE household_id = :hid
            ORDER BY current_period_end DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"hid": household_id},
    )
    row = result.mappings().one_or_none()

    if row is None:
        return SubscriptionStatus(plan="starter", status="inactive")

    period_end = row.get("current_period_end")
    period_end_str = str(period_end) if period_end else None

    return SubscriptionStatus(
        plan=row["plan"] or "starter",
        status=row["status"] or "inactive",
        current_period_end=period_end_str,
        stripe_customer_id=row.get("stripe_customer_id"),
    )
