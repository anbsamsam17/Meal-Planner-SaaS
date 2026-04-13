"""planning.py — Modèles ORM pour le domaine Planification hebdomadaire.

Tables couvertes :
- weekly_plans    : plan de dîners généré par WEEKLY_PLANNER
- planned_meals   : repas individuels composant un plan
- shopping_lists  : liste de courses consolidée par CART_BUILDER
- fridge_items    : stock frigo actuel du foyer (mode anti-gaspi)
- weekly_books    : référence au PDF généré par BOOK_GENERATOR

Note sur week_start :
- Toujours un lundi (contrainte DB ISODOW + contrainte applicative).
- validated_at : timestamp quand le plan passe en status='validated'.
  Déclenche la tâche Celery BOOK_GENERATOR (génération PDF eager).
  Voir 13-pdf-generation-strategy.md pour le flux complet.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base


class WeeklyPlan(Base):
    """Plan de dîners hebdomadaire généré par l'agent WEEKLY_PLANNER.

    Contraintes critiques :
    - week_start ISODOW = 1 : toujours un lundi (garantie DB + applicative).
    - UNIQUE(household_id, week_start) : un seul plan par foyer par semaine.
    - validated_at : NULL en draft, set lors de la validation → déclenche PDF.
    - status 'validated' → seul ce statut déclenche CART_BUILDER et BOOK_GENERATOR.
    """

    __tablename__ = "weekly_plans"

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
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="'draft'")
    # N1 fix (review 2026-04-12) : colonne pour 13-pdf-generation-strategy.md
    validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
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
        UniqueConstraint("household_id", "week_start", name="uq_weekly_plans_household_id_week_start"),
        CheckConstraint(
            "status IN ('draft', 'validated', 'archived')",
            name="weekly_plans_status_check",
        ),
        # M6 fix (review 2026-04-12) : ISODOW 1 = lundi (ISO 8601)
        CheckConstraint(
            "EXTRACT(ISODOW FROM week_start) = 1",
            name="weekly_plans_week_start_monday_check",
        ),
    )

    # Relations
    meals: Mapped[list["PlannedMeal"]] = relationship(
        "PlannedMeal",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlannedMeal.day_of_week",
    )
    shopping_list: Mapped["ShoppingList | None"] = relationship(
        "ShoppingList",
        back_populates="plan",
        cascade="all, delete-orphan",
        uselist=False,
    )
    book: Mapped["WeeklyBook | None"] = relationship(
        "WeeklyBook",
        back_populates="plan",
        cascade="all, delete-orphan",
        uselist=False,
    )


class PlannedMeal(Base):
    """Repas individuel composant un plan hebdomadaire.

    day_of_week : 1=lundi, ..., 7=dimanche (cohérent avec ISODOW).
    slot : 'dinner' uniquement en v0/v1, extensible à 'lunch' en v2.
    servings_adjusted : permet de scaler les portions sans modifier la recette source.

    UNIQUE(plan_id, day_of_week, slot) : un seul repas par jour et par slot dans un plan.
    """

    __tablename__ = "planned_meals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weekly_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[str] = mapped_column(Text, nullable=False, server_default="'dinner'")
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    servings_adjusted: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("plan_id", "day_of_week", "slot", name="uq_planned_meals_plan_day_slot"),
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="planned_meals_day_of_week_check"),
        CheckConstraint("slot IN ('dinner', 'lunch')", name="planned_meals_slot_check"),
        CheckConstraint("servings_adjusted > 0", name="planned_meals_servings_adjusted_check"),
    )

    # Relations
    plan: Mapped["WeeklyPlan"] = relationship("WeeklyPlan", back_populates="meals")


class ShoppingList(Base):
    """Liste de courses consolidée générée par CART_BUILDER.

    items : JSONB structuré [{"ingredient_id": "...", "name": "carotte", "quantity": 500, ...}]
    Partagée en temps réel via Supabase Realtime (les membres cochent les items).
    UNIQUE(plan_id) : une seule liste de courses par plan.
    """

    __tablename__ = "shopping_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weekly_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("plan_id", name="uq_shopping_lists_plan_id"),
    )

    # Relations
    plan: Mapped["WeeklyPlan"] = relationship("WeeklyPlan", back_populates="shopping_list")


class FridgeItem(Base):
    """Stock frigo actuel du foyer.

    WEEKLY_PLANNER lit cette table pour prioriser les recettes utilisant
    les ingrédients proches de péremption (mode anti-gaspi).
    expiry_date : NULL si l'ingrédient est non périssable.

    Phase 2 — colonnes ajoutées (04-phase2-schema.sql) :
    - notes     : note libre saisie par l'utilisateur
    - is_staple : true = produit permanent (sel, huile...) exclu des suggestions de courses
    """

    __tablename__ = "fridge_items"

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
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Numeric] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # Phase 2 : note libre (ex : "flacon ouvert", "à finir avant vendredi")
    notes: Mapped[str | None] = mapped_column(Text)
    # Phase 2 : produit permanent — exclu de suggest_recipes_from_fridge et des listes de courses
    is_staple: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="fridge_items_quantity_check"),
    )


class WeeklyBook(Base):
    """Référence au PDF hebdomadaire généré par BOOK_GENERATOR.

    pdf_r2_key : clé Cloudflare R2 au format "books/{household_id}/{year-week}.pdf".
    notification_sent_at : NULL déclenche l'envoi push/email par RETENTION_LOOP (Celery beat).
    UNIQUE(plan_id) : un seul PDF par plan validé.

    content_hash : SHA-256 du contenu logique du plan (recettes + portions).
    Idempotence Phase 3 : si content_hash est identique à la dernière génération,
    BOOK_GENERATOR ignore la re-génération et retourne le pdf_r2_key existant.
    Ajouté via migration 0003_pdf_idempotence_columns.py (voir 13-pdf-generation-strategy.md).
    """

    __tablename__ = "weekly_books"

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
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weekly_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    pdf_r2_key: Mapped[str] = mapped_column(Text, nullable=False)
    # SHA-256 du contenu logique — NULL sur les anciens enregistrements avant migration 0003
    content_hash: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    notification_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint("plan_id", name="uq_weekly_books_plan_id"),
    )

    # Relations
    plan: Mapped["WeeklyPlan"] = relationship("WeeklyPlan", back_populates="book")
