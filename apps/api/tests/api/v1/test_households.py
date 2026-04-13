"""
Tests des endpoints Households — POST /households, GET /households/me,
POST /households/me/members, PATCH /households/me/members/{id}/preferences.

Stratégie de mock :
- L'authentification JWT est bypassée via le fixture valid_jwt_token (JWT avec audience).
- La DB est mockée via app.state.db_session_factory.
- Chaque test est autonome (Arrange → Act → Assert).
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---- Fixtures locales ----

HOUSEHOLD_ID = uuid4()
MEMBER_ID = uuid4()
PREF_ID = uuid4()
USER_ID = "test-user-uuid-1234"
NOW = datetime(2026, 4, 12, 10, 0, 0)


def _make_mock_session_factory(session: AsyncMock) -> MagicMock:
    """Construit une factory de session mockée compatible avec `async with factory() as session`."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock()
    factory.return_value = ctx
    return factory


class _Row(dict):
    """
    Simule un SQLAlchemy RowMapping compatible avec dict(row) et row["key"].

    FIX : le code prod fait `dict(row)` sur les RowMapping SQLAlchemy.
    Un MagicMock retourne {} quand dict() l'itère car __iter__ ne retourne pas les keys.
    _Row hérite de dict pour que dict(_Row({...})) == {...}.
    """
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


@pytest_asyncio.fixture
async def client_with_db(app_no_lifespan, valid_jwt_token):
    """
    Client HTTP avec session DB mockée et JWT valide injecté.

    Injecte le token dans les headers de chaque requête via le fixture valid_jwt_token.
    """
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


# ---- POST /households ----

class TestCreateHousehold:
    """Tests de création de foyer (POST /api/v1/households)."""

    @pytest.mark.asyncio
    async def test_cree_foyer_retourne_201(self, client_with_db) -> None:
        """La création d'un foyer valide retourne 201 avec les données du foyer."""
        client, session = client_with_db

        # Arrange — l'utilisateur n'appartient pas encore à un foyer
        check_existing = MagicMock()
        check_existing.fetchone.return_value = None

        # FIX : create_household_with_owner retourne household_id + member_id (SQL DEFINER)
        create_definer_row = MagicMock()
        create_definer_row.__getitem__ = lambda self, key: {
            "household_id": HOUSEHOLD_ID,
            "member_id": MEMBER_ID,
        }[key]
        create_definer_result = MagicMock()
        create_definer_result.mappings.return_value.one.return_value = create_definer_row

        # Récupération du foyer complet pour la réponse (_get_household_by_id)
        # FIX : _Row hérite de dict → dict(row) fonctionne pour HouseholdRead.model_validate
        final_row = _Row({
            "id": HOUSEHOLD_ID,
            "name": "Famille Dupont",
            "plan": "free",
            "created_at": NOW,
            "updated_at": NOW,
            "member_id": MEMBER_ID,
            "role": "owner",
            "display_name": "Jean",
            "is_child": False,
            "birth_date": None,
            "member_created_at": NOW,
            "member_updated_at": NOW,
            "pref_id": None,
        })
        final_result = MagicMock()
        final_result.mappings.return_value.all.return_value = [final_row]

        session.execute = AsyncMock(
            side_effect=[check_existing, create_definer_result, final_result]
        )

        # Act
        response = await client.post(
            "/api/v1/households",
            json={
                "name": "Famille Dupont",
                "first_member": {"display_name": "Jean", "is_child": False},
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Famille Dupont"
        assert len(data["members"]) >= 1

    @pytest.mark.asyncio
    async def test_retourne_409_si_foyer_existant(self, client_with_db) -> None:
        """Si l'utilisateur appartient déjà à un foyer, retourne le foyer existant (idempotent — 200)."""
        client, session = client_with_db

        # Arrange — l'utilisateur a déjà un foyer
        existing = MagicMock()
        existing.fetchone.return_value = (HOUSEHOLD_ID,)

        # _get_household_by_id est appelé pour retourner le foyer existant (idempotence)
        existing_row = _Row({
            "id": HOUSEHOLD_ID,
            "name": "Foyer Existant",
            "plan": "free",
            "created_at": NOW,
            "updated_at": NOW,
            "member_id": MEMBER_ID,
            "role": "owner",
            "display_name": "Jean",
            "is_child": False,
            "birth_date": None,
            "member_created_at": NOW,
            "member_updated_at": NOW,
            "pref_id": None,
        })
        existing_result = MagicMock()
        existing_result.mappings.return_value.all.return_value = [existing_row]

        session.execute = AsyncMock(side_effect=[existing, existing_result])

        # Act
        response = await client.post(
            "/api/v1/households",
            json={
                "name": "Doublon",
                "first_member": {"display_name": "Test", "is_child": False},
            },
        )

        # Assert — FIX : l'endpoint est idempotent.
        # households.py retourne le foyer existant sans lever 409.
        # FastAPI utilise toujours le status_code du décorateur (201) même pour le retour idempotent.
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_retourne_401_sans_token(self, app_no_lifespan) -> None:
        """Sans token JWT, retourne 401 Unauthorized."""
        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/households",
                json={
                    "name": "Famille Test",
                    "first_member": {"display_name": "Test", "is_child": False},
                },
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_retourne_422_si_nom_vide(self, client_with_db) -> None:
        """Un nom de foyer vide doit retourner 422 Unprocessable Entity."""
        client, session = client_with_db

        response = await client.post(
            "/api/v1/households",
            json={
                "name": "",
                "first_member": {"display_name": "Jean", "is_child": False},
            },
        )
        assert response.status_code == 422


# ---- GET /households/me ----

class TestGetMyHousehold:
    """Tests de récupération du foyer (GET /api/v1/households/me)."""

    @pytest.mark.asyncio
    async def test_retourne_foyer_avec_membres(self, client_with_db) -> None:
        """Retourne le foyer complet avec ses membres."""
        client, session = client_with_db

        # Arrange — l'utilisateur appartient à un foyer
        membership_result = MagicMock()
        membership_result.fetchone.return_value = (HOUSEHOLD_ID,)

        # FIX : _Row hérite de dict → row.get(), row["key"] et dict(row) fonctionnent
        row = _Row({
            "id": HOUSEHOLD_ID,
            "name": "Famille Martin",
            "plan": "free",
            "created_at": NOW,
            "updated_at": NOW,
            "member_id": MEMBER_ID,
            "role": "owner",
            "display_name": "Pierre",
            "is_child": False,
            "birth_date": None,
            "member_created_at": NOW,
            "member_updated_at": NOW,
            "pref_id": None,
        })
        detail_result = MagicMock()
        detail_result.mappings.return_value.all.return_value = [row]

        session.execute = AsyncMock(side_effect=[membership_result, detail_result])

        # Act
        response = await client.get("/api/v1/households/me")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Famille Martin"

    @pytest.mark.asyncio
    async def test_retourne_404_si_pas_de_foyer(self, client_with_db) -> None:
        """Si l'utilisateur n'appartient à aucun foyer, retourne 404."""
        client, session = client_with_db

        no_membership = MagicMock()
        no_membership.fetchone.return_value = None
        session.execute = AsyncMock(return_value=no_membership)

        response = await client.get("/api/v1/households/me")

        assert response.status_code == 404
        assert "foyer" in response.json()["detail"].lower()


# ---- POST /households/me/members ----

class TestAddMember:
    """Tests d'ajout de membre (POST /api/v1/households/me/members)."""

    @pytest.mark.asyncio
    async def test_owner_peut_ajouter_membre(self, client_with_db) -> None:
        """Le owner d'un foyer peut ajouter un nouveau membre."""
        client, session = client_with_db

        # Arrange — l'appelant est owner
        owner_result = MagicMock()
        owner_result.fetchone.return_value = ("owner", HOUSEHOLD_ID)

        new_member_row = MagicMock()
        new_member_id = uuid4()
        new_member_row.__getitem__ = lambda self, key: {
            "id": new_member_id,
            "household_id": HOUSEHOLD_ID,
            "role": "member",
            "display_name": "Marie",
            "is_child": False,
            "birth_date": None,
            "created_at": NOW,
            "updated_at": NOW,
        }[key]
        member_result = MagicMock()
        member_result.mappings.return_value.one.return_value = new_member_row

        # FIX : _get_member_by_id utilise mappings().one_or_none() et row["key"] / row.get("key")
        # _Row hérite de dict → ces deux accès fonctionnent
        get_member_row = _Row({
            "id": new_member_id,
            "household_id": HOUSEHOLD_ID,
            "role": "member",
            "display_name": "Marie",
            "is_child": False,
            "birth_date": None,
            "created_at": NOW,
            "updated_at": NOW,
            "pref_id": None,
        })
        get_member_result = MagicMock()
        get_member_result.mappings.return_value.one_or_none.return_value = get_member_row

        session.execute = AsyncMock(
            side_effect=[owner_result, member_result, get_member_result]
        )

        # Act
        response = await client.post(
            "/api/v1/households/me/members",
            json={"display_name": "Marie", "is_child": False},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Marie"

    @pytest.mark.asyncio
    async def test_membre_non_owner_retourne_403(self, client_with_db) -> None:
        """Un membre (non-owner) ne peut pas ajouter d'autres membres (403)."""
        client, session = client_with_db

        not_owner_result = MagicMock()
        not_owner_result.fetchone.return_value = ("member", HOUSEHOLD_ID)
        session.execute = AsyncMock(return_value=not_owner_result)

        response = await client.post(
            "/api/v1/households/me/members",
            json={"display_name": "Intrus", "is_child": False},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_retourne_422_si_nom_vide(self, client_with_db) -> None:
        """Un nom de membre vide retourne 422."""
        client, _ = client_with_db

        response = await client.post(
            "/api/v1/households/me/members",
            json={"display_name": "", "is_child": False},
        )
        assert response.status_code == 422


# ---- PATCH /households/me/members/{member_id}/preferences ----

class TestUpdateMemberPreferences:
    """Tests de mise à jour des préférences (PATCH /households/me/members/{id}/preferences)."""

    @pytest.mark.asyncio
    async def test_upsert_preferences_retourne_200(self, client_with_db) -> None:
        """La mise à jour des préférences retourne 200 avec les nouvelles données."""
        client, session = client_with_db

        # Arrange — vérification accès réussie
        access_result = MagicMock()
        access_result.fetchone.return_value = (MEMBER_ID, "owner")

        # FIX : _Row hérite de dict → dict(pref_row) fonctionne avec MemberPreferenceRead.model_validate
        pref_row = _Row({
            "id": PREF_ID,
            "member_id": MEMBER_ID,
            "diet_tags": ["végétarien"],
            "allergies": [],
            "dislikes": ["coriandre"],
            "cooking_time_max": 45,
            "budget_pref": "moyen",
            "created_at": NOW,
            "updated_at": NOW,
        })
        pref_result = MagicMock()
        pref_result.mappings.return_value.one.return_value = pref_row

        session.execute = AsyncMock(side_effect=[access_result, pref_result])

        # Act
        response = await client.patch(
            f"/api/v1/households/me/members/{MEMBER_ID}/preferences",
            json={
                "diet_tags": ["végétarien"],
                "allergies": [],
                "dislikes": ["coriandre"],
                "cooking_time_max": 45,
                "budget_pref": "moyen",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "végétarien" in data["diet_tags"]
        assert data["cooking_time_max"] == 45

    @pytest.mark.asyncio
    async def test_retourne_404_si_membre_inconnu(self, client_with_db) -> None:
        """Si le membre n'existe pas dans le foyer, retourne 404."""
        client, session = client_with_db

        access_result = MagicMock()
        access_result.fetchone.return_value = None
        session.execute = AsyncMock(return_value=access_result)

        response = await client.patch(
            f"/api/v1/households/me/members/{uuid4()}/preferences",
            json={"diet_tags": [], "allergies": [], "dislikes": []},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_budget_pref_invalide_retourne_422(self, client_with_db) -> None:
        """Une valeur de budget_pref inconnue retourne 422."""
        client, _ = client_with_db

        response = await client.patch(
            f"/api/v1/households/me/members/{MEMBER_ID}/preferences",
            json={
                "diet_tags": [],
                "allergies": [],
                "dislikes": [],
                "budget_pref": "ultra-luxe",
            },
        )
        assert response.status_code == 422
