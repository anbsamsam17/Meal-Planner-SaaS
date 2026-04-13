"""
Middleware de vérification d'abonnement Stripe.

Fournit la dépendance FastAPI `require_plan` qui vérifie que le foyer
possède un plan d'abonnement suffisant avant d'accéder aux endpoints premium.

Usage dans les routes :
    from src.core.subscription import require_plan

    @router.get("/premium-feature")
    async def premium(
        _: None = Depends(require_plan("famille")),
        user: TokenPayload = Depends(get_current_user_dep),
    ):
        ...

Plans et niveaux :
    starter (0)  → accès aux features de base
    famille (1)  → accès PDF hebdo, profils famille, frigo
    coach   (2)  → accès coach nutrition, tracking macros
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.stripe_config import PLAN_ORDER, get_plan_level


async def _get_db_session(request: Request) -> AsyncSession:
    """Session DB depuis app.state."""
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données non disponible.",
        )
    async with db_session_factory() as session:
        yield session


async def _get_household_subscription(
    session: AsyncSession,
    household_id: str,
) -> dict[str, Any] | None:
    """
    Récupère l'abonnement actif du foyer depuis la table subscriptions.

    Un abonnement est considéré actif si son statut est 'active' ou 'trialing'.

    Args:
        session: Session SQLAlchemy async.
        household_id: UUID du foyer (str).

    Returns:
        dict avec plan et status, ou None si aucun abonnement actif.
    """
    result = await session.execute(
        text(
            """
            SELECT plan, status, current_period_end
            FROM subscriptions
            WHERE household_id = :household_id
              AND status IN ('active', 'trialing')
            ORDER BY current_period_end DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"household_id": household_id},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


def require_plan(min_plan: str = "starter"):
    """
    Factory de dépendance FastAPI.

    Vérifie que le foyer de l'utilisateur authentifié possède un abonnement
    dont le niveau est >= au plan minimum requis.

    Args:
        min_plan: Niveau minimum requis ('starter', 'famille', 'coach').

    Returns:
        Dépendance FastAPI (callable) à utiliser dans Depends().

    Raises:
        ValueError: si min_plan est un nom de plan inconnu.
    """
    if min_plan not in PLAN_ORDER:
        raise ValueError(
            f"Plan '{min_plan}' invalide. Plans valides : {PLAN_ORDER}"
        )

    min_level = get_plan_level(min_plan)

    async def _check_subscription(
        request: Request,
        session: AsyncSession = Depends(_get_db_session),
    ) -> None:
        """
        Vérifie l'abonnement du foyer.

        Lit household_id depuis request.state (injecté par le middleware JWT).
        Si le foyer est en plan starter (pas de stripe), level = 0.
        """
        household_id = getattr(request.state, "household_id", None)

        if household_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise pour accéder à cette ressource.",
            )

        # Plan starter : pas de vérification Stripe nécessaire (niveau 0)
        if min_level == 0:
            return

        subscription = await _get_household_subscription(session, str(household_id))

        if subscription is None:
            # Aucun abonnement actif → plan starter implicite
            current_plan = "starter"
            current_level = 0
        else:
            current_plan = subscription.get("plan", "starter")
            current_level = get_plan_level(current_plan)

        if current_level < min_level:
            logger.warning(
                "subscription_check_denied",
                household_id=str(household_id),
                current_plan=current_plan,
                required_plan=min_plan,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Cette fonctionnalité requiert le plan '{min_plan}' ou supérieur. "
                    f"Votre plan actuel : '{current_plan}'. "
                    f"Passez à la version supérieure sur /api/v1/billing/checkout."
                ),
            )

        logger.debug(
            "subscription_check_passed",
            household_id=str(household_id),
            current_plan=current_plan,
            required_plan=min_plan,
        )

    return _check_subscription
