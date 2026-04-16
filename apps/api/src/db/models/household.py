"""household.py — Modèles ORM pour le domaine Auth/Tenancy.

Tables couvertes :
- households         : unité de multi-tenancy (un foyer = un tenant)
- household_members  : membres d'un foyer (lien avec Supabase Auth)
- member_preferences : préférences alimentaires par membre
- member_taste_vectors : vecteurs de goût (gérés par TASTE_PROFILE agent)

Architecture SQLAlchemy 2.0 :
- Mapped[T] et mapped_column() : syntaxe strictement typée (pas de Column legacy)
- UUID(as_uuid=True) : les UUIDs sont exposés comme uuid.UUID en Python
- TIMESTAMP(timezone=True) : tous les timestamps sont timezone-aware (UTC)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.subscription import Subscription


class Household(Base):
    """Foyer — unité de multi-tenancy. Chaque foyer est isolé par RLS.

    Un foyer correspond à un abonnement Stripe (Phase 3).
    La clé de tenancy utilisée dans toutes les RLS policies est l'id de cette table.
    """

    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="starter",
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(Text)
    drive_provider: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        default=None,
        comment="Fournisseur de drive préféré : 'leclerc', 'auchan', 'carrefour', 'intermarche', 'other', ou null.",
    )
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
        CheckConstraint("plan IN ('starter', 'famille', 'coach')", name="households_plan_check"),
    )

    # Relations
    members: Mapped[list["HouseholdMember"]] = relationship(
        "HouseholdMember",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="select",
    )
    # Phase 2 : abonnement Stripe (un seul par foyer, None si jamais souscrit)
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription",
        back_populates="household",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )


class HouseholdMember(Base):
    """Membre d'un foyer.

    supabase_user_id est le pont entre Supabase Auth (auth.users) et le schéma métier.
    NULL pour les membres "fantôme" (enfants sans compte Supabase).
    UNIQUE(supabase_user_id) : un utilisateur Supabase ne peut appartenir qu'à un seul foyer.
    """

    __tablename__ = "household_members"

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
    supabase_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    birth_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
    is_child: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
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
        UniqueConstraint("supabase_user_id", name="uq_household_members_supabase_user_id"),
        CheckConstraint("role IN ('owner', 'member')", name="household_members_role_check"),
    )

    # Relations
    household: Mapped["Household"] = relationship("Household", back_populates="members")
    preferences: Mapped["MemberPreference | None"] = relationship(
        "MemberPreference",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=False,
    )
    taste_vector: Mapped["MemberTasteVector | None"] = relationship(
        "MemberTasteVector",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=False,
    )


class MemberPreference(Base):
    """Préférences alimentaires d'un membre.

    diet_tags et allergies sont des JSONB pour flexibilité (pas de migration si nouveaux tags).
    budget_pref est résolu en ordre sémantique par get_household_constraints() :
    'économique' < 'moyen' < 'premium'.
    """

    __tablename__ = "member_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    diet_tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    allergies: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    dislikes: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    cooking_time_max: Mapped[int | None] = mapped_column(Integer)
    budget_pref: Mapped[str | None] = mapped_column(Text)
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
        UniqueConstraint("member_id", name="uq_member_preferences_member_id"),
        CheckConstraint("cooking_time_max > 0", name="member_preferences_cooking_time_max_check"),
        CheckConstraint(
            "budget_pref IN ('économique', 'moyen', 'premium')",
            name="member_preferences_budget_pref_check",
        ),
    )

    # Relations
    member: Mapped["HouseholdMember"] = relationship(
        "HouseholdMember",
        back_populates="preferences",
    )


class MemberTasteVector(Base):
    """Vecteur de goût synthétique par membre.

    Mis à jour après chaque feedback par l'agent TASTE_PROFILE (tâche Celery).
    La recherche cosine entre ce vecteur et recipe_embeddings.embedding
    est le coeur du moteur de recommandation personnalisé.

    IMPORTANT : ne jamais modifier ce vecteur côté API utilisateur.
    Écriture réservée au service_role (TASTE_PROFILE bypasse la RLS).
    """

    __tablename__ = "member_taste_vectors"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Vector(384) : dimension all-MiniLM-L6-v2 — ne pas mélanger avec d'autres modèles
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relations
    member: Mapped["HouseholdMember"] = relationship(
        "HouseholdMember",
        back_populates="taste_vector",
    )
