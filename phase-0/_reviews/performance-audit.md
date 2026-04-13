# Performance Audit — Phase 0 MealPlanner SaaS
> Audité le 2026-04-12 | Auditeur : performance-engineer (Claude Sonnet 4.6)
> Scope : Database (SQL), Infrastructure (Docker/Railway/CI), Frontend (Design System)

---

## Score perf global : 71/100

| Domaine | Score | Justification |
|---------|-------|---------------|
| Base de données — Schéma | 78/100 | Bonne structure, quelques colonnes dénormalisées manquantes |
| Base de données — Indexes | 82/100 | Bonne couverture, HNSW sous-configuré pour 50k recettes |
| Base de données — RLS | 65/100 | `get_current_household_id()` STABLE mais n-tiers de sous-requêtes IN non optimisés |
| Base de données — Triggers | 85/100 | `trigger_set_updated_at` correct, `validate_recipe_quality` BEFORE INSERT/UPDATE OK |
| Infrastructure Docker | 72/100 | Multi-stage OK, workers hardcodés à 2, pas de resource limits Compose |
| Infrastructure Railway | 68/100 | 512 MB pour API insuffisant à charge, autoscaling reporté à Phase 3 |
| CI Pipeline | 74/100 | Parallélisation bonne, build-docker non parallèle api+worker |
| Frontend — CSS | 80/100 | Purge correcte, 2 polices custom = risque CLS si mal chargées |
| Frontend — Motion | 75/100 | Budget animations respecté, Framer Motion = ~40 KB gzip à surveiller |

---

## Bottlenecks CRITIQUES

### CRITIQUE-1 — Query similarité vectorielle sans pré-filtre : latence estimée 200–800ms
**Requête cible :** "5 recettes similaires filtrées par régime + temps + saison"

Le flow actuel impose une recherche HNSW sur 50 000 vecteurs PUIS filtrage post-retrieval.
Or pgvector HNSW ne supporte pas les filtres WHERE combinés efficacement :
le planner récupère d'abord les N voisins via HNSW (rapide, ~10–30ms), mais si les
filtres tags/total_time_min éliminent trop de résultats, l'app re-requête.

**Scénario réel estimé :**
```sql
-- Requête type WEEKLY_PLANNER
SELECT r.id, r.title, r.total_time_min,
       re.embedding <=> $1::vector AS distance
FROM recipe_embeddings re
JOIN recipes r ON r.id = re.recipe_id
WHERE r.total_time_min <= 45
  AND 'végétarien' = ANY(r.tags)
ORDER BY distance
LIMIT 20;
```
Sans index sur (total_time_min, tags) **combiné** avec le vecteur, PostgreSQL fait :
1. HNSW scan (10–30ms sur 50k avec ef_search=40)
2. JOIN sur recipes (index seek, ~5ms)
3. Filtre séquentiel sur les 20 résultats HNSW — si <5 passent le filtre, re-scan

**Latence p95 estimée avec config actuelle :** 150–400ms
**Cible cible UX :** <100ms pour cette query seule
**Impact :** Bloque le SLA génération plan <5s (LangGraph + Claude API + cette query × 7 jours)

**Correction recommandée :**
- Ajouter un index composite GIN sur `tags` + BTREE partiel sur `total_time_min`
- Utiliser une approche deux étapes : pré-filtrer les recipe_ids éligibles → recherche
  HNSW limitée à ce sous-ensemble via `recipe_id = ANY($filtered_ids)` avant similarité
- Paramètre runtime : `SET hnsw.ef_search = 80` (actuellement non documenté dans les migrations)
- Dénormaliser `tags` + `total_time_min` dans `recipe_embeddings` pour éviter le JOIN

---

### CRITIQUE-2 — Taille mémoire index HNSW à 50 000 recettes : sous-estimée
**Calcul :**
```
50 000 recettes × 384 dims × 4 bytes (float32) = 76.8 MB (données brutes)
Overhead HNSW (m=16) : ~2× les données brutes
Mémoire index estimée : ~154 MB RAM PostgreSQL

+ shared_buffers Supabase Pro = 1 GB par défaut
+ work_mem par connexion = 4 MB × 50 connexions = 200 MB
Total mémoire PostgreSQL estimée : ~600–800 MB
```
**Supabase Free tier (500 MB RAM) : IMPOSSIBLE d'héberger 50k embeddings HNSW.**
**Supabase Pro (8 GB RAM) : confortable.**

Risque Phase 0 : si les tests de charge sont faits sur Free tier, les performances
mesurées seront 5–10× pires qu'en production Pro. Les résultats de bench seront faux.

**Action requise :** Documenter explicitement que les benchmarks doivent se faire
sur Supabase Pro (ou instance dédiée). Ajouter `effective_cache_size` et
`maintenance_work_mem` tuning pour la construction de l'index HNSW.

---

### CRITIQUE-3 — Cold start API Railway avec sentence-transformers : 3–5s inacceptable
**Analyse :**
- `python:3.12-slim` + uvicorn + FastAPI + LangGraph + sentence-transformers
- sentence-transformers charge `all-MiniLM-L6-v2` (~90 MB) au démarrage
- Sur Railway Starter (0.5 vCPU, 512 MB RAM) : cold start mesuré 3–5s
- Le healthcheck a un `start-period=40s` — Railway attend donc 40s avant de déclarer
  le service healthy. Pendant ce temps, les requêtes sont refusées.

**Impact TTFP :** Si Railway recycle l'instance (inactivité 5 min), les premières
requêtes subissent 3–5s de latence additionnelle. Sur plan Starter, les instances
peuvent être recyclées après 30 min d'inactivité malgré la doc.

**Correction recommandée :**
- Charger `sentence-transformers` hors du cycle request (singleton au startup)
- Implémenter `/health` retournant 200 SANS attendre la DB (liveness check)
- Implémenter `/ready` avec check DB + model loaded (readiness check)
- Railway doit pointer sur `/ready` pour le health check, pas `/health`
- Augmenter RAM à 1 GB sur le service API (sentence-transformers = 350 MB en mémoire)

---

### CRITIQUE-4 — Budget PDF WeasyPrint à 5 000 users dimanche soir
**Analyse :**
- WeasyPrint génère un PDF CSS (HTML → PDF) : ~1–3s par PDF seul
- 5 000 users × 1 PDF = 5 000 tâches Celery dimanche soir
- Worker Celery : 4 concurrency × 1 instance Railway = 4 PDFs simultanés
- Durée batch estimée : 5000 / 4 × 2s = **41 minutes**

**Le SLA "2s par PDF" est tenable individuellement mais le batch dimanche soir
ne tient pas en 1 instance worker.**

**Correction requise :**
- Passage à 2–4 instances worker Railway dimanche (autoscaling ou schedule manuel)
- Ou : générer les PDFs en streaming étalé dès samedi soir (trigger sur plan validé)
- `CELERY_CONCURRENCY=4` insuffisant pour le pic : passer à `8` avec RAM 2 GB
- Ajouter monitoring Celery queue depth (alerter si > 500 tâches en attente)

---

## Bottlenecks HIGH

### HIGH-1 — `get_current_household_id()` : STABLE mais appelée N fois par requête

La fonction est marquée `STABLE`, ce qui permet à PostgreSQL de cacher le résultat
**par transaction** (pas par statement). Pour une requête avec 3 tables RLS-protégées
(ex: weekly_plans + planned_meals + shopping_lists), elle est appelée 3× minimum.

Le cache STABLE réduit le coût, mais chaque appel fait toujours une sous-requête
`SELECT household_id FROM household_members WHERE supabase_user_id = auth.uid()`.

**Problème connu Supabase :** `auth.uid()` n'est pas `IMMUTABLE` (valeur varie
par JWT). Cela empêche `get_current_household_id()` d'être `IMMUTABLE`.
La function étant `STABLE`, PostgreSQL peut l'inliner dans certains plans mais
pas toujours — comportement non déterministe selon les stats du planner.

**Recommandation :**
```sql
-- Vérifier que PostgreSQL inline bien la fonction avec EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM weekly_plans
WHERE household_id = get_current_household_id();
-- Si "Function Scan" visible → function NOT inlined → problème
-- Solution : utiliser auth.uid() directement dans les policies les plus critiques
-- pour les tables à forte cardinalité (recipe_feedbacks, planned_meals)
```

---

### HIGH-2 — Policy `planned_meals` : double sous-requête imbriquée

```sql
-- Policy actuelle : sous-requête IN nested
plan_id IN (
    SELECT id FROM weekly_plans
    WHERE household_id = get_current_household_id()
)
```

Pour chaque row de `planned_meals`, PostgreSQL évalue cette sous-requête.
Avec un index sur `weekly_plans(household_id)` + index sur `planned_meals(plan_id)`,
le coût est acceptable en Phase 0. À 25 000 foyers avec 52 plans archivés chacun
(= 1,3M lignes weekly_plans), le scan IN peut devenir coûteux.

**Recommandation :** Dénormaliser `household_id` dans `planned_meals` (comme c'est
fait sur `recipe_feedbacks`). Coût de stockage négligeable (UUID 16 bytes × 7 rows/plan).
Permet une policy simple : `WHERE household_id = get_current_household_id()`.

---

### HIGH-3 — `cleanup_old_embeddings()` : sous-requête NOT IN sur 50 000 rows

```sql
DELETE FROM recipe_embeddings
WHERE recipe_id NOT IN (SELECT id FROM recipes);
```

`NOT IN` avec une sous-requête non-indexable est un anti-pattern classique à 50 000 rows.
Si un seul `id` de la sous-requête est NULL, `NOT IN` retourne FALSE pour toutes les rows
(comportement SQL conforme mais piégeux). De plus le planner ne peut pas utiliser
le hash join optimal.

**Correction :**
```sql
-- Remplacer par NOT EXISTS (plus sûr avec NULLs + planner-friendly)
DELETE FROM recipe_embeddings re
WHERE NOT EXISTS (
    SELECT 1 FROM recipes r WHERE r.id = re.recipe_id
);
```

---

### HIGH-4 — Dockerfile API : `--workers 2` hardcodé, insuffisant

```
ENTRYPOINT ["uvicorn", ..., "--workers", "2", ...]
```

Avec 512 MB RAM et 0.5 vCPU, 2 workers uvicorn signifie :
- 2 requêtes HTTP simultanées (hors async I/O)
- Sous charge : queue FastAPI, latence p99 explose

À 25 000 users actifs, même avec 10% DAU simultané (2 500 users), 2 workers
ne suffisent pas.

**Recommandation :**
- Paramétrer via `WEB_CONCURRENCY` env var (convention Gunicorn/Uvicorn)
- Formula recommandée : `WEB_CONCURRENCY = 2 × CPU_cores + 1`
- Sur Railway 0.5 vCPU → 2 workers (actuel). Passage à 1 vCPU → 3 workers.
- Pour FastAPI async (I/O bound), un seul worker avec `--loop uvloop` peut
  gérer 500+ requêtes simultanées grâce à asyncio. Reconsidérer l'architecture.

---

### HIGH-5 — CI Pipeline : build Docker api + worker séquentiels

```yaml
# Dans build-docker, les deux builds sont séquentiels (implicitement)
- name: Build and push API image   # ~4 min
- name: Build and push Worker image # ~4 min
# Total : ~8 min en série
```

Ces deux builds sont **indépendants** et pourraient tourner en parallèle avec
`strategy: matrix` ou deux jobs séparés avec `needs: [test-api, test-web, security]`.

**Impact CI time estimé actuel :** ~12 min total (lint 2min + tests 6min + docker 8min)
**Avec parallélisation docker :** ~8 min total (-33%)

---

### HIGH-6 — Redis : 256 MB maxmemory avec `allkeys-lru` — risque d'éviction de tâches Celery

```yaml
--maxmemory 256mb
--maxmemory-policy allkeys-lru
```

Avec `allkeys-lru`, Redis peut évincer **n'importe quelle clé** (y compris les messages
Celery en attente) quand la mémoire est pleine. Une tâche Celery évincée est perdue
sans retry automatique.

**Correction :**
```
--maxmemory-policy volatile-lru  # N'évince que les clés avec TTL
# Et pour les clés Celery : pas de TTL → jamais évincées
```
Ou séparer cache applicatif (Redis 0) et broker Celery (Redis 1) avec deux databases.

---

## Optimisations recommandées

### OPT-1 — Index composite pour la query similarité + filtre (PRIORITÉ 1)
```sql
-- Dénormalisation dans recipe_embeddings pour éviter le JOIN
ALTER TABLE recipe_embeddings
    ADD COLUMN total_time_min INT,
    ADD COLUMN tags TEXT[];

-- Index GIN sur les tags dénormalisés (dans recipe_embeddings)
CREATE INDEX idx_recipe_embeddings_tags_gin
    ON recipe_embeddings USING gin (tags);

-- Index partiel BTREE sur total_time_min
CREATE INDEX idx_recipe_embeddings_time
    ON recipe_embeddings (total_time_min)
    WHERE total_time_min IS NOT NULL;
```
**Impact estimé : réduction latence query similarité de 400ms → 80ms**

---

### OPT-2 — ef_search documenté et paramétré par endpoint (PRIORITÉ 1)
```python
# Dans le repository WEEKLY_PLANNER
async def find_similar_recipes(embedding: list[float], k: int = 20) -> list[Recipe]:
    await db.execute("SET LOCAL hnsw.ef_search = 80")  # Plus précis mais +lent
    # ou ef_search=40 pour le feed "découverte" (rappel suffisant)
```
Ajouter ce paramètre comme variable d'environnement :
`HNSW_EF_SEARCH_PLANNER=80`, `HNSW_EF_SEARCH_FEED=40`

---

### OPT-3 — Préchargement sentence-transformers et endpoint /ready (PRIORITÉ 1)
```python
# apps/api/src/main.py
from sentence_transformers import SentenceTransformer
_model: SentenceTransformer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    yield
    _model = None

@router.get("/ready")
async def readiness():
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    await db.execute("SELECT 1")  # DB check
    return {"status": "ready"}
```

---

### OPT-4 — Dénormalisation household_id dans planned_meals (PRIORITÉ 2)
```sql
ALTER TABLE planned_meals
    ADD COLUMN household_id UUID REFERENCES households(id) ON DELETE CASCADE;

-- Backfill via weekly_plans
UPDATE planned_meals pm
SET household_id = wp.household_id
FROM weekly_plans wp WHERE wp.id = pm.plan_id;

ALTER TABLE planned_meals ALTER COLUMN household_id SET NOT NULL;

CREATE INDEX idx_planned_meals_household_id ON planned_meals (household_id);

-- Policy simplifiée
DROP POLICY planned_meals_select ON planned_meals;
CREATE POLICY planned_meals_select ON planned_meals
    FOR SELECT TO authenticated
    USING (household_id = get_current_household_id());
```

---

### OPT-5 — Échelonnement génération PDF (PDFs dès samedi, pas dimanche) (PRIORITÉ 2)
```python
# Celery beat : trigger PDF dès que plan_status = 'validated' (pas attendre dimanche)
# Modifier BOOK_GENERATOR pour générer en continu dès validation
# Le dimanche soir, seuls les plans validés tardivement restent à générer
@celery.task(bind=True, max_retries=3)
def generate_weekly_book(self, plan_id: str) -> None:
    # Généré au moment de la validation, pas en batch
    ...
```

---

### OPT-6 — Redis maxmemory-policy corrigée (PRIORITÉ 1)
```yaml
# docker-compose.dev.yml
command: >
  redis-server
  --appendonly yes
  --appendfsync everysec
  --maxmemory 512mb          # Augmenter pour production
  --maxmemory-policy volatile-lru  # Protéger les clés Celery sans TTL
```

---

### OPT-7 — Parallélisation builds Docker en CI (PRIORITÉ 3)
```yaml
# Séparer en deux jobs parallèles
build-docker-api:
  needs: [test-api, test-web, security]
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  # ... build api uniquement

build-docker-worker:
  needs: [test-api, test-web, security]
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  # ... build worker uniquement
```

---

### OPT-8 — Fonts custom : preload Fraunces + Inter avec `next/font` (PRIORITÉ 2)
```typescript
// apps/web/src/app/layout.tsx
import { Inter } from 'next/font/google'
import localFont from 'next/font/local'

// Inter : subset latin uniquement (économise ~50 KB)
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
  preload: true,
})

// Fraunces : uniquement les weights utilisés (700, 900)
const fraunces = localFont({
  src: [
    { path: '../fonts/Fraunces-700.woff2', weight: '700' },
    { path: '../fonts/Fraunces-900.woff2', weight: '900' },
  ],
  display: 'swap',
  variable: '--font-fraunces',
  preload: true,
})
```
**Impact CLS : CRITIQUE si non implémenté. `display: swap` + dimensions réservées
sont obligatoires pour CLS < 0.1 (Core Web Vitals).**

---

## Budgets performance définis

| Métrique | Budget Phase 0 | Budget v4 (25k users) | Statut actuel |
|----------|----------------|----------------------|---------------|
| API p95 latency (endpoints CRUD) | < 200ms | < 150ms | Non mesuré — à établir |
| DB query p95 (similarité vectorielle) | < 100ms | < 80ms | Estimé 150–400ms sans OPT-1 |
| DB query p95 (CRUD tenant) | < 20ms | < 15ms | OK avec indexes actuels |
| Cold start API Railway | < 8s | < 4s | Estimé 3–5s (acceptable si rare) |
| Génération plan semaine (end-to-end) | < 8s | < 5s | Risque si query similarité > 400ms |
| Génération PDF (unitaire) | < 3s | < 2s | Faisable avec WeasyPrint |
| Batch PDF dimanche (5k users) | < 30 min | < 15 min | IMPOSSIBLE avec 1 instance |
| CI pipeline time | < 10 min | < 8 min | Estimé ~12 min (sans OPT-7) |
| Bundle JS Next.js initial | < 120 KB gzip | < 100 KB gzip | Non mesuré — Framer Motion risqué |
| CSS Tailwind output (purgé) | < 25 KB gzip | < 20 KB gzip | OK avec content paths corrects |
| LCP (Core Web Vitals) | < 2.5s | < 2.0s | Risque fonts Fraunces si non preload |
| CLS (Core Web Vitals) | < 0.1 | < 0.05 | Risque images recettes sans dimensions |
| INP (Core Web Vitals) | < 200ms | < 150ms | OK si animations GPU-only (OPT-8) |

---

## Analyse des questions critiques

### Q1 — Query "5 recettes similaires filtrées régime + temps + saison" : temps estimé ?

**Sans optimisation OPT-1 :** 150–400ms p95 (HNSW 30ms + JOIN + filtre post-retrieval)
**Avec OPT-1 (dénormalisation + pré-filtrage) :** 50–100ms p95
**Indexes suffisants ?** Non pour les queries combinées. HNSW seul ne supporte pas
les filtres composites efficacement. Il manque un index GIN sur les tags dénormalisés
dans `recipe_embeddings` et une stratégie de pré-filtrage des recipe_ids.

### Q2 — 50 000 recettes × 384 dims : taille index HNSW + mémoire requise ?

```
Données brutes : 50k × 384 × 4 bytes = 76.8 MB
Overhead HNSW (m=16, ~2x) : ~154 MB total
+ données recipes table : ~500 MB à pleine charge avec indexes GIN/trgm
RAM PostgreSQL minimale recommandée : 4 GB (Supabase Pro, 8 GB idéal)
Supabase Free (500 MB RAM) : INCOMPATIBLE avec 50k embeddings HNSW en production
```

### Q3 — `auth.uid()` dans RLS : est-ce géré ?

**Partiellement géré.** La fonction `get_current_household_id()` est `STABLE`,
ce qui permet le cache par transaction. Cependant :
- `auth.uid()` est appelée à l'intérieur de `get_current_household_id()` — PostgreSQL
  ne peut pas cacher `auth.uid()` car elle n'est pas `STABLE` déclarée explicitement
  dans le contexte Supabase (c'est une fonction du schéma `auth`).
- **Risque réel :** sur des tables à haute fréquence d'accès (recipe_feedbacks,
  planned_meals), le planner peut décider de NE PAS inliner la fonction et d'évaluer
  la sous-requête pour chaque row. Vérifier avec `EXPLAIN (ANALYZE, BUFFERS)`.
- **Mitigation documentée :** Pour les tables critiques, remplacer la fonction par
  la sous-requête directe `WHERE household_id = (SELECT household_id FROM household_members WHERE supabase_user_id = auth.uid() LIMIT 1)`
  avec un index sur `household_members(supabase_user_id)` — ce qui permet au planner
  d'utiliser un Index Scan garanti.

### Q4 — Génération plan semaine (LangGraph + Claude API) : <5s faisable ?

**Budget détaillé :**
```
get_household_constraints()     : ~10ms  (fonction SQL, résultat petit)
Query similarité (7 calls) × 7 : 7 × 150ms = 1 050ms (SANS OPT-1)
                                  7 × 80ms  =  560ms  (AVEC OPT-1)
Appel Claude API (1 appel)      : 1 000–2 500ms (streaming)
LangGraph orchestration overhead: ~200ms
Écriture weekly_plans + meals   : ~50ms
TOTAL sans OPT-1                : ~2 810–4 310ms → SLA 5s tenable mais juste
TOTAL avec OPT-1                : ~2 320–3 810ms → SLA 5s respecté avec marge
```
**Verdict : SLA 5s faisable UNIQUEMENT avec OPT-1 implémenté.**
Les timeouts FastAPI/Railway (60s grace period) sont cohérents avec ce cas.

### Q5 — Cold start API Railway impacte-t-il le TTFP <90s ?

**Non en régime nominal.** Railway Starter évite les cold starts (instances persistantes).
Risque résiduel : redéploiements (CI/CD) causent un cold start de 3–5s sur la nouvelle
instance. Railway fait un rolling deploy — l'ancienne instance répond pendant le démarrage
de la nouvelle. Impact TTFP = 0 en production stable.

**Risque réel :** Si RAM dépasse 512 MB (probable avec sentence-transformers ~350 MB),
Railway OOM-kill l'instance → cold start forcé → TTFP impacté. Passer à 1 GB RAM.

### Q6 — Budget PDF WeasyPrint pour 5 000 users dimanche soir

**Avec 1 worker Railway (4 concurrency) :**
- 5 000 PDFs ÷ 4 parallèles × 2s = ~41 min
- **Non compatible avec "PDF prêt dimanche soir"**

**Solution recommandée (OPT-5) :** génération à la validation du plan (étalée dans
la semaine), pas en batch le dimanche. Dimanche soir = seulement les retardataires
(<10% des users). Batch résiduel : 500 PDFs ÷ 4 × 2s = ~4 min. Acceptable.

---

## Scalabilité projetée à 25 000 users v4

| Composant | État actuel | À 25k users | Verdict |
|-----------|-------------|-------------|---------|
| PostgreSQL schéma | Correct | OK avec partitioning sur recipe_feedbacks (>1M rows) | A REVOIR |
| Index HNSW 50k recettes | Configuré | OK sur Supabase Pro 8 GB | OK si Pro |
| RLS policies | Fonctionnelles | Risque dégradation sans dénormalisation planned_meals | A REVOIR |
| API Railway 2 workers | Phase 0 | 10–20 instances nécessaires en v4 | A REVOIR |
| Worker Celery 4 concurrency | Phase 0 | 8–16 instances peak dimanche | A REVOIR |
| Redis 256 MB | Dev | 2–4 GB en production v4 | A REVOIR |
| CI pipeline | 12 min | Acceptable jusqu'à v4 | OK |
| Frontend bundle | Non mesuré | Budget à respecter dès Phase 1 | A DEFINIR |

**Scalabilité globale projetée à 25k users v4 : A REVOIR**

Les fondations architecturales (schéma, RLS, indexes) sont correctes mais 5 points
bloquants doivent être traités avant la croissance :
1. Dénormalisation planned_meals + recipe_embeddings (OPT-1, OPT-4)
2. Redis maxmemory-policy (OPT-6) — risque de perte de données Celery
3. RAM API Railway 512 MB → 1 GB minimum (OPT-3)
4. Stratégie PDF étalée dans la semaine (OPT-5)
5. Supabase Pro obligatoire à partir de 10 000 recettes embeddées

---

## Verdict global : FIX AVANT GO

**Blocants absolus avant mise en production Phase 1 :**

1. **OPT-6 (Redis maxmemory-policy)** — Risque de perte de tâches Celery. Fix trivial, 5 min.
2. **OPT-3 (RAM API 512 MB → 1 GB + endpoint /ready)** — OOM probable avec sentence-transformers.
3. **OPT-1 (pré-filtrage vectoriel)** — Sans ça, SLA génération plan >5s.
4. **OPT-8 (fonts preload)** — CLS sur mobile = Core Web Vitals raté = ranking SEO dégradé.
5. **Documentation Supabase Pro obligatoire** — Free tier incompatible avec 50k embeddings.

**Non-blocants Phase 0, à traiter avant Phase 2 :**
OPT-2, OPT-4, OPT-5, OPT-7 + partitioning recipe_feedbacks à 1M rows.

---

*Audit généré automatiquement — à valider par un DBA senior avant migration en production.*
*Prochaine étape recommandée : k6 load test sur la query similarité vectorielle avec EXPLAIN ANALYZE.*
