"""
Tests du ConstraintBuilder — agrégation des contraintes multi-membres.

Cas critiques testés :
- Agrégation UNION pour les régimes et allergies
- Agrégation MINIMUM pour le temps et le budget
- Foyer mixte (adultes + enfants)
- Foyer vide (edge case)

Architecture AAA (Arrange → Act → Assert).
"""

import pytest

from src.agents.weekly_planner.constraint_builder import (
    HouseholdConstraints,
    build_household_constraints,
)


# ---- Fixtures ----

@pytest.fixture
def membre_vegetarien() -> dict:
    """Membre végétarien, cuisine rapide, budget économique."""
    return {
        "member_id": "uuid-1",
        "display_name": "Alice",
        "is_child": False,
        "diet_tags": ["végétarien"],
        "allergies": [],
        "dislikes": ["épinards"],
        "cooking_time_max": 30,
        "budget_pref": "économique",
    }


@pytest.fixture
def membre_allergie_gluten() -> dict:
    """Membre avec allergie au gluten, cuisine plus longue, budget moyen."""
    return {
        "member_id": "uuid-2",
        "display_name": "Bob",
        "is_child": False,
        "diet_tags": [],
        "allergies": ["gluten"],
        "dislikes": ["fromage de chèvre"],
        "cooking_time_max": 60,
        "budget_pref": "moyen",
    }


@pytest.fixture
def enfant_sans_preferences() -> dict:
    """Enfant sans contraintes alimentaires particulières."""
    return {
        "member_id": "uuid-3",
        "display_name": "Charlie",
        "is_child": True,
        "diet_tags": [],
        "allergies": [],
        "dislikes": ["brocoli"],
        "cooking_time_max": None,
        "budget_pref": None,
    }


@pytest.fixture
def membre_vegan_premium() -> dict:
    """Membre vegan avec budget premium et temps limité."""
    return {
        "member_id": "uuid-4",
        "display_name": "Diana",
        "is_child": False,
        "diet_tags": ["vegan"],
        "allergies": ["lactose"],
        "dislikes": [],
        "cooking_time_max": 45,
        "budget_pref": "premium",
    }


# ---- Tests de base ----

class TestBuildHouseholdConstraints:
    """Tests de l'agrégation des contraintes."""

    def test_foyer_vide_retourne_defaults(self) -> None:
        """Un foyer sans membres doit retourner des contraintes par défaut."""
        constraints = build_household_constraints([])
        assert isinstance(constraints, HouseholdConstraints)
        assert constraints.diet_tags == []
        assert constraints.allergies == []

    def test_un_seul_membre(self, membre_vegetarien: dict) -> None:
        """Un seul membre → ses préférences sont les contraintes."""
        constraints = build_household_constraints([membre_vegetarien])
        assert "végétarien" in constraints.diet_tags
        assert constraints.time_max_min == 30
        assert constraints.budget == "économique"

    def test_union_regimes(
        self, membre_vegetarien: dict, membre_vegan_premium: dict
    ) -> None:
        """UNION des régimes : végétarien + vegan → les deux présents."""
        constraints = build_household_constraints(
            [membre_vegetarien, membre_vegan_premium]
        )
        assert "végétarien" in constraints.diet_tags
        assert "vegan" in constraints.diet_tags

    def test_union_allergies(
        self, membre_allergie_gluten: dict, membre_vegan_premium: dict
    ) -> None:
        """UNION des allergies : si un membre est allergique, tous sont protégés."""
        constraints = build_household_constraints(
            [membre_allergie_gluten, membre_vegan_premium]
        )
        assert "gluten" in constraints.allergies
        assert "lactose" in constraints.allergies

    def test_union_dislikes(
        self, membre_vegetarien: dict, membre_allergie_gluten: dict
    ) -> None:
        """UNION des dislikes : éviter ce que n'aime personne."""
        constraints = build_household_constraints(
            [membre_vegetarien, membre_allergie_gluten]
        )
        assert "épinards" in constraints.dislikes
        assert "fromage de chèvre" in constraints.dislikes

    def test_minimum_temps(
        self, membre_vegetarien: dict, membre_allergie_gluten: dict
    ) -> None:
        """MINIMUM temps : respecter le membre le plus contraint (30 < 60)."""
        constraints = build_household_constraints(
            [membre_vegetarien, membre_allergie_gluten]
        )
        assert constraints.time_max_min == 30

    def test_minimum_budget(
        self, membre_vegetarien: dict, membre_vegan_premium: dict
    ) -> None:
        """MINIMUM budget : économique < premium → économique gagne."""
        constraints = build_household_constraints(
            [membre_vegetarien, membre_vegan_premium]
        )
        assert constraints.budget == "économique"

    def test_budget_moyen_par_defaut(
        self, membre_allergie_gluten: dict
    ) -> None:
        """Budget moyen si aucun budget défini."""
        membre = {**membre_allergie_gluten, "budget_pref": None}
        # Un seul membre sans budget → défaut "moyen"
        constraints = build_household_constraints([membre])
        assert constraints.budget == "moyen"


# ---- Tests comptage membres ----

class TestMembreComptage:
    """Tests du comptage adultes/enfants."""

    def test_un_adulte(self, membre_vegetarien: dict) -> None:
        constraints = build_household_constraints([membre_vegetarien])
        assert constraints.adult_count == 1
        assert constraints.child_count == 0
        assert constraints.member_count == 1

    def test_adultes_et_enfants(
        self,
        membre_vegetarien: dict,
        membre_allergie_gluten: dict,
        enfant_sans_preferences: dict,
    ) -> None:
        constraints = build_household_constraints(
            [membre_vegetarien, membre_allergie_gluten, enfant_sans_preferences]
        )
        assert constraints.adult_count == 2
        assert constraints.child_count == 1
        assert constraints.member_count == 3

    def test_enfant_sans_temps_ne_bloque_pas_minimum(
        self,
        membre_vegetarien: dict,
        enfant_sans_preferences: dict,
    ) -> None:
        """Un enfant sans contrainte de temps ne doit pas influencer le minimum."""
        # cooking_time_max=None pour l'enfant → ignoré
        constraints = build_household_constraints(
            [membre_vegetarien, enfant_sans_preferences]
        )
        # Seul membre_vegetarien a cooking_time_max=30
        assert constraints.time_max_min == 30


# ---- Tests excluded_tags ----

class TestExcludedTags:
    """Tests de la génération des tags exclus."""

    def test_allergie_gluten_genere_tag_exclu(
        self, membre_allergie_gluten: dict
    ) -> None:
        """L'allergie gluten doit générer un tag exclus pour filtrer les recettes."""
        constraints = build_household_constraints([membre_allergie_gluten])
        # La méthode to_excluded_tags() doit générer des tags de filtrage
        excluded = constraints.to_excluded_tags()
        assert any("gluten" in tag for tag in excluded)

    def test_sans_allergie_aucun_tag_exclu(
        self, membre_vegetarien: dict
    ) -> None:
        """Sans allergie, la liste des tags exclus doit être vide."""
        constraints = build_household_constraints([membre_vegetarien])
        excluded = constraints.to_excluded_tags()
        assert isinstance(excluded, list)
        # Végétarien n'a pas d'allergie
        assert len(excluded) == 0
