"""
Schémas Pydantic pour le domaine Household (foyers et membres).

Conventions :
- Les schémas *Create sont utilisés pour les requêtes POST/PATCH (entrée).
- Les schémas *Read sont utilisés pour les réponses (sortie).
- ConfigDict(from_attributes=True) permet de construire depuis des modèles ORM.

Aligné avec les modèles ORM :
- apps/api/src/db/models/household.py
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---- Préférences ----

class MemberPreferenceCreate(BaseModel):
    """Création ou mise à jour des préférences d'un membre."""

    diet_tags: list[str] = Field(
        default=[],
        description="Régimes alimentaires (ex: ['végétarien', 'sans-gluten']).",
    )
    allergies: list[str] = Field(
        default=[],
        description="Allergènes à éviter (ex: ['gluten', 'lactose']).",
    )
    dislikes: list[str] = Field(
        default=[],
        description="Ingrédients/cuisines non appréciés.",
    )
    cooking_time_max: int | None = Field(
        default=None,
        ge=5,
        le=480,
        description="Temps de cuisson maximum accepté (en minutes).",
    )
    budget_pref: str | None = Field(
        default=None,
        description="Préférence de budget : 'économique', 'moyen', ou 'premium'.",
        pattern="^(économique|moyen|premium)$",
    )


class MemberPreferenceRead(BaseModel):
    """Lecture des préférences d'un membre."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    diet_tags: list[str]
    allergies: list[str]
    dislikes: list[str]
    cooking_time_max: int | None
    budget_pref: str | None
    created_at: datetime
    updated_at: datetime


# ---- Membres ----

class MemberCreate(BaseModel):
    """Ajout d'un membre au foyer."""

    display_name: str = Field(
        min_length=1,
        max_length=100,
        description="Prénom ou surnom du membre.",
    )
    is_child: bool = Field(
        default=False,
        description="True si le membre est un enfant (influe sur les recommandations).",
    )
    birth_date: datetime | None = Field(
        default=None,
        description="Date de naissance (optionnel, pour personnalisation future).",
    )
    preferences: MemberPreferenceCreate | None = Field(
        default=None,
        description="Préférences alimentaires initiales du membre.",
    )


class MemberRead(BaseModel):
    """Lecture d'un membre du foyer."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    display_name: str
    is_child: bool
    role: str
    birth_date: datetime | None
    created_at: datetime
    preferences: MemberPreferenceRead | None


# ---- Foyer ----

class HouseholdCreate(BaseModel):
    """Création d'un nouveau foyer (onboarding step 1)."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Nom du foyer (ex: 'Famille Dupont', 'Chez Emma et Marc').",
    )
    first_member: MemberCreate = Field(
        description="Premier membre du foyer (le owner).",
    )


class HouseholdRead(BaseModel):
    """Lecture d'un foyer avec ses membres."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    plan: str
    created_at: datetime
    updated_at: datetime
    members: list[MemberRead] = []
