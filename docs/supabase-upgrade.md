# Supabase — Plan Free vs Pro : quand migrer ?

> FIX Phase 1 (review 2026-04-12) : BUG #6 — pool_size=10 + max_overflow=20 x 2 workers uvicorn
> = 60 connexions. Supabase Free = 60 connexions max. Le worker Celery depasse ce seuil.

---

## Limites Supabase Free

| Ressource | Free | Pro ($25/mois) |
|-----------|------|----------------|
| Connexions PostgreSQL | **60 max** | **200 max** |
| Compute | Shared / nano | Dedicated 2 vCPU + 4 GB RAM |
| Backup | Aucun (PITR desactive) | Backups quotidiens + PITR 7 jours |
| Bande passante | 5 GB/mois | 250 GB/mois |
| Stockage DB | 500 MB | 8 GB |

## Calcul des connexions Presto

```
Environnement dev local (docker-compose) :
  - API FastAPI     : pool_size=10 + max_overflow=20 = 30 connexions max
  - Total           : 30 connexions (OK pour Supabase Free)

Production (Railway, 2 workers uvicorn) :
  - API FastAPI     : 2 workers x 30 connexions = 60 connexions max
  - Worker Celery   : CELERY_CONCURRENCY=4 x 1 connexion = 4 connexions
  - Total           : 60 + 4 = 64 connexions → DEPASSE Supabase Free

Production avec autoscaling (3 workers uvicorn) :
  - API FastAPI     : 3 workers x 30 connexions = 90 connexions max
  - Worker Celery   : 4 connexions
  - Total           : 94 connexions → necessite Supabase Pro
```

## Declencheurs de migration vers Supabase Pro

Migrer immediatement si l'un de ces signaux est presente :

1. **Worker Celery actif en parallele de l'API en production**
   → Les 60 connexions Free sont saturees au premier batch nocturne

2. **Plus de 10 000 recettes embeddees**
   → Charge memoire + requetes pgvector plus frequentes

3. **WEB_CONCURRENCY >= 3** (Railway autoscaling active)
   → 3 x 30 = 90 connexions, au-dela du seuil Free

4. **Erreur "remaining connection slots reserved"** dans les logs Sentry
   → Seuil atteint, migration urgente

## Verification des connexions actives

Commande a lancer dans le Supabase Dashboard → SQL Editor :

```sql
-- Connexions actives par application
SELECT
  application_name,
  state,
  count(*) AS connexions
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY application_name, state
ORDER BY connexions DESC;

-- Connexions totales vs maximum configure
SELECT
  count(*) AS connexions_actives,
  (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connexions
FROM pg_stat_activity;
```

## Procedure de migration Free → Pro

1. Aller sur https://supabase.com/dashboard → votre projet → Settings → Billing
2. Cliquer "Upgrade to Pro" → $25/mois
3. Aucune action technique requise : les connexions max passent de 60 a 200 automatiquement
4. Verifier apres upgrade :
   ```sql
   SHOW max_connections;
   -- Doit retourner 200
   ```
5. Ajuster optionnellement `pool_size` et `max_overflow` dans `.env.local` pour profiter
   des 200 connexions disponibles (par exemple pool_size=20, max_overflow=40 si 3+ workers)

## Documentation Supabase

- Pricing : https://supabase.com/pricing
- Connexions DB : https://supabase.com/docs/guides/database/connecting-to-postgres
- pgBouncer (mode transaction) : https://supabase.com/docs/guides/database/connection-pooling
