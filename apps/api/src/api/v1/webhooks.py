"""
Endpoint webhook Stripe — traitement des événements d'abonnement.

IMPORTANT : cet endpoint ne doit PAS avoir de rate limit ni d'auth JWT.
La sécurité est assurée par la vérification de la signature Stripe
(STRIPE_WEBHOOK_SECRET).

Événements traités :
  checkout.session.completed      → crée/met à jour l'abonnement
  customer.subscription.updated   → met à jour plan/status
  customer.subscription.deleted   → marque canceled
  invoice.payment_failed          → marque past_due

Isolation tenant : chaque event contient household_id dans les metadata.
"""

from __future__ import annotations

# Import conditionnel : stripe peut ne pas être installé en environnement de test
try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger
from sqlalchemy import text

from src.core.config import get_settings

router = APIRouter(tags=["webhooks"])
settings = get_settings()

# ---- Event handlers ----


async def _handle_checkout_completed(
    session_obj: dict, db_session_factory
) -> None:
    """
    Traite checkout.session.completed.

    Crée ou met à jour l'abonnement dans la table subscriptions.
    Le plan et le household_id sont dans les metadata de la session.
    """
    household_id = session_obj.get("metadata", {}).get("household_id")
    plan_name = session_obj.get("metadata", {}).get("plan_name")
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")

    if not household_id or not plan_name:
        logger.warning(
            "stripe_webhook_checkout_missing_metadata",
            session_id=session_obj.get("id"),
        )
        return

    logger.info(
        "stripe_webhook_checkout_completed",
        household_id=household_id,
        plan=plan_name,
        subscription_id=subscription_id,
    )

    async with db_session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO subscriptions
                    (household_id, stripe_customer_id, stripe_sub_id, plan, status)
                VALUES
                    (:hid, :cid, :sid, :plan, 'active')
                ON CONFLICT (household_id)
                DO UPDATE SET
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    stripe_sub_id = EXCLUDED.stripe_sub_id,
                    plan = EXCLUDED.plan,
                    status = 'active',
                    updated_at = NOW()
                """
            ),
            {
                "hid": household_id,
                "cid": customer_id,
                "sid": subscription_id,
                "plan": plan_name,
            },
        )
        await session.commit()


async def _handle_subscription_updated(
    subscription: dict, db_session_factory
) -> None:
    """
    Traite customer.subscription.updated.

    Met à jour le plan, le statut et la date de fin de période.
    """
    subscription_id = subscription.get("id")
    status_val = subscription.get("status")
    current_period_end = subscription.get("current_period_end")

    # Détermine le plan depuis les items de la subscription
    plan_name = _extract_plan_from_subscription(subscription)

    logger.info(
        "stripe_webhook_subscription_updated",
        subscription_id=subscription_id,
        status=status_val,
        plan=plan_name,
    )

    async with db_session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE subscriptions
                SET
                    plan = COALESCE(:plan, plan),
                    status = :status,
                    current_period_end = TO_TIMESTAMP(:period_end),
                    updated_at = NOW()
                WHERE stripe_sub_id = :sid
                """
            ),
            {
                "plan": plan_name,
                "status": status_val,
                "period_end": current_period_end,
                "sid": subscription_id,
            },
        )
        await session.commit()


async def _handle_subscription_deleted(
    subscription: dict, db_session_factory
) -> None:
    """
    Traite customer.subscription.deleted.

    Marque l'abonnement comme canceled et remet le plan à starter.
    """
    subscription_id = subscription.get("id")

    logger.info(
        "stripe_webhook_subscription_deleted",
        subscription_id=subscription_id,
    )

    async with db_session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE subscriptions
                SET status = 'canceled', plan = 'starter', updated_at = NOW()
                WHERE stripe_sub_id = :sid
                """
            ),
            {"sid": subscription_id},
        )
        await session.commit()


async def _handle_invoice_payment_failed(
    invoice: dict, db_session_factory
) -> None:
    """
    Traite invoice.payment_failed.

    Marque le statut comme past_due — déclenche la logique de rétention.
    """
    subscription_id = invoice.get("subscription")
    customer_id = invoice.get("customer")

    logger.warning(
        "stripe_webhook_payment_failed",
        subscription_id=subscription_id,
        customer_id=customer_id,
    )

    async with db_session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE subscriptions
                SET status = 'past_due', updated_at = NOW()
                WHERE stripe_sub_id = :sid
                """
            ),
            {"sid": subscription_id},
        )
        await session.commit()


def _extract_plan_from_subscription(subscription: dict) -> str | None:
    """
    Extrait le nom du plan Presto depuis une Subscription Stripe.

    Compare les Price IDs des items avec les Price IDs configurés dans PLANS.
    Retourne None si aucun match (plan conservé tel quel).
    """
    from src.core.stripe_config import PLANS

    items = subscription.get("items", {}).get("data", [])
    for item in items:
        price_id = item.get("price", {}).get("id")
        for plan_name, plan_config in PLANS.items():
            if plan_config.get("price_id") == price_id:
                return plan_name

    return None


# ---- Endpoint webhook ----


@router.post(
    "/webhooks/stripe",
    summary="Webhook Stripe",
    description=(
        "Reçoit les événements Stripe et met à jour les abonnements. "
        "AUCUNE authentification JWT — sécurisé par vérification de signature Stripe. "
        "AUCUN rate limit — Stripe envoie des events à la demande."
    ),
    status_code=status.HTTP_200_OK,
    include_in_schema=True,
)
async def stripe_webhook(request: Request) -> dict:
    """
    Point d'entrée pour les webhooks Stripe.

    La signature Stripe est vérifiée avec STRIPE_WEBHOOK_SECRET.
    En cas de signature invalide → 400 (Stripe considère l'event comme non délivré
    et réessaiera plus tard).

    Args:
        request: Requête FastAPI brute (le body doit être lu tel quel, non parsé).

    Returns:
        {"received": True} si l'event est traité avec succès.
    """
    # Vérification que le package Stripe est disponible
    if stripe is None:
        logger.error("stripe_webhook_package_missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Package Stripe non installé.",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("stripe_webhook_missing_signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header stripe-signature manquant.",
        )

    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("stripe_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STRIPE_WEBHOOK_SECRET non configuré.",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except ValueError as exc:
        # Payload invalide
        logger.warning("stripe_webhook_invalid_payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload Stripe invalide.",
        ) from exc
    except Exception as exc:
        # Couvre stripe.error.SignatureVerificationError (quand stripe est importé)
        # et tout autre problème de signature. Potentiellement une attaque.
        if "SignatureVerificationError" in type(exc).__name__:
            logger.warning(
                "stripe_webhook_invalid_signature",
                error=str(exc),
                ip=request.client.host if request.client else "unknown",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signature Stripe invalide.",
            ) from exc
        raise

    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(
        "stripe_webhook_received",
        event_type=event_type,
        event_id=event["id"],
    )

    # Récupération de la session DB factory
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        logger.error("stripe_webhook_no_db")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non disponible.",
        )

    # Dispatch par type d'événement
    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event_data, db_session_factory)

        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event_data, db_session_factory)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event_data, db_session_factory)

        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(event_data, db_session_factory)

        else:
            # Event non géré — logué mais pas d'erreur (Stripe n'a pas besoin de retry)
            logger.debug("stripe_webhook_unhandled_event", event_type=event_type)

    except Exception as exc:
        # En cas d'erreur DB, on retourne 500 pour que Stripe retente
        logger.error(
            "stripe_webhook_processing_error",
            event_type=event_type,
            event_id=event["id"],
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur de traitement de l'event {event_type}.",
        ) from exc

    return {"received": True}
