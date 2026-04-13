"""
Tests des endpoints Feedbacks — POST /feedbacks, GET /feedbacks/me.

Stratégie de mock :
- Authentification JWT via le fixture valid_jwt_token du conftest principal.
- DB entièrement mockée — aucune Postgres réelle requise.

FIX : feedbacks.py ouvre DEUX sessions distinctes par requête :
  1. _get_member_info() : `async with db_session() as session:` → session 1
  2. L'endpoint lui-même : `async with db_session() as session:` → session 2
La factory mock doit retourner des sessions différentes selon l'appel (ou la même
session avec des side_effects ordonnés pour tous les execute()).

Approche retenue : une seule session mockée mais la factory est configurée pour
la retourner à chaque appel. Les execute() sont ordonnés avec side_effect.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---- Données de test ----

HOUSEHOLD_ID = uuid4()
MEMBER_ID = uuid4()
RECIPE_ID = uuid4()
FEEDBACK_ID = uuid4()
NOW = datetime(2026, 4, 12, 10, 0, 0)


class _Row(dict):
    """
    Simule un SQLAlchemy RowMapping compatible avec dict(row), row["key"] et row.get("key").

    FIX : le code prod fait `FeedbackRead.model_validate(dict(row))`.
    Un MagicMock retourne {} car __iter__ ne parcourt pas les keys.
    _Row hérite de dict donc dict(_Row({...})) == {...}.
    """
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def _make_mock_session_factory(session: AsyncMock) -> MagicMock:
    """
    Factory de session compatible avec `async with factory() as session`.

    FIX : feedbacks.py appelle factory() plusieurs fois (une par bloc async with).
    La factory retourne le même context manager pointant vers la même session mockée.
    Chaque appel yield la même session → les side_effects execute() sont partagés.
    """
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock()
    factory.return_value = ctx
    return factory


@pytest_asyncio.fixture
async def client_with_db(app_no_lifespan, valid_jwt_token):
    """Client avec DB mockée et JWT injecté dans les headers."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    app_no_lifespan.state.db_session_factory = _make_mock_session_factory(session)

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan),
        base_url="http://test",
        headers={"Authorization": f"Bearer {valid_jwt_token}"},
    ) as ac:
        yield ac, session


def _mock_feedback_row() -> "_Row":
    """
    Construit un mock de ligne de feedback compatible avec dict(row).

    FIX : FeedbackRead.model_validate(dict(feedback_row)) nécessite que
    dict(row) retourne les bonnes clés. _Row hérite de dict.
    """
    return _Row({
        "id": FEEDBACK_ID,
        "household_id": HOUSEHOLD_ID,
        "member_id": MEMBER_ID,
        "recipe_id": RECIPE_ID,
        "feedback_type": "cooked",
        "rating": 4,
        "notes": "Très bon !",
        "created_at": NOW,
    })


# ---- POST /feedbacks ----

class TestSubmitFeedback:
    """Tests de soumission d'un feedback (POST /api/v1/feedbacks)."""

    @pytest.mark.asyncio
    async def test_feedback_cooked_retourne_201(self, client_with_db) -> None:
        """Un feedback 'cooked' valide retourne 201 avec les données du feedback."""
        client, session = client_with_db

        # FIX : feedbacks.py ouvre 2 sessions. Ordre des execute() sur la session partagée :
        # Session 1 (_get_member_info) : SELECT member_id, household_id → fetchone()
        # Session 2 (submit_feedback) : SELECT recette → fetchone()
        # Session 2 (submit_feedback) : INSERT feedback → mappings().one()

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        recipe_check = MagicMock()
        recipe_check.fetchone.return_value = (RECIPE_ID,)

        feedback_row = _mock_feedback_row()
        insert_result = MagicMock()
        insert_result.mappings.return_value.one.return_value = feedback_row

        session.execute = AsyncMock(
            side_effect=[member_result, recipe_check, insert_result]
        )

        # Act
        response = await client.post(
            "/api/v1/feedbacks",
            json={
                "recipe_id": str(RECIPE_ID),
                "feedback_type": "cooked",
                "rating": 4,
                "notes": "Très bon !",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["feedback_type"] == "cooked"
        assert data["rating"] == 4
        assert data["notes"] == "Très bon !"

    @pytest.mark.asyncio
    async def test_feedback_skipped_sans_note_retourne_201(self, client_with_db) -> None:
        """Un feedback 'skipped' sans rating est valide (rating optionnel)."""
        client, session = client_with_db

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        recipe_check = MagicMock()
        recipe_check.fetchone.return_value = (RECIPE_ID,)

        skipped_row = _Row({
            "id": FEEDBACK_ID,
            "household_id": HOUSEHOLD_ID,
            "member_id": MEMBER_ID,
            "recipe_id": RECIPE_ID,
            "feedback_type": "skipped",
            "rating": None,
            "notes": None,
            "created_at": NOW,
        })
        insert_result = MagicMock()
        insert_result.mappings.return_value.one.return_value = skipped_row

        session.execute = AsyncMock(
            side_effect=[member_result, recipe_check, insert_result]
        )

        response = await client.post(
            "/api/v1/feedbacks",
            json={"recipe_id": str(RECIPE_ID), "feedback_type": "skipped"},
        )

        assert response.status_code == 201
        assert response.json()["rating"] is None

    @pytest.mark.asyncio
    async def test_retourne_404_si_recette_inexistante(self, client_with_db) -> None:
        """Si la recette n'existe pas en base, retourne 404."""
        client, session = client_with_db

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        recipe_not_found = MagicMock()
        recipe_not_found.fetchone.return_value = None

        session.execute = AsyncMock(side_effect=[member_result, recipe_not_found])

        response = await client.post(
            "/api/v1/feedbacks",
            json={
                "recipe_id": str(uuid4()),
                "feedback_type": "cooked",
                "rating": 3,
            },
        )

        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retourne_404_si_utilisateur_sans_foyer(self, client_with_db) -> None:
        """Si l'utilisateur n'appartient à aucun foyer, retourne 404."""
        client, session = client_with_db

        no_member = MagicMock()
        no_member.fetchone.return_value = None
        session.execute = AsyncMock(return_value=no_member)

        response = await client.post(
            "/api/v1/feedbacks",
            json={
                "recipe_id": str(RECIPE_ID),
                "feedback_type": "favorited",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retourne_422_si_feedback_type_invalide(self, client_with_db) -> None:
        """Un feedback_type non reconnu retourne 422 Unprocessable Entity."""
        client, _ = client_with_db

        response = await client.post(
            "/api/v1/feedbacks",
            json={
                "recipe_id": str(RECIPE_ID),
                "feedback_type": "hated",  # Non autorisé
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_retourne_422_si_rating_hors_plage(self, client_with_db) -> None:
        """Un rating en dehors de [1, 5] retourne 422."""
        client, _ = client_with_db

        response = await client.post(
            "/api/v1/feedbacks",
            json={
                "recipe_id": str(RECIPE_ID),
                "feedback_type": "cooked",
                "rating": 10,  # Max = 5
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_retourne_401_sans_token(self, app_no_lifespan) -> None:
        """Sans JWT, retourne 401 Unauthorized."""
        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/feedbacks",
                json={"recipe_id": str(RECIPE_ID), "feedback_type": "cooked"},
            )
        assert response.status_code == 401


# ---- GET /feedbacks/me ----

class TestGetMyFeedbacks:
    """Tests de l'historique des feedbacks (GET /api/v1/feedbacks/me)."""

    @pytest.mark.asyncio
    async def test_retourne_historique_pagine(self, client_with_db) -> None:
        """Retourne la liste paginée des feedbacks de l'utilisateur."""
        client, session = client_with_db

        # FIX : get_my_feedbacks ouvre 2 sessions. Ordre des execute() :
        # Session 1 (_get_member_info) : SELECT member_id, household_id → fetchone()
        # Session 2 (get_my_feedbacks) : COUNT(*) → scalar()
        # Session 2 (get_my_feedbacks) : SELECT feedbacks → mappings().all()

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        count_result = MagicMock()
        count_result.scalar.return_value = 2

        feedback_row_1 = _mock_feedback_row()
        feedback_row_2 = _Row({
            "id": uuid4(),
            "household_id": HOUSEHOLD_ID,
            "member_id": MEMBER_ID,
            "recipe_id": uuid4(),
            "feedback_type": "favorited",
            "rating": 5,
            "notes": None,
            "created_at": NOW,
        })

        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [feedback_row_1, feedback_row_2]

        session.execute = AsyncMock(
            side_effect=[member_result, count_result, rows_result]
        )

        response = await client.get("/api/v1/feedbacks/me")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["page"] == 1
        assert data["has_next"] is False

    @pytest.mark.asyncio
    async def test_filtre_par_feedback_type(self, client_with_db) -> None:
        """Le paramètre feedback_type filtre correctement les résultats."""
        client, session = client_with_db

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        count_result = MagicMock()
        count_result.scalar.return_value = 1

        cooked_row = _mock_feedback_row()
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [cooked_row]

        session.execute = AsyncMock(
            side_effect=[member_result, count_result, rows_result]
        )

        response = await client.get("/api/v1/feedbacks/me?feedback_type=cooked")

        assert response.status_code == 200
        data = response.json()
        # Tous les résultats retournés sont de type 'cooked'
        assert all(r["feedback_type"] == "cooked" for r in data["results"])

    @pytest.mark.asyncio
    async def test_retourne_422_si_feedback_type_filter_invalide(
        self, client_with_db
    ) -> None:
        """Un filtre feedback_type invalide retourne 422."""
        client, _ = client_with_db

        response = await client.get("/api/v1/feedbacks/me?feedback_type=hate")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, client_with_db) -> None:
        """La page 2 avec per_page=1 retourne has_prev=True et has_next selon le total."""
        client, session = client_with_db

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        count_result = MagicMock()
        count_result.scalar.return_value = 3  # 3 éléments au total, per_page=1 → 3 pages

        feedback_row = _mock_feedback_row()
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [feedback_row]

        session.execute = AsyncMock(
            side_effect=[member_result, count_result, rows_result]
        )

        response = await client.get("/api/v1/feedbacks/me?page=2&per_page=1")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["has_prev"] is True
        assert data["has_next"] is True  # 3 total, page 2 sur 3

    @pytest.mark.asyncio
    async def test_retourne_401_sans_token(self, app_no_lifespan) -> None:
        """Sans JWT, retourne 401 Unauthorized."""
        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/feedbacks/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_historique_vide_retourne_liste_vide(self, client_with_db) -> None:
        """Un utilisateur sans feedback retourne une liste vide (total=0)."""
        client, session = client_with_db

        member_result = MagicMock()
        member_result.fetchone.return_value = (MEMBER_ID, HOUSEHOLD_ID)

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[member_result, count_result, rows_result]
        )

        response = await client.get("/api/v1/feedbacks/me")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []
        assert data["has_next"] is False
        assert data["has_prev"] is False
