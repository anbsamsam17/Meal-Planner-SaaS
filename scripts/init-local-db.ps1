# =============================================================================
# scripts/init-local-db.ps1 — Initialisation de la base de données locale (Windows)
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
#   - uv installé et dépendances Python synchronisées (uv sync depuis la racine)
#
# Usage :
#   powershell -ExecutionPolicy Bypass -File scripts/init-local-db.ps1
#   # Ou depuis PowerShell avec la politique d'exécution déjà configurée :
#   .\scripts\init-local-db.ps1
#
# Variables surchargeables :
#   $env:DB_PORT = "5433"   (port hôte PostgreSQL Docker)
#   $env:DB_USER = "mealplanner"
#   $env:DB_NAME = "mealplanner_dev"
#   $env:DB_PASS = "mealplanner_dev_password"
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Configuration (surchargeables via variables d'environnement) ---
$DbPort      = if ($env:DB_PORT) { $env:DB_PORT } else { "5433" }
$DbUser      = if ($env:DB_USER) { $env:DB_USER } else { "mealplanner" }
$DbName      = if ($env:DB_NAME) { $env:DB_NAME } else { "mealplanner_dev" }
$DbPass      = if ($env:DB_PASS) { $env:DB_PASS } else { "mealplanner_dev_password" }
$DbContainer = "mealplanner_postgres"

$DatabaseUrl = "postgresql+asyncpg://${DbUser}:${DbPass}@localhost:${DbPort}/${DbName}"

function Write-Info    { param($Msg) Write-Host "[INFO] $Msg" -ForegroundColor Green }
function Write-Warning { param($Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "[ERR]  $Msg" -ForegroundColor Red }

# --- Vérification que le container PostgreSQL est bien démarré ---
Write-Info "Vérification du container PostgreSQL '$DbContainer'..."
$RunningContainers = docker ps --format '{{.Names}}' 2>&1
if ($RunningContainers -notmatch $DbContainer) {
  Write-Err "Le container '$DbContainer' n'est pas en cours d'exécution."
  Write-Err "Lancez d'abord : docker compose -f docker-compose.dev.yml up -d postgres"
  exit 1
}
Write-Info "Container détecté — OK."

# --- Attente readiness PostgreSQL ---
Write-Info "Attente de la disponibilité de PostgreSQL..."
$MaxTries = 30
$Count = 0
do {
  docker exec $DbContainer pg_isready -U $DbUser -d $DbName -q 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { break }
  $Count++
  if ($Count -ge $MaxTries) {
    Write-Err "PostgreSQL n'est pas prêt après $MaxTries tentatives. Abandon."
    exit 1
  }
  Start-Sleep -Seconds 1
} while ($true)
Write-Info "PostgreSQL prêt."

# =============================================================================
# ÉTAPE 1 — Création du schéma auth et des rôles Supabase simulés
# =============================================================================
Write-Info "Étape 1/3 : Création des rôles et schéma Supabase simulés..."

# SQL transmis via heredoc PowerShell à psql dans le container
$SqlScript = @"
CREATE SCHEMA IF NOT EXISTS auth;

CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID AS `$`$
  SELECT COALESCE(
    current_setting('request.jwt.claim.sub', true)::UUID,
    '00000000-0000-0000-0000-000000000000'::UUID
  );
`$`$ LANGUAGE SQL STABLE;

DO `$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN;
    RAISE NOTICE 'Role anon cree.';
  ELSE
    RAISE NOTICE 'Role anon existant - ignore.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
    RAISE NOTICE 'Role authenticated cree.';
  ELSE
    RAISE NOTICE 'Role authenticated existant - ignore.';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOLOGIN BYPASSRLS;
    RAISE NOTICE 'Role service_role cree.';
  ELSE
    RAISE NOTICE 'Role service_role existant - ignore.';
  END IF;
END
`$`$;

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
"@

# Écriture du script SQL dans un fichier temporaire et exécution dans le container
$TempSqlFile = [System.IO.Path]::GetTempFileName() + ".sql"
$SqlScript | Out-File -FilePath $TempSqlFile -Encoding UTF8

try {
  # Copie du fichier SQL dans le container puis exécution
  docker cp $TempSqlFile "${DbContainer}:/tmp/init_supabase_roles.sql" | Out-Null
  docker exec $DbContainer psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -f /tmp/init_supabase_roles.sql
  if ($LASTEXITCODE -ne 0) {
    Write-Err "Échec de l'exécution du script SQL Supabase."
    exit 1
  }
} finally {
  Remove-Item -Force $TempSqlFile -ErrorAction SilentlyContinue
}

Write-Info "Étape 1/3 : rôles et schéma auth créés."

# =============================================================================
# ÉTAPE 2 — Application des migrations Alembic
# =============================================================================
Write-Info "Étape 2/3 : Application des migrations Alembic..."

# Résolution du chemin racine du monorepo depuis l'emplacement de ce script
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$MonorepoRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$ApiDir       = Join-Path $MonorepoRoot "apps\api"

Push-Location $ApiDir
try {
  $env:DATABASE_URL = $DatabaseUrl
  uv run alembic upgrade head
  if ($LASTEXITCODE -ne 0) {
    Write-Err "Échec des migrations Alembic."
    exit 1
  }
} finally {
  Pop-Location
}

Write-Info "Étape 2/3 : migrations appliquées."

# =============================================================================
# ÉTAPE 3 — Seed des données de test
# =============================================================================
Write-Info "Étape 3/3 : Injection des données de test (seed)..."

Push-Location $ApiDir
try {
  $env:DATABASE_URL = $DatabaseUrl
  uv run python -m src.scripts.seed
  if ($LASTEXITCODE -ne 0) {
    Write-Err "Échec du seed."
    exit 1
  }
} finally {
  Pop-Location
}

Write-Info "Étape 3/3 : données de test injectées."

# --- Résumé ---
Write-Host ""
Write-Info "Setup DB local terminé avec succès."
Write-Host ""
Write-Host "  Base de données : $DbName sur localhost:$DbPort"
Write-Host "  Utilisateur     : $DbUser"
Write-Host ""
Write-Host "Prochaine étape — démarrer l'API :"
Write-Host "  `$env:DATABASE_URL = '$DatabaseUrl'"
Write-Host "  uv run uvicorn apps.api.src.main:app --port 8001 --reload"
