# apps/web — MealPlanner Frontend

Application Next.js 14 App Router du projet MealPlanner SaaS.

## Stack

- **Next.js 14** App Router (React Server Components par défaut)
- **TypeScript** strict mode
- **Tailwind CSS** + shadcn/ui pattern + Radix UI primitives
- **Framer Motion** (animations)
- **next/font** (Fraunces + Inter + JetBrains Mono)
- **Supabase JS v2** (auth + realtime)
- **TanStack Query v5** (data fetching)
- **Zustand** (state léger client)
- **Zod** (validation)
- **next-pwa** (service worker PWA)
- **next-intl** (i18n FR-first)

## Commandes

```bash
# Installation des dépendances
pnpm install

# Développement local
pnpm dev           # http://localhost:3000

# Build de production
pnpm build

# Démarrer en production
pnpm start

# Vérification TypeScript
pnpm typecheck

# Lint
pnpm lint

# Tests
pnpm test
pnpm test:watch    # Mode watch
pnpm test:coverage # Rapport de couverture
```

## Configuration

1. Copier `.env.example` en `.env.local`
2. Remplir les variables Supabase et API
3. Lancer `pnpm dev`

## Structure

```
src/
├── app/                    # App Router — routes et layouts
│   ├── (app)/              # Routes authentifiées
│   │   ├── dashboard/      # Planning semaine
│   │   └── layout.tsx      # Layout avec nav (sidebar/bottom nav)
│   ├── (onboarding)/       # Flux d'onboarding 3 étapes
│   │   └── onboarding/
│   │       ├── step-1/     # "Votre famille"
│   │       ├── step-2/     # "Restrictions alimentaires"
│   │       └── step-3/     # "Contexte et drive"
│   ├── fonts.ts            # Chargement optimisé next/font (OPT-8)
│   ├── globals.css         # Tokens CSS + styles de base
│   ├── layout.tsx          # Root layout (fonts, metadata, providers)
│   ├── manifest.ts         # PWA manifest
│   ├── page.tsx            # Landing page
│   ├── error.tsx           # Error boundary global
│   ├── loading.tsx         # Loading state global
│   └── not-found.tsx       # Page 404
│
├── components/
│   ├── navigation/
│   │   ├── app-bottom-nav.tsx  # Nav mobile (< lg)
│   │   └── app-sidebar.tsx     # Nav desktop (>= lg)
│   ├── providers/
│   │   ├── query-provider.tsx  # TanStack Query
│   │   ├── supabase-provider.tsx # Supabase browser client
│   │   ├── theme-provider.tsx  # next-themes dark mode
│   │   └── root-providers.tsx  # Composition providers
│   └── ui/                 # Design system components
│       ├── badge.tsx
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── progress.tsx
│       ├── skeleton.tsx
│       └── toast.tsx
│
├── lib/
│   ├── api/
│   │   ├── client.ts       # Client HTTP vers FastAPI
│   │   └── types.ts        # Types API (Recipe, Plan, etc.)
│   ├── supabase/
│   │   ├── client.ts       # Browser client
│   │   ├── server.ts       # Server Components client
│   │   ├── middleware.ts   # Session refresh helper
│   │   └── database.types.ts # Types générés (placeholder)
│   └── utils.ts            # cn(), formatDuration(), etc.
│
├── i18n/
│   ├── config.ts           # next-intl config (FR-first)
│   └── messages/
│       └── fr.json         # Strings françaises
│
└── middleware.ts            # Auth middleware + session refresh
```

## Points d'intégration backend

### Supabase Auth
- **Flow** : magic link ou OAuth Google → JWT → middleware Next.js le valide via `getUser()`
- **Session** : rafraîchie automatiquement par le middleware à chaque requête

### API FastAPI (NEXT_PUBLIC_API_URL)
Endpoints consommés (Phase 1 à implémenter) :
- `GET /api/v1/recipes` — liste des recettes avec filtres
- `POST /api/v1/plans/generate` — générer un plan hebdomadaire
- `GET /api/v1/plans/{id}` — récupérer un plan
- `PATCH /api/v1/plans/{id}/days/{day}` — modifier un repas
- `GET /api/v1/shopping-list/{plan_id}` — liste de courses du plan
- `POST /api/v1/households` — créer le profil foyer (onboarding)

## Décisions techniques (Phase 1)

### Version Next.js : 14.2.18 (pinné)
**Décision (2026-04-12)** : Rester sur Next.js 14.2.x stable pour la Phase 1.
- `next` est pinné sans `^` dans `package.json` pour éviter une montée automatique vers Next 15
- **BREAKING CHANGE Next.js 15** : `cookies()` et `headers()` deviennent asynchrones → `await cookies()`
- Migration Next 15 prévue en **Phase 2** via `npx @next/codemod@canary upgrade`
- Fichiers impactés lors de la migration : `src/lib/supabase/server.ts`, tout Server Component utilisant `cookies()`

### Framer Motion : dynamic import obligatoire
**Règle (2026-04-12)** : Ne pas importer directement depuis `framer-motion` sauf pour les éléments above-the-fold.
- Utiliser `@/components/motion` (wrapper dynamic import SSR: false)
- Gain estimé : -15 à -25 KB gzip sur le bundle initial
- Exception : éléments hero/onboarding step-1 si animations visibles au premier rendu

### next-intl : activé Phase 4 (expansion internationale)
**Décision (2026-04-12)** : next-intl est configuré mais utilisé en mode minimal (FR uniquement).
- Pas de prefixe `/fr/` sur les routes (localePrefix: "as-needed")
- Activation complète prévue en **Phase 4** (expansion Belgique/Suisse selon la ROADMAP)
- Les strings sont dans `src/i18n/messages/fr.json`

### CSP : durcissement Phase 2
**TODO Phase 2** : Remplacer `unsafe-inline` + `unsafe-eval` par des nonces via `strict-dynamic`.
- Next.js 14 supporte les nonces via `generateBuildId` + middleware
- Référence : `next.config.mjs` section `securityHeaders`

### Analytics PostHog : stub Phase 1
**Décision (2026-04-12)** : Helper analytics présent (`src/lib/analytics/posthog.ts`) mais sans SDK.
- Ajouter `pnpm add posthog-js` en Phase 2 avec `NEXT_PUBLIC_POSTHOG_KEY`
- En dev sans clé : logs console structurés

## Liens design system (Phase 0)

- `phase-0/design-system/01-brand-vision.md` — ADN visuel
- `phase-0/design-system/02-design-tokens.md` — Couleurs, typo, espacement
- `phase-0/design-system/03-tailwind-config.ts` — Config Tailwind (copiée dans ce repo)
- `phase-0/design-system/04-components-catalog.md` — 30 composants spécifiés
- `phase-0/design-system/05-motion-principles.md` — Animations Framer Motion
- `phase-0/design-system/06-accessibility.md` — WCAG 2.1 AA
- `phase-0/design-system/07-responsive-breakpoints.md` — Layouts mobile/tablet/desktop
- `phase-0/ux-research/onboarding-protocol.md` — Protocole onboarding 3 étapes
- `phase-0/ux-research/personas.md` — Sophie, Camille & Antoine, Nathalie
