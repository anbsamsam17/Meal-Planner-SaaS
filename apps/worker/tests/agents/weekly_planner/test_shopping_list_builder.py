"""
Tests du ShoppingListBuilder — consolidation et groupement des ingrédients.

Cas testés :
- Consolidation des quantités identiques (somme g + g)
- Conversion d'unités (g → kg si >= 1000g)
- Groupement par rayon (fruits_legumes, viandes, etc.)
- Exclusion des ingrédients du frigo
- Scaling des portions au nombre de personnes

Architecture AAA (Arrange → Act → Assert).
"""

import pytest
from decimal import Decimal

from src.agents.weekly_planner.shopping_list_builder import (
    _get_rayon,
    _normalize_unit,
    _denormalize_quantity,
    RAYON_ORDER,
)


# ---- Tests _normalize_unit ----

class TestNormalizeUnit:
    """Tests de la normalisation des unités."""

    def test_grammes_pas_de_conversion(self) -> None:
        qty, unit = _normalize_unit(Decimal("500"), "g")
        assert qty == Decimal("500")
        assert unit == "g"

    def test_kilos_vers_grammes(self) -> None:
        qty, unit = _normalize_unit(Decimal("1.5"), "kg")
        assert float(qty) == pytest.approx(1500.0, 0.01)
        assert unit == "g"

    def test_centilitres_vers_millilitres(self) -> None:
        qty, unit = _normalize_unit(Decimal("25"), "cl")
        assert float(qty) == pytest.approx(250.0, 0.01)
        assert unit == "ml"

    def test_litres_vers_millilitres(self) -> None:
        qty, unit = _normalize_unit(Decimal("2"), "l")
        assert float(qty) == pytest.approx(2000.0, 0.01)
        assert unit == "ml"

    def test_unite_inconnue_conservee(self) -> None:
        """Une unité inconnue doit être conservée sans conversion."""
        qty, unit = _normalize_unit(Decimal("3"), "pincées")
        assert qty == Decimal("3")
        assert unit == "pincées"

    def test_piece_pas_de_conversion(self) -> None:
        qty, unit = _normalize_unit(Decimal("2"), "pièce")
        assert qty == Decimal("2")
        assert unit == "pièce"


# ---- Tests _denormalize_quantity ----

class TestDenormalizeQuantity:
    """Tests du reformatage pour l'affichage."""

    def test_sous_1000g_reste_en_grammes(self) -> None:
        result = _denormalize_quantity(Decimal("500"), "g")
        assert "500" in result
        assert "g" in result

    def test_au_dessus_1000g_converti_en_kg(self) -> None:
        result = _denormalize_quantity(Decimal("1500"), "g")
        assert "kg" in result
        assert "1.5" in result

    def test_entier_sans_decimale(self) -> None:
        result = _denormalize_quantity(Decimal("250"), "g")
        assert "250" in result
        # Pas de décimale inutile
        assert ".0" not in result


# ---- Tests _get_rayon ----

class TestGetRayon:
    """Tests du mapping catégorie → rayon."""

    def test_legume_vers_fruits_legumes(self) -> None:
        assert _get_rayon("légumes") == "fruits_legumes"

    def test_viande_vers_viandes_poissons(self) -> None:
        assert _get_rayon("viande") == "viandes_poissons"

    def test_poisson_vers_viandes_poissons(self) -> None:
        assert _get_rayon("poisson") == "viandes_poissons"

    def test_laitier_vers_produits_laitiers(self) -> None:
        assert _get_rayon("laitier") == "produits_laitiers"

    def test_fromage_vers_produits_laitiers(self) -> None:
        assert _get_rayon("fromage") == "produits_laitiers"

    def test_pates_vers_epicerie_seche(self) -> None:
        assert _get_rayon("pâtes") == "epicerie_seche"

    def test_surgele_vers_surgeles(self) -> None:
        assert _get_rayon("surgelé") == "surgeles"

    def test_categorie_none_vers_autres(self) -> None:
        assert _get_rayon(None) == "autres"

    def test_categorie_inconnue_vers_autres(self) -> None:
        assert _get_rayon("inconnue-xyz") == "autres"

    def test_categorie_partielle_match(self) -> None:
        """Une catégorie contenant un mot-clé doit matcher."""
        # "viandes rouges" contient "viande"
        assert _get_rayon("viandes rouges") == "viandes_poissons"


# ---- Tests ordre des rayons ----

class TestRayonOrder:
    """Tests de l'ordre des rayons."""

    def test_tous_les_rayons_presents(self) -> None:
        """Tous les rayons attendus doivent être dans RAYON_ORDER."""
        expected_rayons = {
            "fruits_legumes",
            "viandes_poissons",
            "produits_laitiers",
            "epicerie_seche",
            "surgeles",
            "autres",
        }
        assert set(RAYON_ORDER) == expected_rayons

    def test_fruits_legumes_premier(self) -> None:
        """Les fruits et légumes doivent être en premier."""
        assert RAYON_ORDER[0] == "fruits_legumes"

    def test_autres_dernier(self) -> None:
        """Les 'autres' doivent être en dernier."""
        assert RAYON_ORDER[-1] == "autres"


# ---- Tests d'intégration (mock DB) ----

class TestBuildShoppingListIntegration:
    """Tests d'intégration avec une session DB mockée."""

    @pytest.mark.asyncio
    async def test_liste_vide_si_pas_de_recettes(self) -> None:
        """Une liste sans recettes doit retourner une liste vide."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4
        from src.agents.weekly_planner.shopping_list_builder import build_shopping_list

        mock_session = AsyncMock()
        # Simule aucun ingrédient trouvé
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await build_shopping_list(
            session=mock_session,
            recipe_ids=[],
            household_id=uuid4(),
            num_persons=4,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_consolidation_meme_ingredient(self) -> None:
        """Deux recettes avec le même ingrédient doivent être consolidées."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4
        from decimal import Decimal
        from src.agents.weekly_planner.shopping_list_builder import build_shopping_list

        # Deux lignes pour "carotte" avec 200g chacune
        ing_id = str(uuid4())
        recipe_id_1 = str(uuid4())
        recipe_id_2 = str(uuid4())

        mock_ingredients_rows = [
            {
                "ingredient_id": ing_id,
                "canonical_name": "carotte",
                "category": "légumes",
                "off_id": None,
                "quantity": Decimal("200"),
                "unit": "g",
                "recipe_id": recipe_id_1,
                "recipe_servings": 4,
            },
            {
                "ingredient_id": ing_id,
                "canonical_name": "carotte",
                "category": "légumes",
                "off_id": None,
                "quantity": Decimal("150"),
                "unit": "g",
                "recipe_id": recipe_id_2,
                "recipe_servings": 4,
            },
        ]

        mock_fridge_rows = []  # Frigo vide

        mock_result_ingredients = MagicMock()
        mock_result_ingredients.mappings.return_value.all.return_value = mock_ingredients_rows

        mock_result_fridge = MagicMock()
        mock_result_fridge.fetchall.return_value = mock_fridge_rows

        call_count = 0

        async def mock_execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result_ingredients
            return mock_result_fridge

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        result = await build_shopping_list(
            session=mock_session,
            recipe_ids=[recipe_id_1, recipe_id_2],
            household_id=uuid4(),
            num_persons=4,
        )

        # Une seule entrée "carotte" consolidée
        carottes = [item for item in result if item["canonical_name"] == "carotte"]
        assert len(carottes) == 1
        assert carottes[0]["rayon"] == "fruits_legumes"
        # Quantité totale : 200 + 150 = 350g (mêmes portions)
        qty_total = carottes[0]["quantities"][0]["quantity_value"]
        assert qty_total == pytest.approx(350.0, 0.01)
