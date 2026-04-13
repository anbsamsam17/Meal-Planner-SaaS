---
project: "MealPlanner SaaS"
domain: "saas"
type: "context"
created: "2026-04-11"
tags: [project/mealplanner-saas, domain/saas, memory/context]
links:
  - "[[memory/MOC]]"
  - "[[memory/primer]]"
  - "[[memory/session-context]]"
  - "[[CLAUDE]]"
---

# Project Context — MealPlanner SaaS

> Fichier de contexte persistant. Mets-le à jour à chaque décision architecturale majeure.
> Ce fichier est lu automatiquement par GitHub Copilot pour contextualiser ses réponses.

---

## Description du projet
**Nom** : MealPlanner SaaS
**Domaine** : SaaS / B2B 📊
**Date de démarrage** : 2026-04-11

**Objectif initial** :
# FICHIER DE RÉFÉRENCE OBLIGATOIRE

Un fichier `ROADMAP.md` est disponible dans les fichiers de ce Project Claude.
**Tu dois le lire intégralement avant d'entreprendre toute tâche.**
Il contient la source de vérité du projet : vision produit, architecture des agents, phases de développement, stack t...

---

## Informations à compléter (important !)
- [ ] Nombre d'utilisateurs / tenants attendus (mois 1, mois 12) ?
- [ ] Plans tarifaires (Free, Pro, Enterprise) ?
- [ ] Intégrations tierces prioritaires (Slack, CRM, webhooks) ?
- [ ] SLA requis par les clients enterprise ?

---

## Stack technique
- React / Next.js (dashboard frontend)
- Node.js ou Python FastAPI (backend)
- PostgreSQL + Redis (données + cache)
- Stripe Billing (abonnements et facturation)
- PostHog / Mixpanel (analytics produit)
- Datadog / Sentry (monitoring et erreurs)

## Architecture
<!-- Décris l'architecture choisie après les premières décisions -->

| Couche | Choix | Justification |
|--------|-------|---------------|
| Frontend | [À définir] | |
| Backend | [À définir] | |
| Base de données | [À définir] | |
| Authentification | [À définir] | |
| Stockage fichiers | [À définir] | |
| Déploiement | Railway (API + Worker) + Vercel (Frontend) | Déploiement rapide depuis GitHub, support Dockerfile monorepo, plugin Redis intégré Railway |
| CI/CD | GitHub Actions (à configurer) + scripts/deploy-check.sh | Script pré-déploiement local — pipeline CI à brancher sur les push tags |

---

## Fonctionnalités principales
<!-- Liste les features planifiées avec leur état -->
- [ ] [Feature 1 — À définir]
- [ ] [Feature 2 — À définir]
- [ ] [Feature 3 — À définir]

---

## Décisions techniques clés
<!-- Documente chaque décision importante : pourquoi ce choix, quelles alternatives ont été écartées -->

| Date | Décision | Raison | Alternatives écartées |
|------|----------|--------|----------------------|
| 2026-04-11 | Initialisation du projet | Setup initial | — |
| 2026-04-12 | Embedding 384 dims (all-MiniLM-L6-v2) | Coût zéro, conforme ROADMAP | OpenAI 1536 dims (payant) |
| 2026-04-12 | recipe_embeddings table séparée | Ne pas pénaliser les requêtes sans similarité | Colonne inline dans recipes |
| 2026-04-12 | FORCE ROW LEVEL SECURITY sur toutes les tables tenant-scoped | Sécurité défensive, propriétaire Supabase (postgres) ne bypass pas RLS | RLS simple sans FORCE |
| 2026-04-12 | 04-triggers-functions avant 03-rls-policies dans l'ordre d'exécution | get_current_household_id() est une dépendance des policies | Ordre naturel des fichiers |
| 2026-04-12 | Stub subscriptions créé en Phase 0 | Éviter migration breaking au passage Phase 3 Stripe | Créer la table en Phase 3 uniquement |
| 2026-04-12 | packages/db partagé (ré-exports) plutôt que copie dans worker | Source de vérité unique, pas de maintenance double, cohérence lors des migrations | Copier les modèles dans apps/worker/src/db/ (maintenance double) |
| 2026-04-12 | AsyncAnthropic dans les coroutines async | Evite le blocage event loop 1-10s par appel Claude | Client sync Anthropic dans coroutines async |
| 2026-04-12 | pgvector dedup : ORDER BY + LIMIT, filtrage seuil en Python | Active l'index HNSW (15-40ms) vs scan séquentiel 76MB (80-400ms) | WHERE distance >= threshold dans la requête SQL |
| 2026-04-12 | difficulty échelle 1-5 (very_easy→very_hard) | Cohérence UX, mapping 5 niveaux standard | 1-3 initial (insuffisant pour recettes française) |
| 2026-04-12 | Gemini 2.0 Flash remplace Anthropic claude-sonnet-4-6 pour RECIPE_SCOUT | Propriétaire a abonnement Claude Max ($180/mois) — évite double facturation API Anthropic. Gemini free tier (15 req/min) suffisant pour batch nocturne. | Garder Anthropic (coût), OpenAI (même problème) |
| 2026-04-12 | WeasyPrint + Jinja2 pour BOOK_GENERATOR | CSS inline obligatoire (pas de fichiers CSS externes, pas de Google Fonts), rendu headless sans navigateur, < 1.5s p50. | Puppeteer/Playwright (lourd), wkhtmltopdf (déprécié) |
| 2026-04-12 | MinIO (dev) + Cloudflare R2 (prod) via boto3 S3-compatible | Protocole S3 unifié — un seul client boto3, switch via STORAGE_BACKEND env var. | AWS S3 (coût), GCS (couplage Google) |
| 2026-04-12 | Stripe Checkout + Customer Portal + webhooks pour la monétisation | Stripe gère PCI compliance, adresse de facturation, taxes UE. Mode test sk_test_... complet. | Paddle (moins connu), LemonSqueezy (Phase 3) |
| 2026-04-12 | require_plan() factory FastAPI pour les endpoints premium | Pattern dependency injection propre, testable unitairement, extensible à N plans. | Middleware global (trop large), décorateur custom (hors standards FastAPI) |
| 2026-04-12 | Railway (backend) + Vercel (frontend) comme plateforme de déploiement | Railway supporte Dockerfile monorepo avec build context racine, Vercel détecte pnpm et Next.js standalone automatiquement. Permet déploiement en 10-15 min sans configuration complexe. | AWS ECS (complexité), GCP Cloud Run (config manuelle), Fly.io (moins adapté pnpm monorepo) |
| 2026-04-12 | railway.toml à la racine + vercel.json dans apps/web | Versionner les configs de déploiement dans le repo garantit la reproductibilité et l'auditabilité des déploiements. | Dashboard-only (pas versionné, pas auditable) |

---

## Préoccupations domaine-spécifiques
- Onboarding utilisateur (time-to-value)
- Taux de churn et rétention
- Performance et scalabilité multi-tenant
- Isolation stricte des données entre tenants
- Intégrations tierces (Slack, Salesforce, Zapier)
- Feature flags pour déploiements progressifs

---

## Contraintes et limites connues
- [À documenter au fur et à mesure]

---

## Équipe
- **Développeur(s)** : [À renseigner]
- **Date cible de livraison** : [À définir]
- **Environnements** : dev / staging / production
