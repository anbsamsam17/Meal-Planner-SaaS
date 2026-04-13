"""
Schémas Pydantic communs — réponses partagées entre tous les endpoints.

Ces schémas standardisent les réponses API pour :
- Les listes paginées (PaginatedResponse)
- Les erreurs (ErrorResponse)
- Les tâches asynchrones (TaskResponse)
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    """Réponse paginée générique pour les endpoints de liste."""

    results: list[T]
    total: int = Field(description="Nombre total d'éléments (toutes pages).")
    page: int = Field(ge=1, description="Page courante.")
    per_page: int = Field(ge=1, description="Éléments par page.")
    has_next: bool = Field(description="Existe-t-il une page suivante ?")
    has_prev: bool = Field(description="Existe-t-il une page précédente ?")

    @classmethod
    def build(
        cls,
        results: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        """Construit la réponse paginée avec calcul automatique has_next/has_prev."""
        return cls(
            results=results,
            total=total,
            page=page,
            per_page=per_page,
            has_next=(page * per_page) < total,
            has_prev=page > 1,
        )


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""

    error: str = Field(description="Code d'erreur machine-readable.")
    message: str = Field(description="Message lisible par l'utilisateur.")
    correlation_id: str | None = Field(
        default=None,
        description="ID de corrélation pour le support.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Détails optionnels de l'erreur.",
    )


class TaskResponse(BaseModel):
    """Réponse de déclenchement d'une tâche asynchrone Celery."""

    task_id: str = Field(description="ID de la tâche Celery.")
    status: str = Field(default="pending", description="Statut initial de la tâche.")
    message: str = Field(description="Message de confirmation.")
    poll_url: str | None = Field(
        default=None,
        description="URL de polling pour suivre l'état de la tâche.",
    )
