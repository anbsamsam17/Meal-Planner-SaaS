import sys
import asyncio

# Fix asyncpg sur Windows : ProactorEventLoop cause des ConnectionResetError
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

"""
env.py — Configuration runtime Alembic pour MealPlanner SaaS.

Compatible Supabase + pgBouncer (mode transaction) :
- NullPool : chaque migration ouvre/ferme sa propre connexion, évite les
  transactions zombies laissées ouvertes côté pgBouncer après la migration.
- compare_type=True : Alembic détecte les changements de type de colonne
  (ex : TEXT → VARCHAR(255)) qui seraient silencieux sans ce flag.
- compare_server_default=True : détecte les changements de DEFAULT SERVER
  (ex : ajout/retrait de DEFAULT now()).

Modes supportés :
- Online async  : utilisé par `alembic upgrade head` (connexion directe DB)
- Offline       : utilisé par `alembic upgrade head --sql` (génère un script SQL)

Schemas inclus :
- public uniquement. Les schémas auth, storage, realtime (Supabase internals)
  sont explicitement exclus pour éviter de générer des migrations parasites.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import du DeclarativeBase pour l'autogenerate
# Tous les modèles doivent être importés ICI pour que Alembic les découvre.
# L'import de src.db.base charge automatiquement les modèles via src.db.models.__init__
from src.db.base import Base  # noqa: F401 — side effects nécessaires
import src.db.models  # noqa: F401 — importe tous les modèles (side effects)

# Configuration Alembic depuis alembic.ini
config = context.config

# Configuration du logging via alembic.ini [loggers]
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées cibles pour l'autogenerate
target_metadata = Base.metadata

# Schemas Supabase à exclure de l'autogenerate.
# Ces schémas sont gérés par Supabase — toute migration générée dessus serait destructive.
EXCLUDED_SCHEMAS = {"auth", "storage", "realtime", "extensions", "graphql", "graphql_public"}

# Schémas à inclure dans l'autogenerate (uniquement public pour Phase 0/1)
INCLUDED_SCHEMAS = {"public"}


def include_object(object, name, type_, reflected, compare_to):  # noqa: A002
    """Filtre les objets à inclure dans l'autogenerate.

    Exclut les objets des schémas Supabase internes pour éviter les migrations
    parasites qui dropperaient les tables auth.users, storage.objects, etc.
    """
    if type_ == "table":
        schema = getattr(object, "schema", None) or "public"
        if schema in EXCLUDED_SCHEMAS:
            return False
    return True


def get_database_url() -> str:
    """Retourne l'URL de connexion depuis les variables d'environnement.

    Priorité :
    1. Variable DATABASE_URL directe (production, CI)
    2. Construction depuis les composantes individuelles (développement local)

    Attention : asyncpg est utilisé car SQLAlchemy 2.0 async requiert un driver async.
    Alembic en mode offline (--sql) utilise quand même cette URL pour la syntaxe du dialecte.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "La variable d'environnement DATABASE_URL est requise. "
            "Format attendu : postgresql+asyncpg://user:pass@host:5432/dbname\n"
            "Pour le développement local, copier .env.example vers .env et renseigner DATABASE_URL."
        )
    # Normalisation : psycopg2:// → asyncpg:// si nécessaire (Supabase Dashboard donne parfois l'URL psycopg2)
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Mode offline : génère le SQL sans connexion DB.

    Appelé par : `alembic upgrade head --sql > migration.sql`
    Utile pour générer un script SQL à auditer avant application en production
    ou pour les environnements sans accès réseau à la DB.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        include_object=include_object,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Exécute les migrations dans une connexion synchrone wrappée.

    Séparé de run_migrations_online pour permettre l'utilisation avec
    run_sync() dans le contexte async.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        include_object=include_object,
        # Table alembic_version dans le schéma public (pas le schéma par défaut du user)
        version_table_schema="public",
        # Préfixe des transactions explicites pour Supabase pgBouncer mode transaction
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Mode online async : connexion directe à la base de données.

    Utilise NullPool pour la compatibilité Supabase/pgBouncer :
    - pgBouncer en mode transaction ne supporte pas les connexions persistantes
      avec transactions imbriquées (erreur : "cannot use prepared statements")
    - NullPool : chaque opération ouvre une nouvelle connexion et la ferme immédiatement
    - Pas de pool overhead pour Alembic (les migrations s'exécutent rarement)
    """
    url = get_database_url()

    # Mise à jour dynamique de l'URL dans la config Alembic
    # (remplace la valeur statique sqlalchemy.url de alembic.ini)
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # connect_args pour Supabase : désactive le prepared statement caching
        # incompatible avec pgBouncer en mode transaction
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    async with connectable.connect() as connection:
        # Forcer le search_path sur public pour la session de migration
        await connection.execute(text("SET search_path TO public"))
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online_sync() -> None:
    """Mode online synchrone — contourne les bugs asyncpg sur Windows.

    Utilise psycopg2 (sync) au lieu d'asyncpg (async) pour les migrations.
    Les migrations n'ont pas besoin d'async — seul le runtime FastAPI en a besoin.
    """
    from sqlalchemy import engine_from_config

    url = get_database_url()
    # Convertir l'URL async en sync via psycopg (v3) — compatible Windows FR
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text("SET search_path TO public"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online_sync()
