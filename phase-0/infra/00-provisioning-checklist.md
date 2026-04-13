# Checklist Phase 0.0 — Provisioning des comptes tiers

> Effectuer ces étapes AVANT d'écrire la moindre ligne de code applicatif.
> Ordre d'exécution : de haut en bas. Chaque clé récupérée va dans Doppler (ou dans un
> fichier `.env.local` gitignored en attendant que Doppler soit opérationnel).
> Budget cible Phase 0 : < 100 €/mois (quasi 100 % plans gratuits).

---

## Conventions de ce document

| Symbole | Sens |
|---------|------|
| MANUEL | Action 100 % manuelle — aucun outil CLI ne peut la remplacer |
| AUTO    | Automatisable une fois le compte créé (Terraform, CLI, script) |
| DOPPLER | Clé à stocker dans Doppler immédiatement après récupération |

---

## 1. GitHub

**URL :** https://github.com

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 1.1 | Créer organisation `mealplanner-saas` (ou utiliser compte perso) | MANUEL | 5 min |
| 1.2 | Créer repo privé `mealplanner-saas` avec README initial | MANUEL | 2 min |
| 1.3 | Activer Dependabot (Security > Enable Dependabot alerts) | MANUEL | 1 min |
| 1.4 | Créer Personal Access Token (PAT) classic, scopes : `repo`, `write:packages` | MANUEL | 3 min |
| 1.5 | Stocker le PAT dans Doppler sous `GITHUB_TOKEN` | DOPPLER | 1 min |

**Ce qu'il faut récupérer :**
- PAT (affiché une seule fois — copier immédiatement)
- URL du repo : `https://github.com/<org>/mealplanner-saas`

**Coût mensuel :** 0 € (plan Free — repos privés illimités depuis 2019)

---

## 2. Vercel

**URL :** https://vercel.com

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 2.1 | Créer compte Vercel (connexion GitHub recommandée) | MANUEL | 3 min |
| 2.2 | Créer une Team `mealplanner` (nécessaire pour custom domain en prod) | MANUEL | 2 min |
| 2.3 | Importer le repo `mealplanner-saas`, pointer sur `apps/web` | MANUEL | 5 min |
| 2.4 | Récupérer le Vercel Token (Settings > Tokens) | MANUEL | 2 min |
| 2.5 | Stocker sous `VERCEL_TOKEN` dans Doppler | DOPPLER | 1 min |

**Ce qu'il faut récupérer :**
- `VERCEL_TOKEN` — pour les déploiements CI
- `VERCEL_ORG_ID` — dans Settings de la Team
- `VERCEL_PROJECT_ID` — dans Settings du projet

**Coût mensuel :** 0 € (Hobby plan pour Phase 0) → 20 $/mois (Pro) quand domaine custom en prod

---

## 3. Railway

**URL :** https://railway.app

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 3.1 | Créer compte Railway (connexion GitHub) | MANUEL | 3 min |
| 3.2 | Créer projet `mealplanner-saas` | MANUEL | 2 min |
| 3.3 | Ajouter service `api` (Dockerfile : `apps/api/Dockerfile`) | MANUEL | 5 min |
| 3.4 | Ajouter service `worker` (Dockerfile : `apps/worker/Dockerfile`) | MANUEL | 5 min |
| 3.5 | Ajouter plugin Redis (Railway plugin natif) | MANUEL | 2 min |
| 3.6 | NE PAS ajouter Postgres Railway — Supabase gère la DB | — | — |
| 3.7 | Récupérer Railway API Token (Account > Tokens) | MANUEL | 2 min |
| 3.8 | Stocker sous `RAILWAY_TOKEN` dans Doppler | DOPPLER | 1 min |

**Ce qu'il faut récupérer :**
- `RAILWAY_TOKEN` — pour les déploiements CI
- `REDIS_URL` — exposée automatiquement par Railway (format `redis://...`)

**Coût mensuel :** 5 $ (plan Starter, nécessaire pour les services dormants)
→ ~15-30 $/mois en Phase 0 selon l'usage réel (CPU/RAM/egress)

---

## 4. Supabase

**URL :** https://supabase.com

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 4.1 | Créer organisation `mealplanner` | MANUEL | 2 min |
| 4.2 | Créer projet en région `eu-central-1` (Frankfurt — RGPD) | MANUEL | 3 min |
| 4.3 | Activer l'extension pgvector (SQL Editor : `CREATE EXTENSION vector;`) | MANUEL | 2 min |
| 4.4 | Récupérer `SUPABASE_URL` (Settings > API > Project URL) | MANUEL | 1 min |
| 4.5 | Récupérer `SUPABASE_ANON_KEY` (clé publique, safe côté client) | MANUEL | 1 min |
| 4.6 | Récupérer `SUPABASE_SERVICE_ROLE_KEY` (clé admin — NE JAMAIS exposer côté client) | MANUEL | 1 min |
| 4.7 | Construire `DATABASE_URL` : `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres` | MANUEL | 2 min |
| 4.8 | Stocker les 4 clés dans Doppler | DOPPLER | 3 min |

**Ce qu'il faut récupérer :**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (rôle `anon`, RLS actif)
- `SUPABASE_SERVICE_ROLE_KEY` (bypass RLS — backend uniquement)
- `DATABASE_URL` (connexion directe PostgreSQL pour SQLAlchemy/asyncpg)

**Coût mensuel :** 0 € (Free tier : 500 MB DB, 1 GB storage, 2 GB transfer)
→ 25 $/mois (Pro) quand > 500 MB ou besoin de backups

---

## 5. Cloudflare R2

**URL :** https://dash.cloudflare.com

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 5.1 | Créer compte Cloudflare (si pas déjà existant) | MANUEL | 5 min |
| 5.2 | Aller dans R2 Object Storage > Create bucket | MANUEL | 2 min |
| 5.3 | Nommer le bucket `mealplanner-pdfs`, région `EEUR` (Europe de l'Est) | MANUEL | 1 min |
| 5.4 | Créer un second bucket `mealplanner-images` pour les images générées | MANUEL | 2 min |
| 5.5 | Créer un API Token R2 : R2 > Manage R2 API Tokens > Create Token | MANUEL | 3 min |
| 5.6 | Permissions : `Object Read & Write` sur les deux buckets | MANUEL | 1 min |
| 5.7 | Stocker `R2_ACCESS_KEY`, `R2_SECRET`, `R2_BUCKET`, `R2_ENDPOINT` dans Doppler | DOPPLER | 3 min |

**Ce qu'il faut récupérer :**
- `R2_ACCESS_KEY` (Access Key ID)
- `R2_SECRET` (Secret Access Key)
- `R2_BUCKET` = `mealplanner-pdfs`
- `R2_ENDPOINT` = `https://<account-id>.r2.cloudflarestorage.com`

**Coût mensuel :** 0 € (Free tier : 10 GB storage, 1M opérations write/mois, egress gratuit)

---

## 6. Sentry

**URL :** https://sentry.io

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 6.1 | Créer organisation `mealplanner-saas` | MANUEL | 3 min |
| 6.2 | Créer projet `web` (type : Next.js) | MANUEL | 2 min |
| 6.3 | Créer projet `api` (type : Python / FastAPI) | MANUEL | 2 min |
| 6.4 | Récupérer `SENTRY_DSN_WEB` et `SENTRY_DSN_API` | MANUEL | 2 min |
| 6.5 | Créer Auth Token pour upload source maps en CI | MANUEL | 2 min |
| 6.6 | Stocker les DSN + Auth Token dans Doppler | DOPPLER | 2 min |

**Ce qu'il faut récupérer :**
- `SENTRY_DSN_WEB`
- `SENTRY_DSN_API`
- `SENTRY_AUTH_TOKEN` (pour source maps upload depuis GitHub Actions)
- `SENTRY_ORG` et `SENTRY_PROJECT_API`

**Coût mensuel :** 0 € (Free tier : 5 000 erreurs/mois)
→ 26 $/mois (Team) quand en production réelle

---

## 7. PostHog

**URL :** https://eu.posthog.com (instance EU — conformité RGPD)

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 7.1 | Créer compte sur `eu.posthog.com` (PAS `app.posthog.com`) | MANUEL | 3 min |
| 7.2 | Créer projet `MealPlanner` | MANUEL | 2 min |
| 7.3 | Récupérer `POSTHOG_KEY` (Project API Key) | MANUEL | 1 min |
| 7.4 | Récupérer `POSTHOG_HOST` = `https://eu.i.posthog.com` | MANUEL | 1 min |
| 7.5 | Stocker dans Doppler | DOPPLER | 1 min |

**Pourquoi EU :** Données hébergées en Europe (RGPD), latence réduite pour les users FR.

**Ce qu'il faut récupérer :**
- `POSTHOG_KEY`
- `POSTHOG_HOST` = `https://eu.i.posthog.com`

**Coût mensuel :** 0 € (Free : 1M events/mois)

---

## 8. Doppler

**URL :** https://doppler.com

> Doppler est le gestionnaire de secrets centralisé. À configurer EN PREMIER parmi les outils
> DevOps car tous les autres secrets seront stockés ici.

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 8.1 | Créer compte Doppler | MANUEL | 3 min |
| 8.2 | Créer Workplace `mealplanner-saas` | MANUEL | 2 min |
| 8.3 | Créer Project `mealplanner` | MANUEL | 2 min |
| 8.4 | Créer environments : `dev`, `staging`, `prod` | MANUEL | 3 min |
| 8.5 | Installer CLI Doppler local : `brew install dopplerhq/cli/doppler` | AUTO | 2 min |
| 8.6 | Authentifier CLI : `doppler login` | MANUEL | 1 min |
| 8.7 | Créer Service Tokens pour CI (un par env) | MANUEL | 5 min |
| 8.8 | Stocker `DOPPLER_TOKEN_DEV`, `DOPPLER_TOKEN_STAGING`, `DOPPLER_TOKEN_PROD` dans GitHub Secrets | MANUEL | 3 min |

**Coût mensuel :** 0 € (Free tier : 5 projets, accès CLI, sync illimité)
→ 6 $/mois (Team) si besoin d'audit logs et de rotation automatique

---

## 9. Anthropic API

**URL :** https://console.anthropic.com

### Actions requises

| # | Action | Type | Durée |
|---|--------|------|-------|
| 9.1 | Créer compte Anthropic | MANUEL | 3 min |
| 9.2 | Ajouter une méthode de paiement (requis pour accès API) | MANUEL | 5 min |
| 9.3 | Créer API Key dans API Keys | MANUEL | 2 min |
| 9.4 | Définir un usage limit mensuel ($50 pour Phase 0) | MANUEL | 1 min |
| 9.5 | Stocker `ANTHROPIC_API_KEY` dans Doppler | DOPPLER | 1 min |

**Modèle utilisé :** `claude-sonnet-4-5` (selon ROADMAP §05)

**Coût mensuel :** Variable — estimer 20-50 $ en Phase 0 (agents batch + validation recettes)

---

## 10. APIs de recettes et enrichissement

### 10.1 Spoonacular

**URL :** https://spoonacular.com/food-api

| # | Action | Type | Durée |
|---|--------|------|-------|
| 10.1.1 | Créer compte et souscrire au plan gratuit | MANUEL | 5 min |
| 10.1.2 | Récupérer `SPOONACULAR_KEY` dans le dashboard | MANUEL | 1 min |
| 10.1.3 | Stocker dans Doppler | DOPPLER | 1 min |

**Coût mensuel :** 0 € (150 req/jour gratuit) → 29 $/mois (390 req/jour) quand scraping actif

### 10.2 Edamam

**URL :** https://developer.edamam.com

| # | Action | Type | Durée |
|---|--------|------|-------|
| 10.2.1 | Créer compte développeur | MANUEL | 5 min |
| 10.2.2 | Créer application Recipe Search API | MANUEL | 3 min |
| 10.2.3 | Récupérer `EDAMAM_APP_ID` et `EDAMAM_APP_KEY` | MANUEL | 1 min |
| 10.2.4 | Stocker dans Doppler | DOPPLER | 1 min |

**Coût mensuel :** 0 € (100 req/min gratuit)

### 10.3 Stability AI

**URL :** https://platform.stability.ai

| # | Action | Type | Durée |
|---|--------|------|-------|
| 10.3.1 | Créer compte | MANUEL | 3 min |
| 10.3.2 | Récupérer `STABILITY_API_KEY` | MANUEL | 1 min |
| 10.3.3 | Stocker dans Doppler | DOPPLER | 1 min |

**Usage Phase 0 :** Génération photos pour les PDFs (BOOK_GENERATOR agent)
**Coût mensuel :** ~10 $ en Phase 0 (images générées ponctuellement)

### 10.4 Resend (emails transactionnels)

**URL :** https://resend.com

| # | Action | Type | Durée |
|---|--------|------|-------|
| 10.4.1 | Créer compte | MANUEL | 3 min |
| 10.4.2 | Vérifier le domaine `mealplanner.fr` (DNS TXT record) | MANUEL | 10 min |
| 10.4.3 | Récupérer `RESEND_API_KEY` | MANUEL | 1 min |
| 10.4.4 | Stocker dans Doppler | DOPPLER | 1 min |

**Coût mensuel :** 0 € (3 000 emails/mois gratuits)

### 10.5 Stripe (paiement)

**URL :** https://dashboard.stripe.com

| # | Action | Type | Durée |
|---|--------|------|-------|
| 10.5.1 | Créer compte Stripe (mode test activé par défaut) | MANUEL | 5 min |
| 10.5.2 | Récupérer `STRIPE_SECRET_KEY` (format `sk_test_...`) | MANUEL | 1 min |
| 10.5.3 | Créer webhook endpoint pour les events Stripe | MANUEL | 5 min |
| 10.5.4 | Récupérer `STRIPE_WEBHOOK_SECRET` (format `whsec_...`) | MANUEL | 1 min |
| 10.5.5 | Stocker dans Doppler | DOPPLER | 1 min |

**Coût mensuel :** 0 € en Phase 0 (mode test — pas de transactions réelles)

---

## 11. Flagsmith (feature flags)

**URL :** https://flagsmith.com

> Obligatoire selon la règle ROADMAP : jamais de `if/else` en dur pour les features.

| # | Action | Type | Durée |
|---|--------|------|-------|
| 11.1 | Créer compte Flagsmith (self-hosted ou cloud) | MANUEL | 5 min |
| 11.2 | Créer Organisation `mealplanner-saas` | MANUEL | 2 min |
| 11.3 | Créer Project `mealplanner` | MANUEL | 2 min |
| 11.4 | Créer environments : `Development`, `Staging`, `Production` | MANUEL | 3 min |
| 11.5 | Récupérer `FLAGSMITH_ENV_KEY` pour chaque environment | MANUEL | 3 min |
| 11.6 | Stocker dans Doppler (une clé par env) | DOPPLER | 3 min |

**Features à créer dès Phase 0 :**
- `recipe_scout_enabled` — active le scraping batch
- `pdf_generation_enabled` — active BOOK_GENERATOR
- `drive_integration_enabled` — désactivé jusqu'à v3
- `stability_ai_enabled` — contrôle les appels payants

**Coût mensuel :** 0 € (Free : 50 000 requests/mois, 2 environnements)
→ 45 $/mois (Startup) pour les 4 environnements

---

## Récapitulatif des coûts Phase 0

| Service | Plan Phase 0 | Coût mensuel estimé |
|---------|--------------|---------------------|
| GitHub | Free | 0 € |
| Vercel | Hobby | 0 € |
| Railway | Starter | ~15 $ |
| Supabase | Free | 0 € |
| Cloudflare R2 | Free | 0 € |
| Sentry | Free (Developer) | 0 € |
| PostHog EU | Free | 0 € |
| Doppler | Free | 0 € |
| Anthropic API | Pay-as-you-go | ~20-50 $ |
| Spoonacular | Free | 0 € |
| Edamam | Free | 0 € |
| Stability AI | Pay-as-you-go | ~10 $ |
| Resend | Free | 0 € |
| Stripe | Test mode | 0 € |
| Flagsmith | Free | 0 € |
| **TOTAL** | | **~45-75 $/mois** |

Budget Phase 0 tenu sous 100 €/mois.

---

## Ordre d'exécution recommandé

1. Doppler (gestionnaire de secrets — prerequis de tout le reste)
2. GitHub (repo + PAT)
3. Supabase (DB principale — necessite du temps de propagation DNS)
4. Railway (backend)
5. Vercel (frontend)
6. Cloudflare R2 (storage)
7. Sentry + PostHog (monitoring)
8. Anthropic + Spoonacular + Edamam (APIs IA)
9. Stability AI + Resend + Stripe (features Phase 2+)
10. Flagsmith (feature flags — configurer les flags avant de coder)
