"""
Schémas Pydantic pour le domaine Feedback (notations et interactions).

Aligné avec les modèles ORM :
- apps/api/src/db/models/feedback.py
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """Soumission d'un feedback utilisateur sur une recette."""

    recipe_id: UUID = Field(description="UUID de la recette notée.")
    feedback_type: str = Field(
        description="Type d'interaction : 'cooked', 'skipped', ou 'favorited'.",
        pattern="^(cooked|skipped|favorited)$",
    )
    rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Note 1-5 étoiles (optionnelle si feedback_type='skipped').",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Commentaire libre de l'utilisateur.",
    )


class FeedbackRead(BaseModel):
    """Lecture d'un feedback soumis."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    member_id: UUID
    recipe_id: UUID
    feedback_type: str
    rating: int | None
    notes: str | None
    created_at: datetime
