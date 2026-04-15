"""recipe.py — Modèles ORM pour le catalogue de recettes (domaine global non-tenant).

Tables couvertes :
- recipes            : catalogue global de recettes (public, non isolé par tenant)
- recipe_embeddings  : vecteurs pgvector 384 dims + colonnes dénormalisées pour pré-filtrage HNSW
- ingredients        : référentiel canonique des ingrédients avec mapping Open Food Facts
- recipe_ingredients : association recette <=> ingrédient avec quantité

Note importante :
- Ces tables ne sont PAS isolées par RLS (données publiques, accès SELECT à anon/authenticated).
- Les écritures sont réservées au service_role (pipeline RECIPE_SCOUT via Celery).
- total_time_min est une colonne GENERATED ALWAYS (calculée par PostgreSQL) :
  ne pas inclure dans les INSERT, ne pas mapper en writable côté ORM.

Dépendance externe : pgvector-python (pgvector.sqlalchemy.Vector)

# Phase 1 mature (2026-04-12) :
    Modèle Ingredient enrichi avec colonnes Open Food Facts (migration 0004).
    RecipeEmbedding : vérification que les colonnes dénormalisées sont bien mappées.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    CheckConstraint,
    Computed,
    Float,
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


class Recipe(Base):
    """Recette de cuisine — catalogue global non-tenant.

    quality_score < 0.6 est interdit par le trigger validate_recipe_quality()
    (défini dans 04-triggers-functions.sql). Le trigger donne un message d'erreur
    lisible pour les logs Celery RECIPE_SCOUT.

    total_time_min est GENERATED ALWAYS AS (prep + cook) STORED : SQLAlchemy
    le mappe en lecture seule via Computed(persisted=True).

    Convention difficulty (alignée RECIPE_SCOUT agent.py + API Pydantic Field ge=1, le=5) :
        1 = très facile   (very_easy)
        2 = facile        (easy)
        3 = moyen         (medium)
        4 = difficile     (hard)
        5 = très difficile (very_hard)
    """

    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    prep_time_min: Mapped[int | None] = mapped_column(Integer)
    cook_time_min: Mapped[int | None] = mapped_column(Integer)
    # Colonne GENERATED ALWAYS — lecture seule, calculée par PostgreSQL
    total_time_min: Mapped[int | None] = mapped_column(
        Integer,
        Computed("COALESCE(prep_time_min, 0) + COALESCE(cook_time_min, 0)", persisted=True),
    )
    difficulty: Mapped[int | None] = mapped_column(Integer)
    cuisine_type: Mapped[str | None] = mapped_column(Text)
    # Type de plat : plat_principal, accompagnement, dessert, boisson,
    # entree, petit_dejeuner, pain_viennoiserie, sauce_condiment
    # Ajouté par migration 0009 — nullable car classification progressive via script
    course: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    nutrition: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'{}'")
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="'{}'",
    )
    quality_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        server_default="0.0",
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
        UniqueConstraint("slug", name="uq_recipes_slug"),
        CheckConstraint("servings > 0", name="recipes_servings_check"),
        CheckConstraint("prep_time_min >= 0", name="recipes_prep_time_min_check"),
        CheckConstraint("cook_time_min >= 0", name="recipes_cook_time_min_check"),
        # Convention : 1=très facile, 2=facile, 3=moyen, 4=difficile, 5=très difficile
        # Aligné avec RECIPE_SCOUT (agent.py mapping very_hard→5) et API (Field ge=1, le=5)
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="recipes_difficulty_check"),
        CheckConstraint(
            "quality_score BETWEEN 0.0 AND 1.0",
            name="recipes_quality_score_check",
        ),
    )

    # Relations
    # lazy="selectin" : évite le N+1 lors du chargement de listes de recettes.
    # Pour Recipe.embedding : selectin charge l'embedding en une seule requête IN.
    # Pour Recipe.recipe_ingredients : selectin + order_by position.
    embedding: Mapped["RecipeEmbedding | None"] = relationship(
        "RecipeEmbedding",
        back_populates="recipe",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.position",
        lazy="selectin",
    )


class RecipeEmbedding(Base):
    """Vecteur d'embedding pgvector pour une recette.

    Séparé de Recipe pour ne pas alourdir les requêtes sans similarité.
    Relation 1:1 avec recipes (recipe_id est la PK).

    Colonnes dénormalisées (OPT #1 review 2026-04-12) :
    tags, total_time_min, difficulty, cuisine_type sont copiées depuis recipes
    pour permettre le pré-filtrage AVANT le scan HNSW (latence cible <100ms).
    Ces colonnes sont maintenues en sync par le trigger recipe_embeddings_sync_metadata.

    IMPORTANT :
    - Ne JAMAIS mélanger des embeddings de modèles différents dans cette table.
    - Dimension 384 = all-MiniLM-L6-v2. Migration requise pour changer de modèle.
    """

    __tablename__ = "recipe_embeddings"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Vector(384) : dimension all-MiniLM-L6-v2
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # Colonnes dénormalisées pour pré-filtrage HNSW
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="'{}'",
    )
    total_time_min: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[int | None] = mapped_column(Integer)
    cuisine_type: Mapped[str | None] = mapped_column(Text)

    # Relations
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="embedding")


class Ingredient(Base):
    """Ingrédient canonique normalisé du référentiel Presto.

    canonical_name est en forme canonique : "carotte" (pas "carottes", "Carotte").
    Normalisé en minuscule, singulier, sans accent superflu.

    Colonnes Open Food Facts (Phase 1 mature — migration 0004) :
        off_id               : product_code OFF — NULL tant que le mapping n'est pas effectué.
        off_last_checked_at  : timestamp de la dernière tentative de mapping (pour retry cron).
                               NULL = jamais tenté (priorité maximale dans la queue de mapping).
        off_match_confidence : score de confiance du match (0.0-1.0), calculé par RECIPE_SCOUT.
                               NULL si pas encore mappé. Seuil de rejet recommandé : < 0.5.
        off_product_name     : snapshot du nom du produit OFF retenu, pour affichage drive
                               sans re-requête API OFF.
        off_brand            : marque du produit OFF (optionnel, affiché dans la liste de courses).

    Workflow mapping OFF (RECIPE_SCOUT) :
        1. SELECT ... WHERE off_id IS NULL ORDER BY off_last_checked_at NULLS FIRST LIMIT 50
        2. Appel API OFF (search par canonical_name)
        3. UPDATE ingredients SET off_id=..., off_match_confidence=...,
                                   off_product_name=..., off_last_checked_at=now()
        4. Si match < seuil : UPDATE off_last_checked_at=now() (retry dans 30 jours)

    Phase 4 (panier drive) : CART_BUILDER lit off_id + off_product_name pour construire
    les liens de commande drive directement depuis cette table (JOIN évité).
    """

    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    unit_default: Mapped[str] = mapped_column(Text, nullable=False, server_default="'g'")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # -- Colonnes Open Food Facts (Phase 1 mature — migration 0004) --

    # Identifiant produit OFF — NULL avant mapping, UNIQUE (via index partial) après
    off_id: Mapped[str | None] = mapped_column(Text)

    # Timestamp de dernière tentative — NULL = jamais tenté = priorité queue
    off_last_checked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Score de confiance du match OFF (0.0-1.0)
    # Float correspond au type PostgreSQL FLOAT (8 bytes, double précision)
    off_match_confidence: Mapped[float | None] = mapped_column(Float)

    # Snapshot nom produit OFF pour affichage drive sans re-requête
    off_product_name: Mapped[str | None] = mapped_column(Text)

    # Marque produit OFF (optionnel)
    off_brand: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("canonical_name", name="uq_ingredients_canonical_name"),
        # NOTE : l'unicité de off_id est garantie par un index UNIQUE PARTIAL en DB
        # (ix_ingredients_off_id_partial WHERE off_id IS NOT NULL — migration 0004).
        # On ne l'ajoute pas en UniqueConstraint ORM car l'index partial ne peut pas
        # être exprimé via UniqueConstraint SQLAlchemy standard.
    )

    # Relations
    recipe_associations: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        lazy="selectin",
    )


class RecipeIngredient(Base):
    """Association recette <=> ingrédient avec quantité et position d'affichage.

    Clé primaire composite (recipe_id, ingredient_id).
    position : ordre d'affichage éditorial dans la liste des ingrédients.
    """

    __tablename__ = "recipe_ingredients"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    __table_args__ = (CheckConstraint("quantity > 0", name="recipe_ingredients_quantity_check"),)

    # Relations
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient",
        back_populates="recipe_associations",
    )
