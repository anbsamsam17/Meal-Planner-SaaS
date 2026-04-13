"""feedback.py — Modèles ORM pour le domaine Taste Profile / Feedback.

Tables couvertes :
- recipe_feedbacks      : journal des interactions utilisateur avec les recettes
- member_taste_vectors  : vecteurs de goût par membre (réexporté depuis household.py)
- member_preferences    : préférences explicites (réexporté depuis household.py pour commodité)

Architecture des feedbacks :
- Immuables après soumission (pas de policy DELETE authenticated).
- Chaque feedback déclenche une mise à jour asynchrone de member_taste_vectors
  via l'agent TASTE_PROFILE (tâche Celery).
- household_id est dénormalisé dans recipe_feedbacks pour simplifier les policies RLS
  (évite un JOIN weekly_plans → household_members à chaque évaluation de policy).

Voir household.py pour MemberTasteVector (défini là car dépend de HouseholdMember).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

# Réexport pour commodité d'import (évite de chercher dans quel module se trouve MemberTasteVector)
from src.db.models.household import (
    MemberPreference,  # noqa: F401
    MemberTasteVector,  # noqa: F401
)

if TYPE_CHECKING:
    from src.db.models.household import HouseholdMember


class RecipeFeedback(Base):
    """Feedback utilisateur sur une recette.

    Types d'interaction :
    - 'cooked'    : l'utilisateur a cuisiné la recette cette semaine
    - 'skipped'   : l'utilisateur a ignoré la recette proposée
    - 'favorited' : coup de coeur (marque-page)

    rating : NULL si seulement skippé ou favoritisé sans note explicite.

    Politique d'immuabilité :
    - Aucune policy DELETE authenticated (documenté dans 03-rls-policies.sql).
    - Pour RGPD droit à l'oubli : procédure service_role dédiée avec audit_log (Phase 2).
    - Pour "corriger" un feedback : soumettre un nouveau feedback (le dernier gagne
      dans l'agrégation TASTE_PROFILE).
    """

    __tablename__ = "recipe_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # household_id dénormalisé pour la policy RLS (évite un JOIN à chaque évaluation)
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("household_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    # NULL si interaction sans note (skip, favorited)
    rating: Mapped[int | None] = mapped_column(Integer)
    feedback_type: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="recipe_feedbacks_rating_check"),
        CheckConstraint(
            "feedback_type IN ('cooked', 'skipped', 'favorited')",
            name="recipe_feedbacks_feedback_type_check",
        ),
    )

    # Relations (pas de cascade delete côté feedback — immuables)
    member: Mapped["HouseholdMember"] = relationship("HouseholdMember", lazy="select")  # type: ignore[name-defined]


# Import tardif pour éviter la référence circulaire
