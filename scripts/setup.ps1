# scripts/setup.ps1 — Script de setup initial Presto (Windows PowerShell)
#
# Usage (depuis PowerShell) :
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\scripts\setup.ps1
#
# Ou depuis bash (Git Bash / WSL) :
#   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
#
# Ce script vérifie les prérequis, installe les dépendances et affiche les next steps.

$ErrorActionPreference = "Stop"

# =============================================================================
# Fonctions utilitaires
# =============================================================================
function Write-Info    { param($msg) Write-Host "[INFO]    $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK]      $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[WARN]    $msg" -ForegroundColor Yellow }
function Write-Fail    { param($msg) Write-Host "[ERREUR]  $msg" -ForegroundColor Red; exit 1 }

# =============================================================================
# En-tête
# =============================================================================
Write-Host ""
Write-Host "Presto — Setup de l'environnement de développement (Windows)" -ForegroundColor White
Write-Host "========================================================================" -ForegroundColor White
Write-Host ""

# =============================================================================
# Vérification des prérequis
# =============================================================================
Write-Info "Vérification des prérequis..."

# Vérifier uv
$uvInstalled = Get-Command uv -ErrorAction SilentlyContinue
if ($uvInstalled) {
    $uvVersion = (uv --version 2>&1) -replace "uv ", ""
    Write-Success "uv trouvé : $uvVersion"
} else {
    Write-Host ""
    Write-Fail "uv non installé. Installer avec :
    powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"
    Puis redémarrer PowerShell."
}

# Vérifier Python 3.12 (uv l'installera automatiquement si absent)
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if ($pythonInstalled) {
    $pythonVersion = (python --version 2>&1) -replace "Python ", ""
    Write-Success "Python trouvé : $pythonVersion"
    if (-not $pythonVersion.StartsWith("3.12")) {
        Write-Warning "Python 3.12 recommandé (trouvé $pythonVersion). uv installera Python 3.12 automatiquement."
    }
} else {
    Write-Warning "python non trouvé dans PATH — uv installera Python 3.12 automatiquement."
}

# Vérifier pnpm
$pnpmInstalled = Get-Command pnpm -ErrorAction SilentlyContinue
if ($pnpmInstalled) {
    $pnpmVersion = (pnpm --version 2>&1)
    Write-Success "pnpm trouvé : $pnpmVersion"
    if (-not $pnpmVersion.StartsWith("9")) {
        Write-Warning "pnpm 9.x recommandé (trouvé $pnpmVersion). Mettre à jour : npm install -g pnpm@9"
    }
} else {
    Write-Fail "pnpm non installé. Installer avec : npm install -g pnpm@9"
}

# Vérifier Node.js >= 20
$nodeInstalled = Get-Command node -ErrorAction SilentlyContinue
if ($nodeInstalled) {
    $nodeVersion = (node --version 2>&1) -replace "v", ""
    $nodeMajor = [int]($nodeVersion.Split(".")[0])
    Write-Success "Node.js trouvé : v$nodeVersion"
    if ($nodeMajor -lt 20) {
        Write-Fail "Node.js >= 20 requis (trouvé v$nodeVersion). Installer depuis https://nodejs.org"
    }
} else {
    Write-Fail "Node.js non installé. Installer depuis https://nodejs.org"
}

# Vérifier Docker
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerInstalled) {
    $dockerVersion = (docker --version 2>&1) -replace "Docker version ", "" -replace ",.*", ""
    Write-Success "Docker trouvé : $dockerVersion"
    # Vérifier que Docker Desktop est démarré
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker est installé mais ne répond pas. Démarrer Docker Desktop."
    }
} else {
    Write-Fail "Docker non installé. Installer Docker Desktop depuis https://docker.com/products/docker-desktop"
}

Write-Host ""
Write-Success "Tous les prérequis sont satisfaits."
Write-Host ""

# =============================================================================
# Répertoire racine du projet
# =============================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# =============================================================================
# Configuration de l'environnement
# =============================================================================
if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.example" ".env.local"
    Write-Success ".env.local créé depuis .env.example"
    Write-Warning "IMPORTANT : éditer .env.local avec vos vraies valeurs avant de continuer."
    Write-Warning "            Ouvrir .env.local dans VS Code : code .env.local"
} else {
    Write-Info ".env.local existe déjà — non écrasé."
}

# =============================================================================
# Copie des Dockerfiles (assemblage monorepo — BUG #2 fix)
# =============================================================================
Write-Info "Copie des Dockerfiles Phase 0 vers les emplacements attendus par le CI..."

if (Test-Path "phase-0\infra\03-apps-api-Dockerfile") {
    Copy-Item "phase-0\infra\03-apps-api-Dockerfile" "apps\api\Dockerfile" -Force
    Write-Success "apps/api/Dockerfile créé"
} else {
    Write-Warning "phase-0/infra/03-apps-api-Dockerfile introuvable — apps/api/Dockerfile non créé"
}

if (Test-Path "phase-0\infra\04-apps-worker-Dockerfile") {
    Copy-Item "phase-0\infra\04-apps-worker-Dockerfile" "apps\worker\Dockerfile" -Force
    Write-Success "apps/worker/Dockerfile créé"
} else {
    Write-Warning "phase-0/infra/04-apps-worker-Dockerfile introuvable — apps/worker/Dockerfile non créé"
}

# =============================================================================
# Installation des dépendances
# =============================================================================
Write-Info "Installation des dépendances Python (uv sync)..."
uv sync
if ($LASTEXITCODE -ne 0) { Write-Fail "uv sync a échoué." }
Write-Success "Dépendances Python installées."

Write-Info "Installation des dépendances JavaScript (pnpm install)..."
pnpm install
if ($LASTEXITCODE -ne 0) { Write-Fail "pnpm install a échoué." }
Write-Success "Dépendances JavaScript installées."

# =============================================================================
# Installation des hooks pre-commit
# =============================================================================
Write-Info "Installation des hooks pre-commit..."
uv run pre-commit install
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pre-commit install a échoué (non bloquant)."
} else {
    Write-Success "Hooks pre-commit installés."
}

# =============================================================================
# Résumé et next steps
# =============================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup terminé avec succès !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines étapes :" -ForegroundColor White
Write-Host ""
Write-Host "  1. Editer .env.local avec vos clés API :" -ForegroundColor White
Write-Host "     code .env.local" -ForegroundColor Gray
Write-Host "     (voir les commentaires dans .env.example pour chaque clé)" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Démarrer les services Docker :" -ForegroundColor White
Write-Host "     docker compose -f docker-compose.dev.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Appliquer les migrations (une fois apps/api/ créé par le backend-developer) :" -ForegroundColor White
Write-Host "     cd apps/api && uv run alembic upgrade head" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Lancer l'application dans 3 terminaux PowerShell :" -ForegroundColor White
Write-Host "     Terminal 1 : uv run uvicorn apps.api.src.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host "     Terminal 2 : uv run celery -A apps.worker.src.app worker --loglevel=info" -ForegroundColor Gray
Write-Host "     Terminal 3 : pnpm --filter @mealplanner/web dev" -ForegroundColor Gray
Write-Host ""
Write-Host "  5. Interfaces locales disponibles apres demarrage :" -ForegroundColor White
Write-Host "     API FastAPI  : http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "     Next.js      : http://localhost:3000" -ForegroundColor Gray
Write-Host "     MailHog      : http://localhost:8025" -ForegroundColor Gray
Write-Host "     MinIO        : http://localhost:9001" -ForegroundColor Gray
Write-Host ""
