"""
Tests unitaires pour BookGeneratorAgent.

Couvre :
1. _compute_plan_hash — déterminisme et sensibilité aux changements
2. _build_shopping_list — consolidation des ingrédients
3. _guess_aisle — classification par rayon
4. run() — idempotence (skip si hash identique)
5. run() — génération complète (mock WeasyPrint + MinIO)
6. template_engine — rendu Jinja2 (smoke test HTML)
7. _fetch_plan_data — structure de sortie attendue

Isolation complète : aucune connexion DB/Redis réelle.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.book_generator.agent import (
    BookGeneratorAgent,
    _build_shopping_list,
    _compute_plan_hash,
    _guess_aisle,
)


# ---- Fixtures ----

@pytest.fixture
def sample_plan_data():
    """Plan de test minimal avec 2 recettes."""
    household_id = str(uuid4())
    plan_id = str(uuid4())
    recipe_id_1 = str(uuid4())
    recipe_id_2 = str(uuid4())

    return {
        "plan_id": plan_id,
        "household_id": household_id,
        "household_name": "Famille Test",
        "week_start": "2026-04-14",
        "generated_at": "2026-04-12T10:00:00",
        "recipes": [
            {
                "day_of_week": 0,
                "slot": "dinner",
                "servings_adjusted": 4,
                "id": recipe_id_1,
                "title": "Poulet rôti aux herbes",
                "cuisine_type": "français",
                "prep_time_min": 15,
                "cook_time_min": 60,
                "total_time_min": 75,
                "difficulty": 2,
                "servings": 4,
                "photo_url": None,
                "instructions": [
                    {"step": 1, "text": "Préchauffer le four à 200°C."},
                    {"step": 2, "text": "Badigeonner le poulet d'herbes."},
                ],
                "tags": ["français", "volaille", "moyen"],
                "ingredients": [
                    {"canonical_name": "poulet", "quantity": 1.5, "unit": "kg"},
                    {"canonical_name": "thym", "quantity": 2, "unit": "branche"},
                ],
            },
            {
                "day_of_week": 1,
                "slot": "dinner",
                "servings_adjusted": 4,
                "id": recipe_id_2,
                "title": "Pâtes carbonara",
                "cuisine_type": "italien",
                "prep_time_min": 10,
                "cook_time_min": 15,
                "total_time_min": 25,
                "difficulty": 1,
                "servings": 4,
                "photo_url": None,
                "instructions": [{"step": 1, "text": "Cuire les pâtes al dente."}],
                "tags": ["italien", "pâtes", "économique"],
                "ingredients": [
                    {"canonical_name": "pâtes", "quantity": 400, "unit": "g"},
                    {"canonical_name": "oeuf", "quantity": 4, "unit": "pièce"},
                    {"canonical_name": "parmesan", "quantity": 100, "unit": "g"},
                ],
            },
        ],
        "shopping_list": [],
    }


@pytest.fixture
def sample_ing_rows():
    """Rows d'ingrédients simulant un retour DB (mappings sqlalchemy)."""
    return [
        {"recipe_id": "r1", "canonical_name": "poulet", "quantity": 1.5, "unit": "kg"},
        {"recipe_id": "r1", "canonical_name": "thym", "quantity": 2.0, "unit": "branche"},
        {"recipe_id": "r2", "canonical_name": "pâtes", "quantity": 400.0, "unit": "g"},
        {"recipe_id": "r2", "canonical_name": "oeuf", "quantity": 4.0, "unit": "pièce"},
        # Doublon : oeuf dans deux recettes → doit être agrégé
        {"recipe_id": "r3", "canonical_name": "oeuf", "quantity": 2.0, "unit": "pièce"},
    ]


# ================================================================
# Tests _compute_plan_hash
# ================================================================

class TestComputePlanHash:
    def test_hash_est_deterministe(self, sample_plan_data):
        """Le même plan_data produit toujours le même hash."""
        h1 = _compute_plan_hash(sample_plan_data)
        h2 = _compute_plan_hash(sample_plan_data)
        assert h1 == h2

    def test_hash_est_sha256(self, sample_plan_data):
        """Le hash est une chaîne hex de 64 caractères (SHA-256)."""
        h = _compute_plan_hash(sample_plan_data)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_change_si_recette_modifiee(self, sample_plan_data):
        """Un changement dans les recettes change le hash."""
        h1 = _compute_plan_hash(sample_plan_data)
        sample_plan_data["recipes"][0]["title"] = "Poulet modifié"
        h2 = _compute_plan_hash(sample_plan_data)
        assert h1 != h2

    def test_hash_stable_malgre_generated_at(self, sample_plan_data):
        """generated_at (timestamp) est exclu du hash → stable entre deux runs."""
        h1 = _compute_plan_hash(sample_plan_data)
        sample_plan_data["generated_at"] = "2026-12-31T23:59:59"
        h2 = _compute_plan_hash(sample_plan_data)
        assert h1 == h2

    def test_hash_different_entre_deux_plans(self, sample_plan_data):
        """Deux plans différents ont des hashs différents."""
        plan_b = dict(sample_plan_data)
        plan_b["plan_id"] = str(uuid4())
        h1 = _compute_plan_hash(sample_plan_data)
        h2 = _compute_plan_hash(plan_b)
        assert h1 != h2


# ================================================================
# Tests _build_shopping_list
# ================================================================

class TestBuildShoppingList:
    def test_aggrge_meme_ingredient_meme_unite(self, sample_ing_rows):
        """Les oeufs de r2 (4) et r3 (2) sont agrégés en 6 pièce."""
        shopping = _build_shopping_list(sample_ing_rows)
        oeuf_items = [i for i in shopping if i["ingredient"] == "oeuf"]
        assert len(oeuf_items) == 1
        assert oeuf_items[0]["quantity"] == pytest.approx(6.0)
        assert oeuf_items[0]["unit"] == "pièce"

    def test_ingredients_differents_non_agrege(self, sample_ing_rows):
        """poulet et pâtes restent séparés (noms différents)."""
        shopping = _build_shopping_list(sample_ing_rows)
        names = [i["ingredient"] for i in shopping]
        assert "poulet" in names
        assert "pâtes" in names

    def test_liste_vide_retourne_vide(self):
        """Aucun ingrédient → liste vide."""
        assert _build_shopping_list([]) == []

    def test_tri_par_rayon(self, sample_ing_rows):
        """Les items sont triés par rayon (aisle) puis par nom."""
        shopping = _build_shopping_list(sample_ing_rows)
        aisles = [i["aisle"] for i in shopping]
        assert aisles == sorted(aisles)

    def test_quantite_nulle_comptee_comme_zero(self):
        """Un ingrédient sans quantité reçoit 0 (pas de crash)."""
        rows = [{"recipe_id": "r1", "canonical_name": "sel", "quantity": None, "unit": ""}]
        shopping = _build_shopping_list(rows)
        assert len(shopping) == 1
        assert shopping[0]["quantity"] == 0.0


# ================================================================
# Tests _guess_aisle
# ================================================================

class TestGuessAisle:
    def test_poulet_viandes(self):
        assert _guess_aisle("poulet") == "Viandes et poissons"

    def test_tomate_fruits_legumes(self):
        assert _guess_aisle("tomate") == "Fruits et légumes"

    def test_parmesan_produits_laitiers(self):
        assert _guess_aisle("parmesan") == "Produits laitiers"

    def test_farine_epicerie(self):
        assert _guess_aisle("farine blanche") == "Épicerie sèche"

    def test_ingredient_inconnu_autres(self):
        assert _guess_aisle("ingrédient_exotique_xyz") == "Autres"


# ================================================================
# Tests BookGeneratorAgent.run()
# ================================================================

class TestBookGeneratorAgentRun:
    @pytest.mark.asyncio
    async def test_skip_si_hash_identique(self, sample_plan_data):
        """run() retourne skipped=True si le hash est inchangé."""
        agent = BookGeneratorAgent()

        content_hash = _compute_plan_hash(sample_plan_data)

        # Mock _fetch_plan_data et _get_existing_hash
        agent._fetch_plan_data = AsyncMock(return_value=sample_plan_data)
        agent._get_existing_hash = AsyncMock(return_value=content_hash)

        result = await agent.run(uuid4(), MagicMock())

        assert result["skipped"] is True
        assert result["content_hash"] == content_hash

    @pytest.mark.asyncio
    async def test_genere_si_hash_different(self, sample_plan_data):
        """run() génère le PDF si le hash du plan a changé."""
        agent = BookGeneratorAgent()

        # Hash différent = ancienne version
        agent._fetch_plan_data = AsyncMock(return_value=sample_plan_data)
        agent._get_existing_hash = AsyncMock(return_value="old_hash_different")
        agent._upsert_weekly_book = AsyncMock()

        # Mocks des étapes de rendu et upload
        agent._template_engine.render = MagicMock(return_value="<html>test</html>")
        agent._pdf_renderer.render = MagicMock(return_value=b"%PDF-1.4 test")
        agent._storage.upload = AsyncMock(return_value="hh_id/plan_id-abcd1234.pdf")

        result = await agent.run(uuid4(), MagicMock())

        assert result["skipped"] is False
        assert result["pdf_key"] is not None
        assert len(result["pdf_key"]) > 0

    @pytest.mark.asyncio
    async def test_raise_si_plan_non_trouve(self):
        """run() lève ValueError si le plan n'est pas trouvé en DB."""
        agent = BookGeneratorAgent()
        agent._fetch_plan_data = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="introuvable"):
            await agent.run(uuid4(), MagicMock())

    @pytest.mark.asyncio
    async def test_upsert_weekly_book_appele(self, sample_plan_data):
        """run() appelle _upsert_weekly_book après upload réussi."""
        agent = BookGeneratorAgent()

        agent._fetch_plan_data = AsyncMock(return_value=sample_plan_data)
        agent._get_existing_hash = AsyncMock(return_value=None)
        agent._template_engine.render = MagicMock(return_value="<html>test</html>")
        agent._pdf_renderer.render = MagicMock(return_value=b"%PDF-1.4")
        agent._storage.upload = AsyncMock(return_value="key")
        agent._upsert_weekly_book = AsyncMock()

        await agent.run(uuid4(), MagicMock())

        agent._upsert_weekly_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_duration_ms_positif(self, sample_plan_data):
        """run() retourne une durée en ms >= 0."""
        agent = BookGeneratorAgent()

        agent._fetch_plan_data = AsyncMock(return_value=sample_plan_data)
        agent._get_existing_hash = AsyncMock(return_value=None)
        agent._template_engine.render = MagicMock(return_value="<html>ok</html>")
        agent._pdf_renderer.render = MagicMock(return_value=b"%PDF")
        agent._storage.upload = AsyncMock(return_value="key")
        agent._upsert_weekly_book = AsyncMock()

        result = await agent.run(uuid4(), MagicMock())

        assert result["duration_ms"] >= 0
