#!/usr/bin/env bash
# =============================================================================
# scripts/init-local-db.sh — Initialisation de la base de données locale
# =============================================================================
#
# Ce script fait tout le setup DB local en une seule commande :
#   1. Crée le schéma auth et les rôles Supabase simulés (pour le dev Docker)
#   2. Applique les migrations Alembic
#   3. Injecte les données de test (seed)
#
# Pré-requis :
#   - Docker Desktop lancé
#   - Container presto_postgres en cours d'exécution
#     (lancer d'abord : docker compose -f docker-compose.dev.yml up -d postgres)
#   - uv installé et dépendances Python synchronisées (make install)
#
# Usage :
#   bash scripts/init-local-db.sh
#   # Ou depuis Git Bash sur Windows :
#   ./scripts/init-local-db.sh
#
# Variables d'environnement surchargeables :
#   DB_PORT   : port hôte PostgreSQL (défaut : 5433)
#   DB_USER   : utilisateur PostgreSQL (défaut : mealplanner)
#   DB_NAME   : nom de la base (défaut : mealplanner_dev)
#   DB_PASS   : mot de passe (défaut : mealplanner_dev_password)
# =============================================================================

set -euo pipefail

# --- Configuration (surchargeables via variables d'environnement) ---
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-mealplanner}"
DB_NAME="${DB_NAME:-mealplanner_dev}"
DB_PASS="${DB_PASS:-mealplanner_dev_password}"
DB_CONTAINER="mealplanner_postgres"

DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}"

# Couleurs pour les messages (désactivées si pas de TTY)
if [ -t 1 ]; then
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  RED='\033[0;31m'
  NC='\033[0m' # No Color
else
  GREEN=''; YELLOW=''; RED=''; NC=''
fi

log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERR]${NC} $1" >&2; }

# --- Vérification que le container PostgreSQL est bien démarré ---
log_info "Vérification du container PostgreSQL '${DB_CONTAINER}'..."
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${DB_CONTAINER}$"; then
  log_error "Le container '${DB_CONTAINER}' n'est pas en cours d'exécution."
  log_error "Lancez d'abord : docker compose -f docker-compose.dev.yml up -d postgres"
  exit 1
fi
log_info "Container détecté — OK."

# --- Attente readiness PostgreSQL (healthcheck) ---
log_info "Attente de la disponibilité de PostgreSQL..."
MAX_TRIES=30
COUNT=0
until docker exec "${DB_CONTAINER}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" -q 2>/dev/null; do
  COUNT=$((COUNT + 1))
  if [ "${COUNT}" -ge "${MAX_TRIES}" ]; then
    log_error "PostgreSQL n'est pas prêt après ${MAX_TRIES} tentatives. Abandon."
    exit 1
  fi
  sleep 1
done
log_info "PostgreSQL prêt."

# =============================================================================
# ÉTAPE 1 — Création du schéma auth et des rôles Supabase simulés
# =============================================================================
log_info "Étape 1/3 : Création des rôles et schéma Supabase simulés..."

docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<'SQL'
-- Schéma auth simulé (Supabase l'injecte automatiquement en prod, on le crée en dev)
CREATE SCHEMA IF NOT EXISTS auth;

-- Fonction auth.uid() — retourne le claim sub du JWT courant
-- En dev sans JWT réel, retourne un UUID zéro (évite les erreurs RLS)
CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claim.sub', true)::UUID,
    '00000000-0000-0000-0000-000000000000'::UUID
  );
$$ LANGUAGE SQL STABLE;

-- Rôles Supabase requis par les policies RLS
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN;
    RAISE NOTICE 'Rôle anon créé.';
  ELSE
    RAISE NOTICE 'Rôle anon existant — ignoré.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
    RAISE NOTICE 'Rôle authenticated créé.';
  ELSE
    RAISE NOTICE 'Rôle authenticated existant — ignoré.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOLOGIN BYPASSRLS;
    RAISE NOTICE 'Rôle service_role créé.';
  ELSE
    RAISE NOTICE 'Rôle service_role existant — ignoré.';
  END IF;
END
$$;

-- Permissions minimales pour les rôles sur le schéma public
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
SQL

log_info "Étape 1/3 : rôles et schéma auth créés."

# =============================================================================
# ÉTAPE 2 — Application des migrations Alembic
# =============================================================================
log_info "Étape 2/3 : Application des migrations Alembic..."

# S'assurer qu'on est à la racine du monorepo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${MONOREPO_ROOT}/apps/api"
DATABASE_URL="${DATABASE_URL}" uv run alembic upgrade head

log_info "Étape 2/3 : migrations appliquées."

# =============================================================================
# ÉTAPE 3 — Seed des données de test
# =============================================================================
log_info "Étape 3/3 : Injection des données de test (seed)..."

cd "${MONOREPO_ROOT}/apps/api"
DATABASE_URL="${DATABASE_URL}" uv run python -m src.scripts.seed

log_info "Étape 3/3 : données de test injectées."

# --- Résumé ---
echo ""
log_info "Setup DB local terminé avec succès."
echo ""
echo "  Base de données : ${DB_NAME} sur localhost:${DB_PORT}"
echo "  Utilisateur     : ${DB_USER}"
echo ""
echo "Prochaine étape — démarrer l'API :"
echo "  DATABASE_URL=\"${DATABASE_URL}\" uv run uvicorn apps.api.src.main:app --port 8001 --reload"
