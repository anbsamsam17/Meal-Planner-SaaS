"""
Agent BOOK_GENERATOR — Phase 2 Presto.

Responsable de la génération des livres de recettes hebdomadaires en PDF.
Pipeline : plan validé → Jinja2 HTML → WeasyPrint PDF → MinIO/R2 upload.

Idempotence : hash SHA-256 du contenu du plan — skip si hash identique.
"""
