# Configuration Vercel — MealPlanner SaaS (apps/web)

> Guide de configuration du projet Next.js 14 sur Vercel.
> Toutes les actions décrites sont à effectuer dans le dashboard Vercel
> (https://vercel.com/dashboard) sauf mention contraire.

---

## 1. Création du projet

### Étapes

1. **Import GitHub repo** : New Project > Import Git Repository > `mealplanner-saas`
2. **Root Directory** : `apps/web` (Vercel doit pointer sur le sous-dossier Next.js)
3. **Framework Preset** : Next.js (détecté automatiquement)
4. **Build Command** : `pnpm build` (override la détection automatique)
5. **Output Directory** : `.next` (défaut Next.js)
6. **Install Command** : `pnpm install --frozen-lockfile`
7. **Node.js Version** : 20.x

---

## 2. Variables d'environnement

### Configuration dans Vercel (Settings > Environment Variables)

Chaque variable doit être assignée aux environments appropriés :
- `Production` = branche `main`
- `Preview` = toutes les branches PR
- `Development` = `vercel dev` local

#### Variables publiques (exposées au navigateur — préfixe `NEXT_PUBLIC_`)

| Variable | Env | Description |
|----------|-----|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Prod + Preview | URL du projet Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Prod + Preview | Clé publique Supabase (RLS actif) |
| `NEXT_PUBLIC_POSTHOG_KEY` | Prod + Preview | Clé projet PostHog EU |
| `NEXT_PUBLIC_POSTHOG_HOST` | Prod + Preview | `https://eu.i.posthog.com` |
| `NEXT_PUBLIC_API_URL` | Prod | `https://api.mealplanner.fr` |
| `NEXT_PUBLIC_API_URL` | Preview | `https://api-staging.mealplanner.fr` |
| `NEXT_PUBLIC_SENTRY_DSN` | Prod + Preview | DSN Sentry projet web |
| `NEXT_PUBLIC_FLAGSMITH_ENV_KEY` | Prod | Clé env Production Flagsmith |
| `NEXT_PUBLIC_FLAGSMITH_ENV_KEY` | Preview | Clé env Staging Flagsmith |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Prod | `pk_live_...` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Preview | `pk_test_...` |

#### Variables serveur (non exposées — Route Handlers Next.js uniquement)

| Variable | Env | Description |
|----------|-----|-------------|
| `SENTRY_AUTH_TOKEN` | Prod + Preview | Upload source maps (CI) |
| `SENTRY_ORG` | Prod + Preview | Organisation Sentry |
| `SENTRY_PROJECT` | Prod + Preview | Projet Sentry `web` |

#### Note sur les secrets

Les secrets (API keys sensibles) ne passent PAS par Vercel directement.
En Phase 0 : les stocker dans Doppler et utiliser l'intégration Doppler → Vercel
(Doppler Dashboard > Integrations > Vercel) pour la synchronisation automatique.

---

## 3. Domaines custom

### Configuration DNS (dans Cloudflare ou votre registrar)

```
app.mealplanner.fr    CNAME  cname.vercel-dns.com
staging.mealplanner.fr CNAME  cname.vercel-dns.com
www.mealplanner.fr    CNAME  cname.vercel-dns.com  (redirect vers app.)
```

### Assignation dans Vercel (Settings > Domains)

| Domaine | Branche | Environment |
|---------|---------|-------------|
| `app.mealplanner.fr` | `main` | Production |
| `staging.mealplanner.fr` | `staging` | Preview fixe |
| `www.mealplanner.fr` | `main` | Production (redirect) |

**Phase 0 :** Les domaines custom nécessitent un plan Pro (20 $/mois).
En Phase 0, utiliser les URLs Vercel générées (`mealplanner-web.vercel.app`).

---

## 4. Preview Deployments

### Configuration recommandée

- **Automatic Preview Deployments** : Activé pour toutes les branches
- Chaque PR reçoit une URL unique : `mealplanner-web-git-<branch>-<org>.vercel.app`
- Commentaire automatique sur la PR avec le lien de preview
- Les previews utilisent les variables `Preview` (mode test Stripe, Flagsmith staging)

---

## 5. Analytics et Speed Insights

Activer dans le dashboard Vercel :
- **Vercel Analytics** : mesure les Core Web Vitals en production (gratuit avec Hobby)
- **Speed Insights** : temps de réponse des pages

Ces métriques complètent PostHog (analytics produit) et Sentry (erreurs).

---

## 6. Configuration `next.config.ts`

```typescript
// apps/web/next.config.ts
// Configuration Next.js pour Vercel + PWA + sécurité
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Headers de sécurité (CSP, HSTS, etc.)
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ]
  },

  // Redirect www → app
  async redirects() {
    return [
      {
        source: '/',
        destination: '/planner',
        permanent: false,
        has: [{ type: 'host', value: 'app.mealplanner.fr' }],
      },
    ]
  },

  // Images : autoriser Cloudflare R2 comme source
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.r2.cloudflarestorage.com',
      },
    ],
  },

  // Source maps en production pour Sentry
  productionBrowserSourceMaps: true,
}

export default nextConfig
```

---

## 7. Intégration Doppler → Vercel

Une fois Doppler configuré (livrable 11), synchroniser automatiquement les secrets :

1. Doppler Dashboard > Integrations > Add Integration > Vercel
2. Connecter votre compte Vercel
3. Mapper : `prod` Doppler → `Production` Vercel
4. Mapper : `staging` Doppler → `Preview` Vercel
5. Activer la synchronisation automatique

Chaque mise à jour d'un secret dans Doppler déclenche un redéploiement Vercel.
