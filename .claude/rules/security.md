# Security Rules — Presto (MealPlanner SaaS)

> Règles de sécurité appliquées automatiquement. Chargées par Claude Code à chaque session.

---

## Multi-tenancy & Isolation des données

- **RLS Supabase obligatoire** : chaque nouvelle table DOIT avoir `FORCE ROW LEVEL SECURITY` activé
- Chaque requête SQL DOIT filtrer par `household_id` ou `user_id` — jamais d'accès cross-tenant
- Les policies RLS doivent être testées : un utilisateur ne peut JAMAIS voir les données d'un autre tenant
- Les migrations Alembic qui touchent des tables avec données utilisateur DOIVENT inclure les policies RLS

## Stripe & Paiements

- JAMAIS stocker de données de carte en clair — Stripe gère tout via Checkout Sessions
- Valider les webhooks Stripe avec `stripe.Webhook.construct_event()` et la signature
- Tester TOUS les scénarios webhook en staging : `checkout.session.completed`, `invoice.payment_failed`, `customer.subscription.updated`
- Les montants sont TOUJOURS en centimes côté API (Stripe convention)
- Vérifier l'idempotence des webhooks (re-delivery safe)

## Authentification Supabase

- Toujours valider le JWT côté serveur (FastAPI dependency `get_current_user`)
- Ne jamais exposer la `service_role` key côté client — uniquement `anon` key
- Les routes API protégées DOIVENT vérifier `Authorization: Bearer <token>`
- RBAC : vérifier les permissions par rôle (owner, admin, member) sur chaque endpoint

## Secrets & Environment

- JAMAIS de secrets dans le code — utiliser les variables d'environnement
- `.env.local` est gitignored — ne jamais le committer
- En production : secrets via Railway/Vercel environment variables
- `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` = ultra-sensibles

## Validation des entrées

- Côté API : Pydantic models pour TOUTE validation d'entrée (jamais de dict brut)
- Côté frontend : validation Zod/React Hook Form AVANT envoi, mais re-valider côté serveur
- SQL : TOUJOURS des requêtes paramétrées via SQLAlchemy ORM — jamais de f-string SQL
- Upload fichiers : valider le type MIME, la taille, et scanner le contenu

## Headers de sécurité

- CSP configuré dans `next.config.mjs` — ne pas l'affaiblir sans raison documentée
- CORS : whitelist explicite des origines autorisées (pas `*` en production)
- HSTS activé en production
- X-Frame-Options: DENY

## Logging sécurité

- Logger les échecs d'authentification avec IP et user-agent
- Logger les accès aux données sensibles (profil, paiement, subscription)
- JAMAIS logger de données sensibles (mots de passe, tokens, numéros de carte, PII)
- Correlation ID sur chaque requête pour le tracing

## Fichiers nécessitant une review sécurité

Toute modification à ces chemins doit être vérifiée pour les implications sécurité :

- `apps/api/src/core/security.py`
- `apps/api/src/core/stripe_config.py`
- `apps/api/src/api/v1/webhooks*`
- `apps/web/src/middleware.ts`
- `apps/web/src/lib/auth*`
- `packages/db/src/**/models.py` (policies RLS)
- `**/alembic/versions/*.py` (migrations)
