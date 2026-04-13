# 05 — Guide Setup Alembic

## Contexte

Alembic gère les migrations de schéma PostgreSQL pour le backend FastAPI.
Les fichiers SQL de ce dossier (`01-schema-core.sql`, etc.) représentent l'état initial (migration `0001`).
Toutes les évolutions futures passent par des fichiers de migration Alembic, **jamais par modification directe des SQL**.

---

## Structure dans le projet

```
apps/
└── api/
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    │       └── 20260411_1000_initial_schema.py
    ├── app/
    │   ├── main.py
    │   └── models/         # SQLAlchemy models (si utilisé)
    └── requirements.txt
```

---

## Installation

```bash
# Dans l'environnement virtuel du projet
pip install alembic sqlalchemy psycopg2-binary asyncpg
```

Ajouter dans `requirements.txt` :
```
alembic==1.13.1
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
asyncpg==0.29.0
```

---

## Configuration alembic.ini

```ini
[alembic]
script_location = alembic
file_template = %%(year)s%%(month)s%%(day)s_%%(hour)s%%(minute)s_%%(slug)s
# Désactiver le timestamp automatique (on le gère dans le nom)
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %%H:%%M:%%S
```

---

## env.py — Configuration Supabase

```python
"""
Configuration Alembic pour MealPlanner SaaS.
Connexion à Supabase PostgreSQL via DATABASE_URL (variable d'environnement).
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# Lecture de la config Alembic
config = context.config

# Configuration logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injection de la DATABASE_URL depuis l'environnement
# Format Supabase : postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
# Ne JAMAIS hardcoder cette URL dans le code source.
database_url = os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", database_url)

# Si SQLAlchemy models sont définis, importer target_metadata ici.
# Pour l'instant, migrations SQL raw uniquement.
target_metadata = None


def run_migrations_offline() -> None:
    """
    Mode offline : génère le SQL sans connexion réelle.
    Utile pour review avant application en production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Mode online : connexion directe à Supabase PostgreSQL.
    Utilisé en CI/CD et en développement local via pgBouncer ou connexion directe.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool obligatoire pour les environnements serverless (Railway, Render)
        # où les connexions ne sont pas persistées entre les requêtes.
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Convention de nommage des migrations

Format : `YYYYMMDD_HHMM_description_courte.py`

Exemples :
```
20260411_1000_initial_schema.py
20260415_0900_add_recipe_source_index.py
20260420_1430_add_subscriptions_table.py
20260501_1100_alter_member_preferences_add_locale.py
```

**Règles :**
- `YYYYMMDD` = date UTC de création de la migration
- `HHMM` = heure UTC (évite les collisions si plusieurs migrations le même jour)
- Description en `snake_case`, verbe à l'infinitif (`add_`, `alter_`, `drop_`, `create_`)
- Maximum 50 caractères pour la description

---

## Initialisation — migration 0001

La première migration encapsule les fichiers SQL de phase-0 :

```python
"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-04-11 10:00:00.000000
"""
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lire et exécuter les fichiers SQL dans l'ordre
    import os
    sql_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'phase-0', 'database')
    files = [
        '00-setup-extensions.sql',
        '01-schema-core.sql',
        '02-indexes.sql',
        '04-triggers-functions.sql',  # avant 03 (get_current_household_id dépendance)
        '03-rls-policies.sql',
        '07-seed-data.sql',           # seed uniquement en dev/staging, pas en prod
    ]
    for filename in files:
        filepath = os.path.join(sql_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            sql = f.read()
        op.execute(sql)


def downgrade() -> None:
    # Suppression complète — DESTRUCTIF, uniquement pour reset dev local
    op.execute("""
        DROP TABLE IF EXISTS subscriptions CASCADE;
        DROP TABLE IF EXISTS weekly_books CASCADE;
        DROP TABLE IF EXISTS fridge_items CASCADE;
        DROP TABLE IF EXISTS shopping_lists CASCADE;
        DROP TABLE IF EXISTS planned_meals CASCADE;
        DROP TABLE IF EXISTS weekly_plans CASCADE;
        DROP TABLE IF EXISTS recipe_feedbacks CASCADE;
        DROP TABLE IF EXISTS member_taste_vectors CASCADE;
        DROP TABLE IF EXISTS member_preferences CASCADE;
        DROP TABLE IF EXISTS recipe_ingredients CASCADE;
        DROP TABLE IF EXISTS recipe_embeddings CASCADE;
        DROP TABLE IF EXISTS recipes CASCADE;
        DROP TABLE IF EXISTS ingredients CASCADE;
        DROP TABLE IF EXISTS household_members CASCADE;
        DROP TABLE IF EXISTS households CASCADE;
        DROP FUNCTION IF EXISTS get_current_household_id() CASCADE;
        DROP FUNCTION IF EXISTS trigger_set_updated_at() CASCADE;
        DROP FUNCTION IF EXISTS validate_recipe_quality() CASCADE;
        DROP FUNCTION IF EXISTS get_household_constraints(UUID) CASCADE;
        DROP FUNCTION IF EXISTS cleanup_old_embeddings() CASCADE;
    """)
```

---

## Commandes essentielles

```bash
# Vérifier la connexion et l'état des migrations
alembic current

# Appliquer toutes les migrations en attente
alembic upgrade head

# Revenir à la migration précédente (ATTENTION en production)
alembic downgrade -1

# Générer une nouvelle migration vide
alembic revision --autogenerate -m "add_fridge_scan_table"
# Nom généré : 20260420_HHMM_add_fridge_scan_table.py

# Voir l'historique des migrations
alembic history --verbose

# Mode offline : générer le SQL sans appliquer
alembic upgrade head --sql > migration_preview.sql
```

---

## Variables d'environnement requises

```bash
# .env.local (jamais committé)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

# Pour pgBouncer (Transaction mode — recommandé en production Supabase)
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

---

## Piège pgBouncer + Supabase

En mode Transaction pooling (pgBouncer), certaines fonctionnalités PostgreSQL ne fonctionnent pas :
- `SET LOCAL` → à éviter dans les migrations
- `LISTEN/NOTIFY` → utiliser Supabase Realtime à la place
- `pg_advisory_lock` → remplacer par une colonne `locked_at` dans la table

Pour les migrations Alembic, utiliser la **connexion directe** (port 5432), pas le pooler (port 6543).
