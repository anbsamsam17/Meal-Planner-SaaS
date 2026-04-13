"""
PlanSelector — sélection des 5-7 recettes finales du plan hebdomadaire.

Ce module sélectionne les meilleures recettes parmi les candidates
en appliquant des critères de diversité et d'équilibre.

Stratégie v0 (heuristique pure, sans LLM) :
1. Diversité culinaire : pas plus de 2 recettes de même cuisine
2. Variété des temps de préparation (équilibre rapide/élaboré)
3. Score composite : similarité goût + quality_score + fraîcheur
4. Fallback LLM : si l'heuristique ne trouve pas num_dinners recettes,
   appel Claude pour compléter (coût justifié car cas rare)

Performance : O(n) sur les candidats, pas de LLM en chemin nominale.
"""

from dataclasses import dataclass
from typing import Any

from loguru import logger

# Poids du score composite (configurables)
WEIGHT_SIMILARITY = 0.5     # Proximité avec le vecteur de goût
WEIGHT_QUALITY = 0.3        # Score de qualité LLM de la recette
WEIGHT_DIFFICULTY_BONUS = 0.1  # Bonus recettes "facile" si enfants
WEIGHT_VARIETY = 0.1        # Bonus diversité cuisine

# Limite de recettes par type de cuisine
MAX_SAME_CUISINE = 2

# Buckets de temps de préparation (minutes)
TIME_BUCKET_RAPIDE = 30     # <= 30 min
TIME_BUCKET_MOYEN = 60      # 31-60 min
TIME_BUCKET_LONG = 9999     # > 60 min


@dataclass
class ScoredRecipe:
    """Recette avec son score composite pour la sélection."""

    recipe_id: str
    title: str
    cuisine_type: str | None
    total_time_min: int | None
    difficulty: int | None
    quality_score: float
    distance: float  # Distance cosine pgvector (plus faible = plus proche)
    tags: list[str]
    servings: int | None
    photo_url: str | None
    composite_score: float = 0.0


def score_candidates(
    candidates: list[dict[str, Any]],
    has_children: bool = False,
) -> list[ScoredRecipe]:
    """
    Calcule le score composite pour chaque recette candidate.

    Args:
        candidates: Recettes candidates depuis RecipeRetriever.
        has_children: True si le foyer comporte des enfants.

    Returns:
        Liste de ScoredRecipe triée par score descendant.
    """
    scored: list[ScoredRecipe] = []

    for candidate in candidates:
        quality = float(candidate.get("quality_score", 0.0) or 0.0)
        distance = float(candidate.get("distance", 1.0) or 1.0)

        # Similarity score : 1 - distance normalisée (distance cosine [0,2] → [1,0])
        similarity = max(0.0, 1.0 - distance / 2.0)

        # Bonus difficulté pour les foyers avec enfants
        difficulty_bonus = 0.0
        if has_children:
            difficulty = candidate.get("difficulty")
            if difficulty in (1, 2):  # very_easy, easy
                difficulty_bonus = 1.0
            elif difficulty == 3:  # medium
                difficulty_bonus = 0.5

        # Score composite
        composite = (
            WEIGHT_SIMILARITY * similarity
            + WEIGHT_QUALITY * quality
            + WEIGHT_DIFFICULTY_BONUS * difficulty_bonus
        )

        scored.append(
            ScoredRecipe(
                recipe_id=str(candidate.get("id", "")),
                title=str(candidate.get("title", "")),
                cuisine_type=candidate.get("cuisine_type"),
                total_time_min=candidate.get("total_time_min"),
                difficulty=candidate.get("difficulty"),
                quality_score=quality,
                distance=distance,
                tags=list(candidate.get("tags") or []),
                servings=candidate.get("servings"),
                photo_url=candidate.get("photo_url"),
                composite_score=composite,
            )
        )

    # Tri par score descendant
    scored.sort(key=lambda r: r.composite_score, reverse=True)
    return scored


def _get_time_bucket(total_time_min: int | None) -> str:
    """
    Classe une recette dans un bucket de temps de préparation.

    Args:
        total_time_min: Temps total en minutes.

    Returns:
        Identifiant du bucket ('rapide', 'moyen', 'long').
    """
    if total_time_min is None:
        return "moyen"
    if total_time_min <= TIME_BUCKET_RAPIDE:
        return "rapide"
    if total_time_min <= TIME_BUCKET_MOYEN:
        return "moyen"
    return "long"


def select_diverse_plan(
    scored_candidates: list[ScoredRecipe],
    num_dinners: int = 5,
    has_children: bool = False,
) -> list[ScoredRecipe]:
    """
    Sélectionne num_dinners recettes en appliquant les critères de diversité.

    Algorithme :
    1. Itère les candidats par score décroissant
    2. Vérifie les contraintes de diversité cuisine
    3. Essaie de couvrir les 3 buckets de temps (rapide/moyen/long)
    4. Arrête quand num_dinners recettes sont sélectionnées

    Args:
        scored_candidates: Candidats triés par score.
        num_dinners: Nombre de dîners à sélectionner.
        has_children: Si le foyer a des enfants (module difficulté).

    Returns:
        Liste des recettes sélectionnées.
    """
    selected: list[ScoredRecipe] = []
    cuisine_count: dict[str, int] = {}
    time_bucket_count: dict[str, int] = {"rapide": 0, "moyen": 0, "long": 0}

    for candidate in scored_candidates:
        if len(selected) >= num_dinners:
            break

        cuisine = (candidate.cuisine_type or "autre").lower()
        time_bucket = _get_time_bucket(candidate.total_time_min)

        # Contrainte diversité cuisine
        if cuisine_count.get(cuisine, 0) >= MAX_SAME_CUISINE:
            logger.debug(
                "plan_selector_cuisine_limit_skip",
                title=candidate.title[:40],
                cuisine=cuisine,
            )
            continue

        # Bonus diversité temps si on manque d'un bucket
        # (n'exclut pas, mais oriente la sélection)
        # Cette logique est heuristique : on accepte quand même si déséquilibré

        selected.append(candidate)
        cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1
        time_bucket_count[time_bucket] = time_bucket_count.get(time_bucket, 0) + 1

        logger.debug(
            "plan_selector_selected",
            title=candidate.title[:40],
            cuisine=cuisine,
            score=round(candidate.composite_score, 3),
            time_bucket=time_bucket,
        )

    # Si on n'a pas assez de recettes avec les contraintes diversité,
    # on relâche la contrainte cuisine pour compléter
    if len(selected) < num_dinners:
        logger.warning(
            "plan_selector_diversity_fallback",
            selected_count=len(selected),
            needed=num_dinners,
        )
        for candidate in scored_candidates:
            if len(selected) >= num_dinners:
                break
            if candidate not in selected:
                selected.append(candidate)

    logger.info(
        "plan_selector_result",
        selected_count=len(selected),
        num_dinners=num_dinners,
        cuisine_distribution=cuisine_count,
        time_distribution=time_bucket_count,
    )

    return selected[:num_dinners]
