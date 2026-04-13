"""
PdfRenderer — conversion HTML → PDF bytes via WeasyPrint.

WeasyPrint est un moteur CSS/HTML → PDF headless (pas de Chrome/Puppeteer).
Requis : `pip install weasyprint` + dépendances système (libpango, libcairo).

Cible performance : < 1.5s p50 pour un PDF de 7 recettes sans images externes.
"""

from __future__ import annotations

import io

from loguru import logger


class PdfRenderer:
    """
    Wrapper WeasyPrint pour la conversion HTML → PDF.

    Instance légère : WeasyPrint charge le HTML à chaque appel.
    Pas de state partagé — thread-safe pour Celery workers.
    """

    def render(self, html_content: str) -> bytes:
        """
        Convertit un document HTML en PDF bytes.

        Utilise WeasyPrint avec un base_url None (pas de ressources externes).
        CSS inline uniquement — pas de fichiers CSS externes pour garantir
        le rendu cohérent en environnement worker sans accès réseau.

        Args:
            html_content: HTML complet avec CSS inline.

        Returns:
            PDF en bytes.

        Raises:
            ImportError: si WeasyPrint n'est pas installé.
            weasyprint.errors.StylesheetParseError: si le CSS est invalide.
        """
        try:
            import weasyprint
        except ImportError as exc:
            raise ImportError(
                "WeasyPrint non installé. "
                "Ajouter 'weasyprint' dans pyproject.toml [project.dependencies]. "
                "Dépendances système requises : libpango-1.0, libcairo2, libgdk-pixbuf2.0."
            ) from exc

        logger.debug(
            "pdf_renderer_start",
            html_length=len(html_content),
        )

        # WeasyPrint accepte directement une chaîne HTML
        # base_url=None : pas de résolution d'URL externes (CSS, images distantes)
        # Les images doivent être en base64 inline ou absentes
        pdf_document = weasyprint.HTML(string=html_content, base_url=None)

        buffer = io.BytesIO()
        pdf_document.write_pdf(buffer)
        pdf_bytes = buffer.getvalue()

        logger.debug(
            "pdf_renderer_done",
            pdf_size_bytes=len(pdf_bytes),
        )

        return pdf_bytes
