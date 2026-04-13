# Guide de déploiement — Presto

> Dernière mise à jour : 2026-04-12
> Stack : FastAPI + Celery + Next.js 14 + PostgreSQL (Supabase) + Redis
> Repo : https://github.com/anbsamsam17/Meal-Planner-SaaS.git
>
> Temps estimé : 10 minutes pour Vercel, 15 minutes pour Railway

---

## Section 1 — Pré-requis

Avant de commencer, s'assurer d'avoir :

| Pré-requis | Lien | Statut |
|---|---|---|
| Compte Railway | https://railway.app | Obligatoire |
| Compte Vercel | https://vercel.com | Obligatoire |
| Repo GitHub pushé | https://github.com/anbsamsam17/Meal-Planner-SaaS | Obligatoire |
| Projet Supabase configuré | https://supabase.com/dashboard | Obligatoire |
| Domaine personnalisé (optionnel) | `api.presto.fr`, `app.presto.fr` | Optionnel |

### Variables à collecter avant de commencer

Ouvrir un éditeur de texte et noter les valeurs suivantes depuis les dashboards avant de démarrer — elles seront saisies dans Railway et Vercel.

**Depuis Supabase Dashboard → Settings → API :**
- `SUPABASE_URL` (ex: `https://abcdefgh.supabase.co`)
- `SUPABASE_ANON_KEY` (clé publique, format `eyJ...`)
- `SUPABASE_SERVICE_ROLE_KEY` (clé privée, format `eyJ...`)
- `SUPABASE_JWT_SECRET` (Settings → API → JWT Settings → JWT Secret)

**Depuis Supabase Dashboard → Settings → Database → Connection string (Python) :**
- `DATABASE_URL` (format : `postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres`)
  - Important : utiliser le mode **Session** (port 5432, pas port 6543 pgBouncer) avec le suffixe `+asyncpg`

**Depuis Google AI Studio :**
- `GOOGLE_AI_API_KEY` (https://aistudio.google.com/apikey)

**Depuis Stripe Dashboard → Developers → API Keys :**
- `STRIPE_SECRET_KEY` (sk_live_... en prod, sk_test_... en staging)
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (pk_live_... en prod)

**Optionnel :**
- `SPOONACULAR_API_KEY`, `EDAMAM_APP_ID`, `EDAMAM_APP_KEY`
- `SENTRY_DSN`, `POSTHOG_KEY`

---

## Section 2 — Railway (Backend API + Worker Celery)

### Étape 2.1 — Créer le projet Railway

1. Se connecter sur https://railway.app
2. Cliquer **New Project**
3. Choisir **Deploy from GitHub repo**
4. Autoriser Railway à accéder au compte GitHub si ce n'est pas déjà fait
5. Sélectionner le repo `anbsamsam17/Meal-Planner-SaaS`
6. Railway va créer un projet vide — ne pas encore déployer, configurer d'abord les services

---

### Étape 2.2 — Ajouter le plugin Redis

Avant de configurer l'API (elle a besoin de `REDIS_URL`), ajouter Redis :

1. Dans le projet Railway, cliquer **+ New** → **Database** → **Add Redis**
2. Railway provisionne le Redis et injecte automatiquement `REDIS_URL` dans l'environnement du projet
3. Prendre note de l'URL Redis (visible dans le panel Redis → Variables) — elle sera utilisée pour le worker aussi

---

### Étape 2.3 — Service 1 : API FastAPI

1. Cliquer **+ New** → **GitHub Repo** → sélectionner `Meal-Planner-SaaS`
2. Dans les **Settings** du service créé :
   - **Service Name** : `mealplanner-api`
   - **Root Directory** : `/` (racine du monorepo — le Dockerfile gère tout)
   - **Dockerfile Path** : `apps/api/Dockerfile`
   - **Start Command** : laisser vide (le CMD du Dockerfile est utilisé)
3. Aller dans l'onglet **Variables** et ajouter toutes les variables suivantes :

```
# Application
ENV=production
LOG_LEVEL=INFO
WEB_CONCURRENCY=2

# Base de données Supabase
DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Supabase Auth
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=[votre-jwt-secret]

# Redis (auto-injectée par Railway si vous utilisez le plugin)
# REDIS_URL est injecté automatiquement — ne pas redéfinir manuellement
REDIS_CACHE_URL=${REDIS_URL}

# LLM Google Gemini
GOOGLE_AI_API_KEY=[votre-clé]
GEMINI_MODEL=gemini-2.0-flash
LLM_PROVIDER=gemini

# APIs Recettes (optionnel)
SPOONACULAR_API_KEY=
EDAMAM_APP_ID=
EDAMAM_APP_KEY=

# Stripe (optionnel si Phase 2 active)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_FAMILLE=price_...
STRIPE_PRICE_COACH=price_...
STRIPE_SUCCESS_URL=https://app.presto.fr/billing/success
STRIPE_CANCEL_URL=https://app.presto.fr/billing/cancel

# Storage Cloudflare R2 (optionnel si Phase 2 active)
R2_ACCESS_KEY=
R2_SECRET=
R2_BUCKET=mealplanner-pdfs
R2_IMAGES_BUCKET=mealplanner-images
R2_ENDPOINT=https://[account-id].r2.cloudflarestorage.com
R2_PUBLIC_URL=

# Monitoring (optionnel)
SENTRY_DSN=
```

4. Aller dans **Settings → Deploy** :
   - **Healthcheck Path** : `/api/v1/health`
   - **Healthcheck Timeout** : 30
   - **Restart Policy** : On Failure (3 retries)

5. Cliquer **Deploy** — Railway va builder l'image depuis `apps/api/Dockerfile` avec le context racine

6. Attendre que le déploiement soit vert (2-4 minutes la première fois)

7. **(Optionnel) Custom domain** : Settings → Domains → Add Custom Domain → `api.presto.fr`
   - Copier le CNAME fourni par Railway et l'ajouter dans votre DNS

---

### Étape 2.4 — Service 2 : Worker Celery

1. Dans le même projet Railway, cliquer **+ New** → **GitHub Repo** → même repo `Meal-Planner-SaaS`
2. Dans **Settings** :
   - **Service Name** : `mealplanner-worker`
   - **Root Directory** : `/`
   - **Dockerfile Path** : `apps/worker/Dockerfile`
   - **Start Command** : laisser vide (l'ENTRYPOINT du Dockerfile est utilisé)
3. Aller dans **Variables** — copier exactement les mêmes variables que l'API (sauf `WEB_CONCURRENCY` et `PORT` qui ne concernent pas le worker) :

```
# Application
ENV=production
LOG_LEVEL=INFO
CELERY_CONCURRENCY=4
CELERY_PREFETCH_MULTIPLIER=1
CELERY_LOG_LEVEL=INFO

# Base de données (même que l'API)
DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres

# Supabase (même que l'API)
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=[votre-jwt-secret]

# Redis (injecté automatiquement par le plugin Railway)
# REDIS_URL est partagé entre l'API et le worker via les variables de projet Railway
REDIS_CACHE_URL=${REDIS_URL}

# LLM
GOOGLE_AI_API_KEY=[votre-clé]
GEMINI_MODEL=gemini-2.0-flash
LLM_PROVIDER=gemini

# Storage (même que l'API)
R2_ACCESS_KEY=
R2_SECRET=
R2_BUCKET=mealplanner-pdfs
R2_IMAGES_BUCKET=mealplanner-images
R2_ENDPOINT=
R2_PUBLIC_URL=

# APIs Recettes
SPOONACULAR_API_KEY=
EDAMAM_APP_ID=
EDAMAM_APP_KEY=
```

4. Le worker ne nécessite **pas** de port exposé ni de healthcheck HTTP
   - Railway ne génère pas de domaine public pour ce service (aucune requête entrante)
   - La santé du worker est surveillée via les logs Celery (pas de `/health` HTTP)

5. Cliquer **Deploy**

---

### Étape 2.5 — Variables partagées entre services Railway

Pour éviter la duplication, Railway permet de définir des variables au niveau **projet** qui sont injectées dans tous les services :

1. Dans Railway → votre projet → onglet **Variables** (niveau projet, pas service)
2. Ajouter les variables communes (`DATABASE_URL`, `SUPABASE_*`, `GOOGLE_AI_API_KEY`, etc.)
3. Les services API et Worker héritent automatiquement de ces variables de projet

---

## Section 3 — Vercel (Frontend Next.js 14)

### Étape 3.1 — Importer le repo

1. Se connecter sur https://vercel.com
2. Cliquer **Add New...** → **Project**
3. Cliquer **Import Git Repository** et sélectionner `anbsamsam17/Meal-Planner-SaaS`
4. Si le repo n'apparaît pas, cliquer **Adjust GitHub App Permissions** pour autoriser l'accès

### Étape 3.2 — Configurer le projet

Dans l'écran de configuration Vercel avant le premier déploiement :

| Champ | Valeur |
|---|---|
| Project Name | `mealplanner-web` |
| Framework Preset | `Next.js` (auto-détecté) |
| Root Directory | `apps/web` |
| Build Command | `pnpm build` |
| Output Directory | `.next` (auto-détecté par Next.js) |
| Install Command | `pnpm install` |

### Étape 3.3 — Variables d'environnement Vercel

Dans l'écran de configuration, aller dans **Environment Variables** et ajouter :

```
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=https://mealplanner-api.up.railway.app
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_FLAGSMITH_ENV_KEY=
```

Notes importantes :
- `NEXT_PUBLIC_API_URL` : copier l'URL générée par Railway pour le service `mealplanner-api` (visible dans Railway → service → Settings → Domains)
- En production avec domaine personnalisé : `https://api.presto.fr`
- Ces variables commençant par `NEXT_PUBLIC_` sont embarquées dans le bundle JavaScript — ne jamais y mettre de clés secrètes

### Étape 3.4 — Déployer

1. Cliquer **Deploy**
2. Vercel va installer les dépendances avec `pnpm`, builder Next.js et déployer
3. Temps estimé : 3-5 minutes pour le premier build

4. **(Optionnel) Custom domain** : Project → Settings → Domains → Add → `app.presto.fr`
   - Suivre les instructions DNS Vercel (CNAME ou A record selon le registrar)

5. **Preview deployments** : Vercel crée automatiquement un déploiement de preview pour chaque Pull Request — activé par défaut, aucune configuration nécessaire

---

## Section 4 — Post-déploiement

### Étape 4.1 — Initialiser le schéma Supabase

La base de données Supabase ne se configure pas via Docker init-scripts en production. Suivre ces étapes dans l'ordre :

**1. Extensions PostgreSQL (Supabase Dashboard → SQL Editor) :**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

**2. Schéma principal :** Ouvrir `infra/docker/init-scripts/postgres/02-schema.sql` depuis le repo et copier-coller le contenu dans Supabase SQL Editor → Run

**3. Schéma Phase 2 :** Même opération avec `infra/docker/init-scripts/postgres/04-phase2-schema.sql`

**4. Seed de développement (optionnel en prod) :** Ne pas appliquer `03-seed.sql` en production

### Étape 4.2 — Configurer Supabase Auth

1. Supabase Dashboard → Authentication → URL Configuration :
   - **Site URL** : `https://app.presto.fr` (ou l'URL Vercel en staging)
   - **Redirect URLs** : ajouter `https://app.presto.fr/auth/callback`

2. Si en staging sur Vercel preview : ajouter aussi `https://*.vercel.app/auth/callback`

### Étape 4.3 — Configurer le webhook Stripe

1. Stripe Dashboard → Developers → Webhooks → Add Endpoint
2. **Endpoint URL** : `https://api.presto.fr/api/v1/webhooks/stripe`
   (ou `https://mealplanner-api.up.railway.app/api/v1/webhooks/stripe` si pas de domaine custom)
3. **Events à écouter** :
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copier le **Signing Secret** (`whsec_...`) et le mettre dans `STRIPE_WEBHOOK_SECRET` sur Railway

### Étape 4.4 — Vérifier le déploiement

Tester les endpoints suivants après déploiement :

```bash
# Health API (doit retourner {"status": "ok"})
curl https://api.presto.fr/api/v1/health

# Readiness API (vérifie DB + Redis)
curl https://api.presto.fr/api/v1/ready

# Frontend (doit retourner la landing page)
curl -I https://app.presto.fr
```

---

## Récapitulatif des URLs de production

| Service | URL |
|---|---|
| Frontend | `https://app.presto.fr` |
| API FastAPI | `https://api.presto.fr` |
| Documentation API | `https://api.presto.fr/docs` |
| Health check | `https://api.presto.fr/api/v1/health` |

---

## Dépannage courant

### Railway : "Build failed — workspace root not found"
Le build context doit être la racine du monorepo, pas `apps/api/`. Vérifier dans Railway → service → Settings que **Root Directory** est `/` (pas `apps/api`).

### Railway : le worker crash au démarrage
Vérifier que `REDIS_URL` est bien injecté. Si le plugin Redis est dans le même projet Railway, la variable est auto-injectée. Sinon, la définir manuellement.

### Vercel : "pnpm not found"
Vercel détecte pnpm via `pnpm-lock.yaml` à la racine. Vérifier que le fichier est commité dans le repo.

### Vercel : erreur CORS API
S'assurer que `NEXT_PUBLIC_API_URL` pointe vers l'URL Railway correcte (avec `https://`, sans slash final). La CSP dans `next.config.mjs` autorise les connexions vers l'API en production.

### Supabase : auth callback échoue
Vérifier que l'URL `https://app.presto.fr/auth/callback` est bien dans la liste des **Redirect URLs** autorisées dans Supabase Auth.
