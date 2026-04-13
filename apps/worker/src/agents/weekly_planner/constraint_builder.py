"""
ConstraintBuilder — agrégation des contraintes multi-membres d'un foyer.

Ce module collecte les préférences de tous les membres du foyer
et les agrège en un ensemble de contraintes exploitables par le
moteur de sélection de recettes.

Règles d'agrégation :
- Régimes : UNION (si un membre est végétarien, le plan l'est aussi)
- Allergies : UNION stricte (si un membre est allergique, PERSONNE ne mange cet allergène)
- Dislikes : UNION (si un membre n'aime pas, on évite)
- Temps max : MINIMUM (on respecte le membre le plus contraints en temps)
- Budget : MINIMUM sémantique (on respecte le plus restrictif)

Ce système de contraintes "par union/minimum" est conservateur mais préférable
pour la satisfaction family : une seule plainte possible, pas 5.
"""

from dataclasses import dataclass, field

from loguru import logger

# Mapping sémantique des budgets (pour le tri)
BUDGET_ORDRE = {"économique": 0, "moyen": 1, "premium": 2}
# Temps de cuisson par défaut si aucune contrainte membre (en minutes)
DEFAULT_TIME_MAX = 60


@dataclass
class HouseholdConstraints:
    """
    Contraintes agrégées du foyer pour le WEEKLY_PLANNER.

    Ces contraintes sont passées directement au RecipeRetriever
    pour filtrer les recettes candidates.

    Attributes:
        diet_tags: Union des régimes alimentaires (ex: ["vegan", "sans-gluten"]).
        allergies: Union des allergènes à exclure (ex: ["gluten", "lactose"]).
        dislikes: Union des ingrédients/cuisines détestés à éviter.
        time_max_min: Temps de cuisson maximum (minutes) — min des membres.
        budget: Niveau de budget le plus restrictif.
        excluded_tags: Tags à exclure des recettes (dérivé de diet_tags + allergies).
        member_count: Nombre de membres du foyer.
        adult_count: Nombre d'adultes (pour les portions).
        child_count: Nombre d'enfants (pour les portions et la difficulté).
    """

    diet_tags: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    time_max_min: int = DEFAULT_TIME_MAX
    budget: str = "moyen"
    excluded_tags: list[str] = field(default_factory=list)
    member_count: int = 1
    adult_count: int = 1
    child_count: int = 0

    def to_excluded_tags(self) -> list[str]:
        """
        Retourne la liste complète des tags à exclure des recettes.

        Combine les allergies et les régimes pour créer une liste de
        tags que les recettes candidates ne doivent PAS avoir.

        Returns:
            Liste de tags à exclure.
        """
        excluded = set()

        # Tags d'allergie directs (ex: "contient-gluten" si allergie gluten)
        for allergie in self.allergies:
            excluded.add(f"contient-{allergie.lower().replace(' ', '-')}")
            excluded.add(allergie.lower())

        return list(excluded)


def build_household_constraints(members_preferences: list[dict]) -> HouseholdConstraints:
    """
    Agrège les préférences de tous les membres en un seul objet HouseholdConstraints.

    Args:
        members_preferences: Liste de dicts avec les préférences de chaque membre.
            Chaque dict contient :
            - diet_tags: list[str]
            - allergies: list[str]
            - dislikes: list[str]
            - cooking_time_max: int | None
            - budget_pref: str | None
            - is_child: bool

    Returns:
        HouseholdConstraints agrégées.
    """
    if not members_preferences:
        logger.warning("constraint_builder_no_members", using_defaults=True)
        return HouseholdConstraints()

    # ---- Agrégation UNION ----
    all_diet_tags: set[str] = set()
    all_allergies: set[str] = set()
    all_dislikes: set[str] = set()

    # ---- Agrégation MINIMUM ----
    time_max_values: list[int] = []
    budget_values: list[int] = []

    # ---- Comptage membres ----
    adult_count = 0
    child_count = 0

    for prefs in members_preferences:
        # Régimes — UNION
        diet_tags = prefs.get("diet_tags", []) or []
        if isinstance(diet_tags, list):
            all_diet_tags.update(str(t).strip().lower() for t in diet_tags if t)

        # Allergies — UNION (critique : sécurité alimentaire)
        allergies = prefs.get("allergies", []) or []
        if isinstance(allergies, list):
            all_allergies.update(str(a).strip().lower() for a in allergies if a)

        # Dislikes — UNION
        dislikes = prefs.get("dislikes", []) or []
        if isinstance(dislikes, list):
            all_dislikes.update(str(d).strip().lower() for d in dislikes if d)

        # Temps — MINIMUM (on respecte le plus contraint)
        time_max = prefs.get("cooking_time_max")
        if time_max and isinstance(time_max, (int, float)) and time_max > 0:
            time_max_values.append(int(time_max))

        # Budget — MINIMUM sémantique
        budget_pref = prefs.get("budget_pref")
        if budget_pref and budget_pref in BUDGET_ORDRE:
            budget_values.append(BUDGET_ORDRE[budget_pref])

        # Comptage
        if prefs.get("is_child", False):
            child_count += 1
        else:
            adult_count += 1

    # Calcul du temps maximum (MINIMUM des contraintes)
    time_max_min = min(time_max_values) if time_max_values else DEFAULT_TIME_MAX

    # Calcul du budget le plus restrictif
    if budget_values:
        budget_level = min(budget_values)
        budget = {v: k for k, v in BUDGET_ORDRE.items()}[budget_level]
    else:
        budget = "moyen"

    constraints = HouseholdConstraints(
        diet_tags=sorted(all_diet_tags),
        allergies=sorted(all_allergies),
        dislikes=sorted(all_dislikes),
        time_max_min=time_max_min,
        budget=budget,
        member_count=adult_count + child_count,
        adult_count=adult_count,
        child_count=child_count,
    )
    constraints.excluded_tags = constraints.to_excluded_tags()

    logger.info(
        "constraint_builder_result",
        diet_tags=constraints.diet_tags,
        allergies=constraints.allergies,
        time_max_min=constraints.time_max_min,
        budget=constraints.budget,
        member_count=constraints.member_count,
        child_count=constraints.child_count,
    )

    return constraints
