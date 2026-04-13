"""
Classe abstraite BaseRecipeScraper — interface commune pour tous les scrapers.

Chaque spider (Marmiton, Allrecipes, 750g...) doit hériter de cette classe
et implémenter les méthodes abstraites. L'interface commune permet à l'agent
RECIPE_SCOUT d'orchestrer plusieurs scrapers sans dépendre des implémentations.

Conventions de scraping respectées (ROADMAP #10 + éthique) :
- Respect des robots.txt
- Throttling par défaut (1 req/s)
- User-Agent transparent identifiant Presto
- Pas de bypass de CAPTCHAs ni de mécanismes de protection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawRecipe:
    """
    Structure de données brute d'une recette scrapée.

    Contient les données telles qu'extraites du HTML — avant normalisation.
    Les champs optionnels peuvent être None si non disponibles sur la source.

    Attributes:
        title: Titre de la recette (obligatoire).
        source_url: URL de la page source (obligatoire).
        source_name: Nom de la source (ex: "marmiton", "750g").
        ingredients_raw: Liste brute des lignes d'ingrédients (ex: "200g de farine").
        instructions_raw: Liste des étapes de préparation.
        prep_time_min: Temps de préparation en minutes.
        cook_time_min: Temps de cuisson en minutes.
        servings: Nombre de portions.
        difficulty: Niveau de difficulté (chaîne brute, ex: "Facile").
        photo_url: URL de la photo principale.
        rating: Note moyenne de la recette sur la source.
        cuisine_type: Type de cuisine si indiqué sur la source.
        tags_raw: Tags bruts tels qu'indiqués par la source.
        extra: Métadonnées supplémentaires spécifiques à la source.
    """

    title: str
    source_url: str
    source_name: str
    ingredients_raw: list[str] = field(default_factory=list)
    instructions_raw: list[str] = field(default_factory=list)
    prep_time_min: int | None = None
    cook_time_min: int | None = None
    servings: int | None = None
    difficulty: str | None = None  # Chaîne brute avant normalisation
    photo_url: str | None = None
    rating: float | None = None
    cuisine_type: str | None = None
    tags_raw: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class BaseRecipeScraper(ABC):
    """
    Interface abstraite pour les scrapers de recettes.

    Chaque sous-classe doit implémenter :
    - `scrape_url()` : extrait une recette depuis une URL donnée
    - `get_listing_urls()` : retourne une liste d'URLs à scraper

    La logique de throttling, de retry et de respect des robots.txt
    est implémentée dans les spiders Scrapy (marmiton.py) pour profiter
    du framework natif. Cette classe définit uniquement l'interface.
    """

    # Nom de la source — utilisé pour le champ source_name des RawRecipe
    source_name: str = "unknown"

    # Délai entre les requêtes (secondes) — respecter les robots.txt
    default_delay_seconds: float = 1.0

    # User-Agent transparent identifiant notre bot
    user_agent: str = (
        "PrestoBot/1.0 (+https://presto.fr/bot; "
        "collecte@presto.fr)"
    )

    @abstractmethod
    def scrape_url(self, url: str) -> RawRecipe | None:
        """
        Extrait les données d'une recette depuis une URL.

        Respecte les robots.txt de la source. Retourne None si la page
        est inaccessible, protégée par CAPTCHA ou ne contient pas de recette.

        Args:
            url: URL complète de la page recette.

        Returns:
            RawRecipe avec les données brutes, ou None si échec.
        """
        ...

    @abstractmethod
    def get_listing_urls(self, max_pages: int = 10) -> list[str]:
        """
        Retourne une liste d'URLs de recettes à scraper.

        Navigue les pages de listing de la source pour collecter
        les URLs individuelles des recettes.

        Args:
            max_pages: Nombre maximum de pages de listing à parcourir.

        Returns:
            Liste d'URLs complètes de pages de recettes.
        """
        ...

    def is_valid_raw_recipe(self, recipe: RawRecipe) -> bool:
        """
        Validation minimale de la cohérence d'une RawRecipe.

        Un scraper bien implémenté ne devrait pas retourner de recette invalide,
        mais cette vérification sert de filet de sécurité avant la normalisation.

        Args:
            recipe: Recette brute à valider.

        Returns:
            True si la recette est exploitable, False sinon.
        """
        # Titre non vide (minimum obligatoire)
        if not recipe.title or not recipe.title.strip():
            return False

        # Au moins un ingrédient
        if not recipe.ingredients_raw:
            return False

        # Au moins une instruction
        # FIX : retourner bool explicitement — `return recipe.instructions_raw` retournait
        # la liste elle-même au lieu de True (bug détecté par test_allrecipes_scraper.py)
        if not recipe.instructions_raw:
            return False
        return True
