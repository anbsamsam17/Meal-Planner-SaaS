"""
Tests des endpoints Plans — POST /plans/generate, GET /plans/{plan_id},
GET /plans/me/current, POST /plans/{plan_id}/validate, PATCH /{plan_id}/meals/{meal_id},
GET /plans/me/{plan_id}/shopping-list.

Stratégie de mock :
- Authentification JWT via valid_jwt_token du conftest principal.
- Base de données entièrement mockée (pas de Postgres requis).
- FIX : plans.py utilise Depends(get_db) qui ouvre une session unique depuis
  db_session_factory. Tous les session.execute() partagent la même session mockée.
- La tâche Celery generate_plan_task est mockée (pas de broker Redis requis).
"""

import json
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---- Données de test partagées ----

HOUSEHOLD_ID = uuid4()
PLAN_ID = uuid4()
MEAL_ID = uuid4()
RECIPE_ID = uuid4()
MEMBER_ID = uuid4()
# FIX : 2026-04-13 est un lundi (isoweekday=1), 2026-04-14 était un mardi
NOW = datetime(2026, 4, 13, 10, 0, 0)
MONDAY = date(2026, 4, 13)


class _Row(dict):
    """
    Simule un SQLAlchemy RowMapping compatible avec dict(row), row["key"] et row.get("key").

    FIX : le code prod fait `dict(row)` sur les RowMapping SQLAlchemy (ex: PlannedMealRead.model_validate).
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

    FIX : plans.py utilise Depends(get_db) qui fait `async with db_session_factory() as session`.
    La factory doit retourner un context manager async qui yielde la session mockée.
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


def _mock_plan_row() -> "_Row":
    """
    Construit un mock de ligne de plan compatible avec dict(row).

    FIX : _Row hérite de dict → dict(plan_row) retourne les données correctes
    pour WeeklyPlanRead.model_validate(dict(updated)) dans validate_plan.
    """
    return _Row({
        "id": PLAN_ID,
        "household_id": HOUSEHOLD_ID,
        "week_start": MONDAY,
        "status": "draft",
        "validated_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    })


def _mock_meal_row() -> "_Row":
    """
    Construit un mock de ligne de repas planifié compatible avec dict(row).

    FIX : _Row hérite de dict → dict(meal_row) retourne les données correctes
    pour PlannedMealRead.model_validate(dict(row)) dans _get_plan_detail.
    """
    return _Row({
        "id": MEAL_ID,
        "plan_id": PLAN_ID,
        "day_of_week": 1,
        "slot": "dinner",
        "recipe_id": RECIPE_ID,
        "servings_adjusted": 4,
        "recipe_title": "Poulet rôti",
        "recipe_cuisine_type": "française",
        "recipe_total_time_min": 105,
        "recipe_difficulty": 2,
        "recipe_photo_url": None,
    })


# ---- POST /plans/generate ----

class TestGeneratePlan:
    """Tests de génération de plan (POST /api/v1/plans/generate)."""

    @pytest.mark.asyncio
    async def test_retourne_202_avec_task_id(self, client_with_db) -> None:
        """La génération d'un plan retourne 202 Accepted avec un task_id."""
        import sys

        client, session = client_with_db

        # FIX : plans.py utilise une session unique (Depends(get_db)).
        # _get_user_household_id exécute 1 query sur la session.
        household_result = MagicMock()
        household_result.fetchone.return_value = (HOUSEHOLD_ID,)
        session.execute = AsyncMock(return_value=household_result)

        # Mock de la tâche Celery via sys.modules (import tardif dans le handler)
        # FIX : le module src.agents.weekly_planner.tasks n'existe pas dans l'API.
        # plans.py fait `from src.agents.weekly_planner.tasks import generate_plan_task`
        # dans un try/except. On injecte le module dans sys.modules pour que l'import réussisse.
        mock_task = MagicMock()
        mock_task.id = "celery-task-uuid-test"

        mock_generate = MagicMock()
        mock_generate.apply_async.return_value = mock_task

        mock_tasks_module = MagicMock()
        mock_tasks_module.generate_plan_task = mock_generate

        # Injecter les modules manquants dans sys.modules
        sys.modules.setdefault("src.agents", MagicMock())
        sys.modules.setdefault("src.agents.weekly_planner", MagicMock())
        sys.modules["src.agents.weekly_planner.tasks"] = mock_tasks_module

        try:
            response = await client.post(
                "/api/v1/plans/generate",
                json={"week_start": "2026-04-13", "num_dinners": 5},
            )
        finally:
            # Nettoyage pour ne pas polluer les autres tests
            sys.modules.pop("src.agents.weekly_planner.tasks", None)

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_retourne_404_si_pas_de_foyer(self, client_with_db) -> None:
        """Sans foyer associé, retourne 404."""
        client, session = client_with_db

        no_household = MagicMock()
        no_household.fetchone.return_value = None
        session.execute = AsyncMock(return_value=no_household)

        response = await client.post(
            "/api/v1/plans/generate",
            json={"week_start": "2026-04-13", "num_dinners": 5},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retourne_422_si_semaine_pas_lundi(self, client_with_db) -> None:
        """week_start doit être un lundi — sinon 422 Unprocessable Entity."""
        client, _ = client_with_db

        # Le 2026-04-15 est un mercredi (ISODOW=3)
        response = await client.post(
            "/api/v1/plans/generate",
            json={"week_start": "2026-04-15", "num_dinners": 5},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_retourne_401_sans_token(self, app_no_lifespan, valid_jwt_token) -> None:
        """
        Sans JWT, retourne 401.

        FIX : plans.py utilise Depends(get_db) qui est évalué en même temps que
        Depends(get_current_user_dep). Avec db_session_factory=None, get_db lève 503
        avant la vérification d'auth, masquant le 401. On configure une DB mockée
        minimale pour que le 401 soit retourné par l'absence de token.
        """
        # Une DB mockée est nécessaire pour que get_db ne lève pas 503 avant l'auth
        session = AsyncMock()
        session.commit = AsyncMock()
        factory_ctx = AsyncMock()
        factory_ctx.__aenter__ = AsyncMock(return_value=session)
        factory_ctx.__aexit__ = AsyncMock(return_value=None)
        factory = MagicMock()
        factory.return_value = factory_ctx
        app_no_lifespan.state.db_session_factory = factory

        async with AsyncClient(
            transport=ASGITransport(app=app_no_lifespan),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/plans/generate",
                json={"week_start": "2026-04-13", "num_dinners": 5},
            )

        # Nettoyage de la db_session_factory après le test
        app_no_lifespan.state.db_session_factory = None
        assert response.status_code == 401


# ---- GET /plans/{plan_id} ----

class TestGetPlan:
    """Tests de récupération d'un plan (GET /api/v1/plans/{plan_id})."""

    @pytest.mark.asyncio
    async def test_retourne_plan_avec_repas(self, client_with_db) -> None:
        """Retourne le plan complet avec ses repas (sans shopping list)."""
        client, session = client_with_db

        # FIX : session unique via Depends(get_db) — tous les execute() sur la même session.
        # Ordre des appels dans get_plan + _get_plan_detail :
        # 1. _get_user_household_id → fetchone()
        # 2. vérification plan (SELECT id, household_id...) → mappings().one_or_none()
        # 3. _get_plan_detail : plan detail → mappings().one_or_none()
        # 4. _get_plan_detail : meals → mappings().all()
        # 5. _get_plan_detail : shopping list → fetchone()
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        plan_row = _mock_plan_row()
        plan_check_res = MagicMock()
        plan_check_res.mappings.return_value.one_or_none.return_value = plan_row

        plan_detail_res = MagicMock()
        plan_detail_res.mappings.return_value.one_or_none.return_value = plan_row

        meal_row = _mock_meal_row()
        meals_res = MagicMock()
        meals_res.mappings.return_value.all.return_value = [meal_row]

        sl_res = MagicMock()
        sl_res.fetchone.return_value = None

        session.execute = AsyncMock(
            side_effect=[household_res, plan_check_res, plan_detail_res, meals_res, sl_res]
        )

        response = await client.get(f"/api/v1/plans/{PLAN_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["meals"]) == 1
        assert data["meals"][0]["recipe_title"] == "Poulet rôti"

    @pytest.mark.asyncio
    async def test_retourne_403_si_plan_autre_foyer(self, client_with_db) -> None:
        """Un plan d'un autre foyer retourne 403 Forbidden."""
        client, session = client_with_db

        my_household = MagicMock()
        my_household.fetchone.return_value = (HOUSEHOLD_ID,)

        other_household_id = uuid4()
        plan_row = _Row({
            "id": PLAN_ID,
            "household_id": other_household_id,
            "week_start": MONDAY,
            "status": "draft",
            "validated_at": None,
            "created_at": NOW,
            "updated_at": NOW,
        })
        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = plan_row

        session.execute = AsyncMock(side_effect=[my_household, plan_check])

        response = await client.get(f"/api/v1/plans/{PLAN_ID}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_retourne_404_si_plan_inexistant(self, client_with_db) -> None:
        """Un plan inexistant retourne 404."""
        client, session = client_with_db

        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[household_res, plan_check])

        response = await client.get(f"/api/v1/plans/{uuid4()}")

        assert response.status_code == 404


# ---- GET /plans/me/current ----

class TestGetCurrentPlan:
    """Tests du plan de la semaine courante (GET /api/v1/plans/me/current)."""

    @pytest.mark.asyncio
    async def test_retourne_none_si_aucun_plan_cette_semaine(self, client_with_db) -> None:
        """Retourne null si aucun plan n'existe pour la semaine en cours."""
        client, session = client_with_db

        # FIX : session unique — 2 queries : household lookup + plan lookup
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        no_plan = MagicMock()
        no_plan.fetchone.return_value = None

        session.execute = AsyncMock(side_effect=[household_res, no_plan])

        response = await client.get("/api/v1/plans/me/current")

        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_retourne_plan_si_existant(self, client_with_db) -> None:
        """Retourne le plan de la semaine courante s'il existe."""
        client, session = client_with_db

        # FIX : session unique — queries dans get_current_plan + _get_plan_detail :
        # 1. _get_user_household_id → fetchone()
        # 2. SELECT id FROM weekly_plans (semaine courante) → fetchone()
        # 3. _get_plan_detail : plan detail → mappings().one_or_none()
        # 4. _get_plan_detail : meals → mappings().all()
        # 5. _get_plan_detail : shopping list → fetchone()
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        current_plan = MagicMock()
        current_plan.fetchone.return_value = (PLAN_ID,)

        plan_row = _mock_plan_row()
        plan_detail = MagicMock()
        plan_detail.mappings.return_value.one_or_none.return_value = plan_row

        meals_res = MagicMock()
        meals_res.mappings.return_value.all.return_value = []

        sl_res = MagicMock()
        sl_res.fetchone.return_value = None

        session.execute = AsyncMock(
            side_effect=[household_res, current_plan, plan_detail, meals_res, sl_res]
        )

        response = await client.get("/api/v1/plans/me/current")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"


# ---- POST /plans/{plan_id}/validate ----

class TestValidatePlan:
    """Tests de validation d'un plan (POST /api/v1/plans/{plan_id}/validate)."""

    @pytest.mark.asyncio
    async def test_valide_plan_draft_retourne_200(self, client_with_db) -> None:
        """La validation d'un plan draft retourne 200 avec status='validated'."""
        client, session = client_with_db

        # FIX : session unique — queries dans validate_plan :
        # 1. _get_user_household_id → fetchone()
        # 2. SELECT plan (vérif ownership + status) → mappings().one_or_none()
        # 3. UPDATE plan → mappings().one_or_none()
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        # FIX : _Row hérite de dict → dict(draft_row) et dict(validated_row) fonctionnent
        draft_row = _Row({
            "id": PLAN_ID,
            "household_id": HOUSEHOLD_ID,
            "status": "draft",
        })
        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = draft_row

        validated_row = _Row({
            "id": PLAN_ID,
            "household_id": HOUSEHOLD_ID,
            "week_start": MONDAY,
            "status": "validated",
            "validated_at": NOW,
            "created_at": NOW,
            "updated_at": NOW,
        })
        update_result = MagicMock()
        update_result.mappings.return_value.one_or_none.return_value = validated_row

        session.execute = AsyncMock(side_effect=[household_res, plan_check, update_result])

        response = await client.post(
            f"/api/v1/plans/{PLAN_ID}/validate",
            json={"confirm": True},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "validated"

    @pytest.mark.asyncio
    async def test_retourne_409_si_plan_deja_valide(self, client_with_db) -> None:
        """Re-valider un plan déjà validé retourne 409 Conflict."""
        client, session = client_with_db

        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        already_validated = _Row({"id": PLAN_ID, "household_id": HOUSEHOLD_ID, "status": "validated"})
        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = already_validated

        session.execute = AsyncMock(side_effect=[household_res, plan_check])

        response = await client.post(
            f"/api/v1/plans/{PLAN_ID}/validate",
            json={"confirm": True},
        )

        assert response.status_code == 409


# ---- PATCH /plans/{plan_id}/meals/{meal_id} ----

class TestSwapMeal:
    """Tests de remplacement de recette (PATCH /plans/{plan_id}/meals/{meal_id})."""

    @pytest.mark.asyncio
    async def test_swap_retourne_repas_mis_a_jour(self, client_with_db) -> None:
        """Le swap retourne le repas mis à jour avec la nouvelle recette."""
        client, session = client_with_db

        new_recipe_id = uuid4()

        # FIX : session unique — queries dans swap_meal :
        # 1. _get_user_household_id → fetchone()
        # 2. SELECT plan (household_id + status) → mappings().one_or_none()
        # 3. UPDATE planned_meals → mappings().one_or_none()
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        # FIX : _Row hérite de dict → dict(plan_row) et dict(updated_meal_row) fonctionnent
        plan_row = _Row({"household_id": HOUSEHOLD_ID, "status": "draft"})
        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = plan_row

        updated_meal_row = _Row({
            "id": MEAL_ID,
            "plan_id": PLAN_ID,
            "day_of_week": 1,
            "slot": "dinner",
            "recipe_id": new_recipe_id,
            "servings_adjusted": 4,
        })
        swap_result = MagicMock()
        swap_result.mappings.return_value.one_or_none.return_value = updated_meal_row

        session.execute = AsyncMock(side_effect=[household_res, plan_check, swap_result])

        response = await client.patch(
            f"/api/v1/plans/{PLAN_ID}/meals/{MEAL_ID}",
            json={"new_recipe_id": str(new_recipe_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recipe_id"] == str(new_recipe_id)

    @pytest.mark.asyncio
    async def test_retourne_409_si_plan_valide(self, client_with_db) -> None:
        """On ne peut pas modifier un plan validé — retourne 409."""
        client, session = client_with_db

        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        validated_plan = _Row({"household_id": HOUSEHOLD_ID, "status": "validated"})
        plan_check = MagicMock()
        plan_check.mappings.return_value.one_or_none.return_value = validated_plan

        session.execute = AsyncMock(side_effect=[household_res, plan_check])

        response = await client.patch(
            f"/api/v1/plans/{PLAN_ID}/meals/{MEAL_ID}",
            json={"new_recipe_id": str(uuid4())},
        )

        assert response.status_code == 409


# ---- GET /plans/me/{plan_id}/shopping-list ----

class TestGetShoppingList:
    """Tests de la liste de courses (GET /plans/me/{plan_id}/shopping-list)."""

    @pytest.mark.asyncio
    async def test_retourne_items_de_courses(self, client_with_db) -> None:
        """Retourne la liste de courses JSONB du plan."""
        client, session = client_with_db

        # FIX : session unique — queries dans get_shopping_list :
        # 1. _get_user_household_id → fetchone()
        # 2. SELECT household_id FROM weekly_plans → fetchone()
        # 3. SELECT items FROM shopping_lists → fetchone()
        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        plan_check = MagicMock()
        plan_check.fetchone.return_value = (HOUSEHOLD_ID,)

        shopping_items = [
            {
                "ingredient_id": str(uuid4()),
                "canonical_name": "poulet",
                "category": "viandes",
                "rayon": "viandes_poissons",
                "off_id": None,
                "quantities": [{"quantity_display": "600", "quantity_value": 600.0, "unit": "g"}],
                "checked": False,
                "in_fridge": False,
            }
        ]
        sl_res = MagicMock()
        sl_res.fetchone.return_value = (json.dumps(shopping_items),)

        session.execute = AsyncMock(side_effect=[household_res, plan_check, sl_res])

        response = await client.get(f"/api/v1/plans/me/{PLAN_ID}/shopping-list")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["canonical_name"] == "poulet"
        assert data[0]["rayon"] == "viandes_poissons"

    @pytest.mark.asyncio
    async def test_retourne_404_si_liste_non_generee(self, client_with_db) -> None:
        """Si la liste de courses n'a pas encore été générée, retourne 404."""
        client, session = client_with_db

        household_res = MagicMock()
        household_res.fetchone.return_value = (HOUSEHOLD_ID,)

        plan_check = MagicMock()
        plan_check.fetchone.return_value = (HOUSEHOLD_ID,)

        no_sl = MagicMock()
        no_sl.fetchone.return_value = None

        session.execute = AsyncMock(side_effect=[household_res, plan_check, no_sl])

        response = await client.get(f"/api/v1/plans/me/{PLAN_ID}/shopping-list")

        assert response.status_code == 404
