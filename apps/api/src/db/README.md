# Database — Guide des migrations Alembic

## Prérequis

```bash
# Depuis apps/api/
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/dbname"
# Ou via fichier .env dans apps/api/
```

## Commandes courantes

### Appliquer toutes les migrations (première installation)

```bash
cd apps/api
uv run alembic upgrade head
```

### Créer une nouvelle migration par autogenerate

```bash
cd apps/api
uv run alembic revision --autogenerate -m "add_content_hash_to_weekly_books"
# Vérifier le fichier généré dans alembic/versions/ avant d'appliquer
uv run alembic upgrade head
```

### Revenir en arrière d'une migration

```bash
cd apps/api
uv run alembic downgrade -1
```

### Revenir à un état vierge (dev uniquement)

```bash
cd apps/api
uv run alembic downgrade base
```

### Générer le SQL sans l'appliquer (audit production)

```bash
cd apps/api
uv run alembic upgrade head --sql > migration_to_review.sql
```

### Voir l'historique des migrations

```bash
cd apps/api
uv run alembic history --verbose
```

### Voir la version actuelle de la DB

```bash
cd apps/api
uv run alembic current
```

## Alimenter la base en dev/staging

```bash
cd apps/api
uv run python -m src.scripts.seed
```

## Ajouter un nouveau modèle ORM

1. Créer le fichier dans `src/db/models/nom_du_domaine.py`
2. Hériter de `Base` (depuis `src.db.base`)
3. Importer le modèle dans `src/db/models/__init__.py`
4. Générer la migration : `uv run alembic revision --autogenerate -m "add_xxx"`
5. Vérifier le fichier généré (toujours relire l'autogenerate avant d'appliquer)
6. Appliquer : `uv run alembic upgrade head`

## Points d'attention Supabase

- **pgBouncer mode transaction** : `statement_cache_size=0` et `prepared_statement_cache_size=0`
  sont obligatoires dans `connect_args`. Sans ça, erreur `prepared statement does not exist`.
- **NullPool dans env.py** : chaque migration ouvre/ferme sa propre connexion. Évite les
  transactions zombies après une migration partielle.
- **Schémas exclus** : `auth`, `storage`, `realtime`, `extensions` sont exclus de l'autogenerate
  (définis dans `alembic/env.py` → `EXCLUDED_SCHEMAS`). Ne jamais migrer ces schémas.
- **service_role vs anon** : les migrations s'exécutent avec `DATABASE_URL` qui doit pointer
  vers un compte avec les droits DDL (pas `anon`, utiliser le compte `postgres` ou `service_role`).

## Dépendances Python requises

```toml
# pyproject.toml (apps/api)
[project.dependencies]
sqlalchemy = { version = ">=2.0", extras = ["asyncio"] }
alembic = ">=1.13"
asyncpg = ">=0.29"
pgvector = ">=0.3"  # pgvector-python

[project.optional-dependencies]
dev = ["python-dotenv", "ruff"]
```
