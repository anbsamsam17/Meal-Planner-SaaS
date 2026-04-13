"""
Tests unitaires du normaliseur d'ingrédients.

Couverture :
- Extraction de quantité et unité (formats variés)
- Mapping vers les noms canoniques
- Catégorisation des ingrédients
- Cas limites (ligne vide, ingrédient inconnu, fractions)

Convention AAA : Arrange → Act → Assert sur chaque test.
"""

import pytest

from src.agents.recipe_scout.normalizer import (
    NormalizedIngredient,
    normalize_ingredient_line,
    normalize_recipe_ingredients,
    _extract_quantity_and_unit,
    _find_canonical_name,
)


class TestExtractQuantityAndUnit:
    """Tests pour l'extraction de quantité et unité."""

    def test_extract_grams(self):
        """
        Extrait correctement une quantité en grammes.

        Arrange : "200g de farine"
        Act : _extract_quantity_and_unit
        Assert : quantity=200, unit="g", nom contient "farine"
        """
        qty, unit, name = _extract_quantity_and_unit("200g de farine")

        assert qty == 200.0
        assert unit == "g"
        assert "farine" in name.lower()

    def test_extract_kilograms(self):
        """
        Extrait une quantité en kilogrammes.

        Arrange : "1,5 kg de boeuf"
        Act : _extract_quantity_and_unit
        Assert : quantity=1.5, unit="kg"
        """
        qty, unit, name = _extract_quantity_and_unit("1,5 kg de boeuf")

        assert qty == 1.5
        assert unit == "kg"

    def test_extract_fraction(self):
        """
        Convertit les fractions en décimales.

        Arrange : "1/2 oignon"
        Act : _extract_quantity_and_unit
        Assert : quantity=0.5
        """
        qty, unit, name = _extract_quantity_and_unit("1/2 oignon")

        assert qty == 0.5

    def test_extract_tablespoon(self):
        """
        Reconnaît les cuillères à soupe (cs).

        Arrange : "3 cuillères à soupe d'huile d'olive"
        Act : _extract_quantity_and_unit
        Assert : unit="cs", quantity=3
        """
        qty, unit, name = _extract_quantity_and_unit("3 cuillères à soupe d'huile d'olive")

        assert qty == 3.0
        assert unit == "cs"

    def test_extract_no_quantity(self):
        """
        Gère les ingrédients sans quantité.

        Arrange : "sel"
        Act : _extract_quantity_and_unit
        Assert : quantity=None
        """
        qty, unit, name = _extract_quantity_and_unit("sel")

        assert qty is None
        assert "sel" in name.lower()

    def test_extract_units(self):
        """
        Reconnaît les unités simples (u = pièce).

        Arrange : "2 oeufs"
        Act : _extract_quantity_and_unit
        Assert : quantity=2
        """
        qty, unit, name = _extract_quantity_and_unit("2 oeufs")

        assert qty == 2.0

    def test_extract_liters(self):
        """
        Reconnaît les volumes en litres et centilitres.

        Arrange : "25 cl de crème liquide"
        Act : _extract_quantity_and_unit
        Assert : unit="cl", quantity=25
        """
        qty, unit, name = _extract_quantity_and_unit("25 cl de crème liquide")

        assert qty == 25.0
        assert unit == "cl"


class TestFindCanonicalName:
    """Tests pour la recherche du nom canonique."""

    def test_canonical_poulet(self):
        """
        Trouve le canonical de 'poulet'.

        Arrange : "poulet"
        Act : _find_canonical_name
        Assert : canonical="poulet", category="viandes_volailles"
        """
        canonical, category = _find_canonical_name("poulet")

        assert canonical == "poulet"
        assert category == "viandes_volailles"

    def test_canonical_ail(self):
        """
        Trouve le canonical de 'ail' (légume).

        Arrange : "ail"
        Act : _find_canonical_name
        Assert : canonical="ail", category="légumes"
        """
        canonical, category = _find_canonical_name("ail")

        assert canonical == "ail"
        assert category == "légumes"

    def test_canonical_unknown_ingredient(self):
        """
        Retourne le texte original pour un ingrédient inconnu.

        Arrange : ingrédient exotique non référencé
        Act : _find_canonical_name
        Assert : canonical=texte original, category="autres"
        """
        canonical, category = _find_canonical_name("cardamome noire")

        assert "cardamome" in canonical.lower()
        assert category == "autres"

    def test_canonical_synonym(self):
        """
        Trouve le canonical via un synonyme.

        Arrange : "lardons" (synonym de lardons)
        Act : _find_canonical_name
        Assert : canonical="lardons", category="charcuterie"
        """
        canonical, category = _find_canonical_name("lardons")

        assert canonical == "lardons"
        assert category == "charcuterie"


class TestNormalizeIngredientLine:
    """Tests pour la normalisation complète d'une ligne d'ingrédient."""

    def test_normalize_complete_line(self):
        """
        Normalise une ligne complète avec quantité, unité et nom.

        Arrange : "200g de farine T55"
        Act : normalize_ingredient_line
        Assert : NormalizedIngredient avec tous les champs corrects
        """
        result = normalize_ingredient_line("200g de farine T55")

        assert isinstance(result, NormalizedIngredient)
        assert result.quantity == 200.0
        assert result.unit == "g"
        assert result.raw_text == "200g de farine T55"

    def test_normalize_empty_line(self):
        """
        Gère les lignes vides sans erreur.

        Arrange : ""
        Act : normalize_ingredient_line
        Assert : NormalizedIngredient avec canonical_name="inconnu"
        """
        result = normalize_ingredient_line("")

        assert isinstance(result, NormalizedIngredient)
        assert result.quantity is None

    def test_normalize_preserves_raw_text(self):
        """
        Le champ raw_text préserve le texte original.

        Essentiel pour l'audit et le debug (traçabilité).

        Arrange : ligne brute quelconque
        Act : normalize_ingredient_line
        Assert : raw_text identique à l'entrée
        """
        raw = "3 cuillères à soupe d'huile d'olive vierge extra"
        result = normalize_ingredient_line(raw)

        assert result.raw_text == raw

    def test_normalize_removes_parenthetical(self):
        """
        Supprime les conseils entre parenthèses.

        Les parenthèses contiennent souvent des conseils de découpe
        qui gênent la normalisation.

        Arrange : "oignon (finement émincé)"
        Act : normalize_ingredient_line
        Assert : canonical_name correspond à "oignon"
        """
        result = normalize_ingredient_line("1 oignon (finement émincé)")

        assert "oignon" in result.canonical_name.lower()


class TestNormalizeRecipeIngredients:
    """Tests pour la normalisation d'une liste complète d'ingrédients."""

    def test_normalize_full_recipe(self, sample_raw_recipe):
        """
        Normalise tous les ingrédients d'une recette complète.

        Arrange : recette avec 6 ingrédients.
        Act : normalize_recipe_ingredients
        Assert : 6 NormalizedIngredient retournés.
        """
        results = normalize_recipe_ingredients(sample_raw_recipe.ingredients_raw)

        assert len(results) == len(sample_raw_recipe.ingredients_raw)
        assert all(isinstance(r, NormalizedIngredient) for r in results)

    def test_normalize_filters_empty_lines(self):
        """
        Ignore les lignes vides dans la liste.

        Arrange : liste avec lignes vides entremêlées.
        Act : normalize_recipe_ingredients
        Assert : seules les lignes non vides sont normalisées.
        """
        lines = ["200g de farine", "", "2 oeufs", "   ", "100g de beurre"]
        results = normalize_recipe_ingredients(lines)

        # Les lignes vides sont filtrées
        assert len(results) == 3

    def test_normalize_all_have_canonical_name(self):
        """
        Toutes les lignes normalisées ont un canonical_name non vide.

        Garantit qu'aucun ingrédient n'est perdu silencieusement.

        Arrange : liste d'ingrédients simples.
        Act : normalize_recipe_ingredients
        Assert : canonical_name non vide sur chaque résultat.
        """
        lines = ["ail", "oignon", "tomate", "sel"]
        results = normalize_recipe_ingredients(lines)

        for result in results:
            assert result.canonical_name, f"canonical_name vide pour : {result.raw_text}"
