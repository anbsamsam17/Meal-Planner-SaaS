"""subscription.py — Modèles ORM pour le domaine Stripe / Abonnements.

Tables couvertes :
- subscriptions    : abonnement Stripe par foyer (Phase 2 enrichi)
- engagement_events : signaux d'engagement foyer (RETENTION_LOOP)

Décision architecturale (2026-04-12) :
- Subscription séparée de household.py : responsabilité unique, évite de grossir
  household.py qui gère déjà Household + HouseholdMember + MemberPreference + MemberTasteVector.
- EngagementEvent dans ce fichier car couplé au cycle de vie des abonnements (churn, rétention).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base


class Subscription(Base):
    """Abonnement Stripe d'un foyer.

    Phase 0/1 : table stub, non peuplée. Le plan households.plan est la source de vérité.
    Phase 2    : colonnes Stripe complètes ajoutées (stripe_customer_id, stripe_price_id,
                 cancel_at_period_end, canceled_at, trial_end).
    Phase 3    : webhooks Stripe actifs, cette table devient la source de vérité du statut.

    Contraintes :
    - UNIQUE(household_id) : un seul enregistrement par foyer (même annulé).
    - index partiel ix_subscriptions_household_active : unicité des status active/trialing.
    - status CHECK : valeurs alignées sur les statuts Stripe officiels.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Identifiants Stripe
    stripe_sub_id: Mapped[str] = mapped_column(Text, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(Text)
    stripe_price_id: Mapped[str | None] = mapped_column(Text)
    # Plan interne (aligné sur le CHECK de la table households)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    # Statut Stripe — valeurs officielles Stripe + 'canceled' pour les abonnements résiliés
    status: Mapped[str] = mapped_column(Text, nullable=False)
    # Fin de période de facturation courante (UTC)
    current_period_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    # Annulation programmée : l'utilisateur a demandé l'annulation, accès maintenu jusqu'à current_period_end
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    # Timestamp de l'annulation effective (NULL si toujours actif)
    canceled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Fin du trial gratuit (NULL si pas de période d'essai)
    trial_end: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("household_id", name="uq_subscriptions_household_id"),
        UniqueConstraint("stripe_sub_id", name="uq_subscriptions_stripe_sub_id"),
        CheckConstraint(
            "plan IN ('starter', 'famille', 'coach')",
            name="subscriptions_plan_check",
        ),
        CheckConstraint(
            "status IN ('active', 'trialing', 'past_due', 'canceled', 'incomplete', 'incomplete_expired', 'unpaid')",
            name="subscriptions_status_check",
        ),
    )

    # Relation inverse vers le foyer (optionnelle — évite le chargement eager par défaut)
    household: Mapped["Household"] = relationship(  # type: ignore[name-defined]
        "Household",
        back_populates="subscription",
        lazy="select",
    )


class EngagementEvent(Base):
    """Événement d'engagement d'un foyer — table de signaux pour RETENTION_LOOP.

    Écrit exclusivement par l'agent RETENTION_LOOP (service_role Celery).
    Lecture autorisée aux membres authentifiés (policy RLS subscriptions_select_own).

    event_type : catégorie de l'événement (voir COMMENT ON COLUMN dans 04-phase2-schema.sql).
    event_data : contexte libre JSONB, extensible sans migration de schéma.

    Cycle de rétention typique :
      app_opened → plan_generated → recipe_rated → [at_risk → win_back_sent → reactivated]
    """

    __tablename__ = "engagement_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Type d'événement — non contraint par CHECK pour permettre l'extension sans migration
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    # Données contextuelles libres
    event_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="'{}'",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Pas de relation ORM vers Household : lecture directe par household_id suffisante
    # (les queries RETENTION_LOOP font des GROUP BY household_id, pas de jointure ORM)
