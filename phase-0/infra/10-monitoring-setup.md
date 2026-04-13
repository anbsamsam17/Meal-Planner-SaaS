# Plan de monitoring — Sentry + PostHog

> Ce document définit la stratégie d'observabilité pour MealPlanner SaaS.
> Objectif : détecter les régressions avant les utilisateurs, comprendre
> le parcours d'onboarding, et mesurer les KPI du ROADMAP en temps réel.

---

## 1. Sentry — Monitoring d'erreurs

### 1.1 DSN par environnement

Créer deux projets distincts dans Sentry (un par service) :

| Projet Sentry | Environnement | Variable |
|---------------|---------------|----------|
| `web` (Next.js) | Production | `NEXT_PUBLIC_SENTRY_DSN` |
| `api` (FastAPI) | Production | `SENTRY_DSN` |

**Pourquoi deux projets séparés :**
- Alertes indépendantes (une erreur API ne noie pas les erreurs web)
- Fingerprinting distinct (Python vs JavaScript)
- Quotas séparés (5 000 erreurs/mois chacun sur Free tier)

### 1.2 Intégration FastAPI

```python
# apps/api/src/main.py — extrait
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,  # development | staging | production
    # Release tracking : permet de voir quelle version a introduit un bug
    release=f"mealplanner-api@{settings.APP_VERSION}",
    # Traces : 10% en prod pour économiser le quota Sentry
    traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
        RedisIntegration(),
        CeleryIntegration(),
    ],
    # Ne pas envoyer les erreurs en développement local
    before_send=lambda event, hint: None if settings.ENVIRONMENT == "development" else event,
)
```

### 1.3 Intégration Next.js

```typescript
// apps/web/sentry.client.config.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION,
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,
  // Replay : enregistre les sessions utilisateur pour reproduire les bugs
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,  // Toujours enregistrer si erreur
  integrations: [
    Sentry.replayIntegration(),
  ],
})
```

### 1.4 Release Tracking via CI

Ajouter dans le workflow CI (après déploiement sur main) :

```yaml
# Extrait à ajouter dans ci.yml — job deploy-sentry-release
- name: Create Sentry Release
  uses: getsentry/action-release@v1
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
  with:
    environment: production
    projects: api web
    version: ${{ github.sha }}
```

### 1.5 Upload Source Maps (Next.js)

```typescript
// apps/web/next.config.ts — ajouter
import { withSentryConfig } from '@sentry/nextjs'

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: 'web',
  // Upload source maps automatique à chaque build Vercel
  silent: !process.env.CI,
  widenClientFileUpload: true,
  hideSourceMaps: true,  // Cacher les source maps du bundle public
})
```

### 1.6 Alertes Sentry recommandées

| Alerte | Condition | Canal |
|--------|-----------|-------|
| Spike d'erreurs | > 50 nouvelles erreurs en 5 min | Email + Slack |
| Erreur critique | Severity CRITICAL ou FATAL | Email immédiat |
| Régression | Erreur réapparaît après résolution | Email |
| Performance | P95 response time > 2s | Slack |

---

## 2. PostHog — Analytics produit

### 2.1 Instance EU

URL : `https://eu.posthog.com`
Host pour les events : `https://eu.i.posthog.com`

**Obligatoire pour le RGPD :** Les données sont hébergées en Europe.
Ajouter une notice dans la politique de confidentialité.

### 2.2 Events clés à tracker

Ces events correspondent aux étapes critiques du funnel ROADMAP (onboarding → rétention).

#### Onboarding

| Event | Propriétés | Déclencheur |
|-------|------------|-------------|
| `onboarding_started` | `source`, `referrer` | Création du compte |
| `onboarding_step_completed` | `step_name`, `step_number`, `duration_seconds` | Chaque étape du wizard |
| `onboarding_completed` | `total_duration_seconds`, `household_size`, `dietary_restrictions` | Fin du wizard (max 3 étapes) |
| `onboarding_abandoned` | `last_step`, `time_on_step` | Abandon en cours d'onboarding |

#### Planification

| Event | Propriétés | Déclencheur |
|-------|------------|-------------|
| `plan_generation_requested` | `household_size`, `week_number` | Demande de plan semaine |
| `plan_generated` | `recipes_count`, `generation_time_ms`, `plan_id` | Plan généré avec succès |
| `plan_regenerated` | `reason`, `rejected_recipes_count` | Regénération du plan |
| `recipe_viewed` | `recipe_id`, `recipe_cuisine`, `recipe_duration` | Ouverture fiche recette |
| `recipe_rated` | `recipe_id`, `rating`, `household_member` | Note 1-5 étoiles |
| `recipe_skipped` | `recipe_id`, `reason` | Skip d'une recette |

#### Liste de courses et drive

| Event | Propriétés | Déclencheur |
|-------|------------|-------------|
| `shopping_list_created` | `items_count`, `plan_id` | Création liste de courses |
| `cart_created` | `retailer`, `items_count`, `estimated_price` | Panier drive créé |
| `cart_sent_to_retailer` | `retailer`, `final_price` | Envoi vers le drive |

#### Abonnement

| Event | Propriétés | Déclencheur |
|-------|------------|-------------|
| `subscription_started` | `plan`, `price`, `trial` | Paiement Stripe confirmé |
| `subscription_cancelled` | `plan`, `reason`, `days_active` | Annulation Stripe |
| `subscription_paused` | `plan`, `days_active` | Pause abonnement |

#### PDF hebdomadaire

| Event | Propriétés | Déclencheur |
|-------|------------|-------------|
| `pdf_generated` | `week_number`, `generation_time_ms`, `file_size_kb` | PDF créé par BOOK_GENERATOR |
| `pdf_downloaded` | `week_number`, `source` | Téléchargement par l'utilisateur |

### 2.3 Funnels à créer dans PostHog

1. **Funnel Onboarding** : `onboarding_started` → `onboarding_completed` → `plan_generated`
2. **Funnel Conversion** : `plan_generated` → `subscription_started`
3. **Funnel Rétention** : J1 → J7 → J14 → J30 (sessions actives)

### 2.4 Intégration côté API Python

```python
# apps/api/src/utils/analytics.py
from posthog import Posthog
from src.config import settings

posthog_client = Posthog(
    project_api_key=settings.POSTHOG_KEY,
    host=settings.POSTHOG_HOST,
)

def track_event(user_id: str, event: str, properties: dict) -> None:
    """Envoie un event PostHog depuis le backend.
    Utilisé pour les events côté serveur (PDF généré, webhook Stripe, etc.)
    Les events UI sont envoyés directement depuis Next.js.
    """
    if settings.ENVIRONMENT == "development":
        return  # Ne pas polluer PostHog avec les données de dev
    posthog_client.capture(
        distinct_id=user_id,
        event=event,
        properties={**properties, "source": "api"},
    )
```

### 2.5 Dashboards PostHog à créer

| Dashboard | Métriques clés |
|-----------|----------------|
| Onboarding | Completion rate, abandon rate, temps par étape |
| Engagement | DAU, WAU, plans générés/semaine, recettes notées |
| Rétention | Courbe J1/J7/J14/J30, churn mensuel |
| Revenue | MRR, conversion freemium→payant, LTV estimé |
| Performance | Temps de génération des plans, erreurs API |
