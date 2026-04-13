"""
Tests des endpoints Recipes — GET /recipes/{id}, GET /recipes (search).

Stratégie de mock :
- Les recettes sont publiques (pas d'auth requise pour la lecture).
- DB mockée via app.state.db_session_factory.
- Les tests couvrent : happy path, 404, pagination, filtres.

FIX : recipes.py (search_recipes) utilise un seul SELECT avec COUNT(*) OVER()
(window function) au lieu de deux appels séparés (COUNT + SELECT).
Les mocks doivent retourner les rows avec total_count inclus.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---- Données de test ----

RECIPE_ID = uuid4()
NOW = datetime(2026, 4, 12, 10, 0, 0)


def _make_mock_session_factory(session: AsyncMock) -> MagicMock:
    """Factory de session compatible avec `async with factory() as session`."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock()
    factory.return_value = ctx
    return factory


def _mock_recipe_row(
    recipe_id=None,
    title: str = "Poulet rôti aux herbes",
    cuisine: str = "française",
    total_time: int = 105,
    quality_score: float = 0.85,
    total_count: int = 1,
) -> MagicMock:
    """
    Construit un mock de ligne de recette.

    FIX : search_recipes utilise COUNT(*) OVER() → le champ total_count
    est inclus dans chaque row retourné (window function SQL).
    """
    row = MagicMock()
    data = {
        "id": recipe_id or RECIPE_ID,
        "title": title,
        "slug": "poulet-roti-aux-herbes",
        "source": "marmiton",
        "servings": 4,
        "prep_time_min": 15,
        "cook_time_min": 90,
        "total_time_min": total_time,
        "difficulty": 2,
        "cuisine_type": cuisine,
        "tags": ["poulet", "four", "facile"],
        "quality_score": quality_score,
        # FIX : champ total_count requis par search_recipes (window function)
        "total_count": total_count,
    }
    row.__getitem__ = lambda self, key: data[key]
    row.get = lambda key, default=None: data.get(key, default)
    # __iter__ et keys() pour permettre dict(row) dans les endpoints
    row.keys = lambda: data.keys()
    row.items = lambda: data.items()
    return row


@pytest_asyncio.fixture
async def client_with_db(app_no_lifespan):
    """Client HTTP avec DB mockée (sans authentification — recettes publiques)."""
    session = AsyncMock()
    app_no_lifespan.state.db_session_factory = _make_mock_session_factory(session)

    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan),
        base_url="http://test",
    ) as ac:
        yield ac, session


# ---- GET /recipes/{recipe_id} ----

class TestGetRecipe:
    """Tests de récupération d'une recette par ID."""

    @pytest.mark.asyncio
    async def test_retourne_recette_existante(self, client_with_db) -> None:
        """Retourne 200 avec les métadonnées complètes de la recette."""
        client, session = client_with_db

        recipe_row = _mock_recipe_row()
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = recipe_row
        session.execute = AsyncMock(return_value=result)

        response = await client.get(f"/api/v1/recipes/{RECIPE_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Poulet rôti aux herbes"
        assert data["cuisine_type"] == "française"
        assert data["quality_score"] == 0.85
        assert data["difficulty"] == 2

    @pytest.mark.asyncio
    async def test_retourne_404_si_recette_inexistante(self, client_with_db) -> None:
        """Un UUID inconnu retourne 404 Not Found."""
        client, session = client_with_db

        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        response = await client.get(f"/api/v1/recipes/{uuid4()}")

        assert response.status_code == 404
        assert "introuvable" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retourne_503_sans_db(self, app_no_lifespan) -> None:
        """Sans DB configurée, retourne 503 Service Unavailable."""
        # Pas de db_session_factory dans app.state
        app_no_lifespan.state.db_session_factory = None

        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/api/v1/recipes/{RECIPE_ID}")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_retourne_422_si_uuid_invalide(self, client_with_db) -> None:
        """Un recipe_id non-UUID retourne 422 Unprocessable Entity."""
        client, _ = client_with_db

        response = await client.get("/api/v1/recipes/pas-un-uuid")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_tags_sont_une_liste(self, client_with_db) -> None:
        """Le champ tags est bien retourné sous forme de liste."""
        client, session = client_with_db

        recipe_row = _mock_recipe_row()
        result = MagicMock()
        result.mappings.return_value.one_or_none.return_value = recipe_row
        session.execute = AsyncMock(return_value=result)

        response = await client.get(f"/api/v1/recipes/{RECIPE_ID}")

        assert response.status_code == 200
        assert isinstance(response.json()["tags"], list)
        assert "poulet" in response.json()["tags"]


# ---- GET /recipes (search) ----

class TestSearchRecipes:
    """Tests de la recherche de recettes (GET /api/v1/recipes)."""

    @pytest.mark.asyncio
    async def test_recherche_sans_filtre_retourne_resultats(
        self, client_with_db
    ) -> None:
        """
        Sans filtre, retourne toutes les recettes de qualité >= 0.6.

        FIX : search_recipes fait UN seul SELECT avec COUNT(*) OVER().
        Un seul call session.execute() avec les rows incluant total_count.
        """
        client, session = client_with_db

        # FIX : un seul appel execute() avec COUNT(*) OVER() dans chaque row
        row1 = _mock_recipe_row(title="Poulet rôti", total_count=3)
        row2 = _mock_recipe_row(recipe_id=uuid4(), title="Boeuf bourguignon", total_count=3)
        row3 = _mock_recipe_row(recipe_id=uuid4(), title="Quiche lorraine", total_count=3)
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [row1, row2, row3]

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_recherche_avec_filtre_cuisine(self, client_with_db) -> None:
        """Le filtre cuisine retourne uniquement les recettes du type demandé."""
        client, session = client_with_db

        italiana = _mock_recipe_row(title="Pizza Margherita", cuisine="italienne", total_count=1)
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [italiana]

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes?cuisine=italienne")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["cuisine_type"] == "italienne"

    @pytest.mark.asyncio
    async def test_recherche_avec_max_time(self, client_with_db) -> None:
        """Le filtre max_time retourne uniquement les recettes dans le temps imparti."""
        client, session = client_with_db

        rapide = _mock_recipe_row(title="Omelette rapide", total_time=15, total_count=1)
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [rapide]

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes?max_time=20")

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["total_time_min"] == 15

    @pytest.mark.asyncio
    async def test_recherche_par_mot_cle(self, client_with_db) -> None:
        """La recherche par mot-clé filtre sur le titre."""
        client, session = client_with_db

        poulet_row = _mock_recipe_row(title="Poulet tikka masala", total_count=1)
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = [poulet_row]

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes?q=poulet")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "poulet"
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_pagination_retourne_bonne_page(self, client_with_db) -> None:
        """La pagination retourne la page correcte avec per_page résultats."""
        client, session = client_with_db

        # 50 résultats au total — page 2 avec per_page=10 → éléments 11-20
        rows = [
            _mock_recipe_row(recipe_id=uuid4(), title=f"Recette {i}", total_count=50)
            for i in range(10)
        ]
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = rows

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes?page=2&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert data["total"] == 50
        assert len(data["results"]) == 10

    @pytest.mark.asyncio
    async def test_retourne_liste_vide_si_aucun_resultat(
        self, client_with_db
    ) -> None:
        """Si aucune recette ne correspond, retourne une liste vide (pas 404)."""
        client, session = client_with_db

        # FIX : rows vide → total = 0 (logique dans search_recipes : `rows[0]["total_count"] if rows else 0`)
        rows_result = MagicMock()
        rows_result.mappings.return_value.all.return_value = []

        session.execute = AsyncMock(return_value=rows_result)

        response = await client.get("/api/v1/recipes?q=recette-qui-nexiste-pas")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_retourne_liste_vide_sans_db(self, app_no_lifespan) -> None:
        """Sans DB configurée, search_recipes retourne une liste vide (non-bloquant)."""
        app_no_lifespan.state.db_session_factory = None

        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/recipes")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_retourne_422_si_per_page_trop_grand(
        self, client_with_db
    ) -> None:
        """per_page > 100 retourne 422 (validation Pydantic Query)."""
        client, _ = client_with_db

        response = await client.get("/api/v1/recipes?per_page=500")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_retourne_422_si_max_time_trop_petit(
        self, client_with_db
    ) -> None:
        """max_time < 5 retourne 422 (validation Pydantic Query)."""
        client, _ = client_with_db

        response = await client.get("/api/v1/recipes?max_time=2")

        assert response.status_code == 422
