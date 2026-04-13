# Agent BOOK_GENERATOR

Phase 2 Presto — Génération des livres de recettes hebdomadaires en PDF.

## Pipeline

```
plan_id (validé)
  → récupère plan + recettes + ingrédients (DB)
  → calcul SHA-256 content_hash (idempotence)
  → skip si hash identique dans weekly_books
  → Jinja2 → HTML (template weekly_book.html)
  → WeasyPrint → PDF bytes (< 1.5s p50)
  → upload MinIO (dev) / R2 (prod)
  → upsert weekly_books (pdf_r2_key, content_hash, generated_at)
  → log notification (Phase 3 : Resend + Web Push)
```

## Déclencheurs

1. **Temps-réel** : `POST /api/v1/plans/{plan_id}/book/generate` → queue `pdf_high` (priorité 9)
2. **Automatique** : `POST /api/v1/plans/{plan_id}/validate` peut déclencher la génération directement
3. **Batch** : Celery beat dimanche 22h → queue `pdf_low` (filet de sécurité)

## Dépendances système (WeasyPrint)

```bash
# Debian/Ubuntu
apt-get install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0

# macOS
brew install pango cairo

# Python
pip install weasyprint boto3
```

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `STORAGE_BACKEND` | `minio` | `minio` (dev) ou `r2` (prod) |
| `MINIO_ENDPOINT` | `http://localhost:9000` | URL MinIO local |
| `MINIO_ACCESS_KEY` | `minioadmin` | Clé MinIO |
| `MINIO_SECRET_KEY` | `minioadmin` | Secret MinIO |
| `MINIO_BUCKET` | `mealplanner-pdfs` | Bucket PDF |

## Test manuel

```bash
# Déclencher la génération d'un plan
curl -X POST http://localhost:8001/api/v1/plans/{plan_id}/book/generate \
  -H "Authorization: Bearer <JWT>"

# Consulter le statut
curl http://localhost:8001/api/v1/plans/{plan_id}/book \
  -H "Authorization: Bearer <JWT>"
```
