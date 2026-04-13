"""
TemplateEngine — rendu Jinja2 vers HTML pour le livre de recettes.

Charge le template weekly_book.html depuis le répertoire templates/.
Le HTML résultant est passé à PdfRenderer (WeasyPrint).

Pas de chargement de polices Google (incompatible WeasyPrint sans réseau).
CSS inline avec polices système : Georgia, serif.
"""

from __future__ import annotations

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Singleton Jinja2 Environment — chargé une seule fois par worker
_env: Environment | None = None


def _get_env() -> Environment:
    """Retourne l'instance singleton de l'Environment Jinja2."""
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(_TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


class TemplateEngine:
    """
    Moteur de rendu Jinja2 pour le livre de recettes.

    Méthode principale : render(plan_data) → str HTML.
    """

    def render(self, plan_data: dict[str, Any]) -> str:
        """
        Rend le template weekly_book.html avec les données du plan.

        Args:
            plan_data: dict structuré produit par BookGeneratorAgent._fetch_plan_data().

        Returns:
            Chaîne HTML complète prête pour WeasyPrint.

        Raises:
            jinja2.TemplateNotFound: si le fichier HTML template est absent.
        """
        env = _get_env()
        template = env.get_template("weekly_book.html")

        # Calcul des infos supplémentaires pour le template
        context = {
            **plan_data,
            "recipe_count": len(plan_data.get("recipes", [])),
            "difficulty_labels": _DIFFICULTY_LABELS,
            "day_labels": _DAY_LABELS,
        }

        html = template.render(**context)

        logger.debug(
            "template_engine_render_done",
            plan_id=plan_data.get("plan_id"),
            html_length=len(html),
            recipe_count=context["recipe_count"],
        )

        return html


_DIFFICULTY_LABELS: dict[int, str] = {
    1: "Très facile",
    2: "Facile",
    3: "Intermédiaire",
    4: "Difficile",
    5: "Expert",
}

_DAY_LABELS: dict[int, str] = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}
