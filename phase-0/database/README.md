# Database Foundation — Phase 0

MealPlanner SaaS · PostgreSQL 16 + pgvector + Supabase

---

## Vue d'ensemble du schéma

Le schéma est organisé en 7 domaines fonctionnels. Toutes les données utilisateur
sont isolées par `household_id` via Row Level Security.

### Diagramme des relations

```mermaid
erDiagram
    households {
        uuid id PK
        text name
        text plan
        text stripe_customer_id
        timestamptz created_at
    }

    household_members {
        uuid id PK
        uuid household_id FK
        uuid supabase_user_id
        text role
        text display_name
        date birth_date
        bool is_child
    }

    member_preferences {
        uuid id PK
        uuid member_id FK
        jsonb diet_tags
        jsonb allergies
        jsonb dislikes
        int cooking_time_max
        text budget_pref
    }

    member_taste_vectors {
        uuid member_id PK-FK
        vector_384 vector
        timestamptz updated_at
    }

    recipes {
        uuid id PK
        text source
        text title
        text slug
        jsonb instructions
        int servings
        int prep_time_min
        int cook_time_min
        int total_time_min
        int difficulty
        text cuisine_type
        jsonb nutrition
        text_array tags
        numeric quality_score
    }

    recipe_embeddings {
        uuid recipe_id PK-FK
        vector_384 embedding
    }

    ingredients {
        uuid id PK
        text canonical_name
        text category
        text unit_default
        text off_id
    }

    recipe_ingredients {
        uuid recipe_id FK
        uuid ingredient_id FK
        numeric quantity
        text unit
        int position
    }

    recipe_feedbacks {
        uuid id PK
        uuid household_id FK
        uuid member_id FK
        uuid recipe_id FK
        int rating
        text feedback_type
        timestamptz created_at
    }

    weekly_plans {
        uuid id PK
        uuid household_id FK
        date week_start
        text status
    }

    planned_meals {
        uuid id PK
        uuid plan_id FK
        int day_of_week
        text slot
        uuid recipe_id FK
        int servings_adjusted
    }

    shopping_lists {
        uuid id PK
        uuid plan_id FK
        jsonb items
        timestamptz generated_at
    }

    fridge_items {
        uuid id PK
        uuid household_id FK
        uuid ingredient_id FK
        numeric quantity
        date expiry_date
    }

    weekly_books {
        uuid id PK
        uuid household_id FK
        uuid plan_id FK
        text pdf_r2_key
        timestamptz notification_sent_at
    }

    subscriptions {
        uuid id PK
        uuid household_id FK
        text stripe_sub_id
        text plan
        text status
        timestamptz current_period_end
    }

    households           ||--o{ household_members      : "a"
    households           ||--o{ weekly_plans           : "génère"
    households           ||--o{ fridge_items           : "possède"
    households           ||--o{ weekly_books           : "reçoit"
    households           ||--o|  subscriptions         : "souscrit"
    household_members    ||--o|  member_preferences    : "configure"
    household_members    ||--o|  member_taste_vectors  : "calcule"
    household_members    ||--o{ recipe_feedbacks       : "soumet"
    weekly_plans         ||--o{ planned_meals          : "contient"
    weekly_plans         ||--o|  shopping_lists        : "génère"
    weekly_plans         ||--o|  weekly_books          : "produit"
    recipes              ||--o{ recipe_ingredients     : "liste"
    recipes              ||--o|  recipe_embeddings     : "vectorise"
    recipes              ||--o{ planned_meals          : "planifiée dans"
    recipes              ||--o{ recipe_feedbacks       : "reçoit"
    ingredients          ||--o{ recipe_ingredients     : "utilisé dans"
    ingredients          ||--o{ fridge_items           : "stocké en"
```

---

## Fichiers — ordre d'exécution

| Ordre | Fichier | Description |
|-------|---------|-------------|
| 1 | `00-setup-extensions.sql` | Extensions PostgreSQL (pgvector, pg_trgm, etc.) |
| 2 | `01-schema-core.sql` | Tables, contraintes, FK |
| 3 | `02-indexes.sql` | HNSW, btree, GIN, trgm |
| 4 | `04-triggers-functions.sql` | Fonctions RLS + triggers (avant policies) |
| 5 | `03-rls-policies.sql` | Row Level Security policies |
| 6 | `07-seed-data.sql` | Seed dev/staging uniquement |
| — | `05-alembic-setup.md` | Guide Alembic |
| — | `06-supabase-setup.md` | Checklist Supabase |

---

## Checklist de validation

### Schema

- [ ] `SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'` retourne 13 tables
- [ ] Toutes les FK sont vérifiées (pas de FK orpheline)
- [ ] `total_time_min` est un GENERATED ALWAYS (pas de colonne manuelle)
- [ ] Trigger `validate_recipe_quality` bloque l'insertion si `quality_score < 0.6`

### Extensions

- [ ] `SELECT * FROM pg_extension WHERE extname = 'vector'` retourne une ligne
- [ ] `CREATE TABLE test_vec (v vector(384))` réussit
- [ ] `SELECT 'test' % 'test2'` (pg_trgm) réussit sans erreur

### RLS

- [ ] RLS activée sur les 11 tables tenant-scoped (`SELECT relrowsecurity FROM pg_class`)
- [ ] Un utilisateur authentifié sans foyer voit 0 ligne dans `households`
- [ ] Deux households isolés ne voient pas mutuellement leurs `weekly_plans`
- [ ] `recipe_feedbacks` : un membre ne peut créer un feedback que pour lui-même
- [ ] Le service_role bypass RLS correctement (voit tout)

### Indexes

- [ ] `\d recipe_embeddings` montre l'index HNSW
- [ ] `EXPLAIN SELECT * FROM recipes WHERE title ILIKE '%poulet%'` utilise `idx_recipes_title_trgm`
- [ ] `EXPLAIN SELECT * FROM weekly_plans WHERE status = 'draft'` utilise l'index partiel

### Seed

- [ ] 10 ingrédients présents
- [ ] 3 recettes avec embeddings
- [ ] 1 household test avec 1 membre et 1 plan draft

---

## Corrections post-review (2026-04-12)

Les corrections suivantes ont été appliquées suite aux audits code-reviewer, debugger et performance-engineer.
Chaque modification est taguée `-- FIX #X` ou `-- OPT #X` dans le fichier SQL concerné.

### FIX #1 — WITH CHECK manquant sur 4 policies UPDATE [CRITIQUE SECURITE]

**Fichier :** `03-rls-policies.sql`
**Tables corrigées :** `household_members`, `member_preferences`, `fridge_items`, `planned_meals`

Sans `WITH CHECK`, PostgreSQL vérifie l'accès à la ligne AVANT la modification (clause `USING`)
mais ne revalide pas la ligne APRES modification. Un attaquant pouvait faire un UPDATE en changeant
`household_id` ou `member_id` pour pointer vers un autre tenant — cassant l'isolation multi-tenant.

Fix appliqué : ajout de `WITH CHECK (...)` identique à la clause `USING` sur chaque policy UPDATE.
Aucune régression : les UPDATEs légitimes (qui ne changent pas le tenant) passent les deux clauses.

### FIX #2 — Récursion RLS sur household_members INSERT [CRITIQUE ONBOARDING]

**Fichier :** `03-rls-policies.sql` (suppression policy INSERT) + `04-triggers-functions.sql` (nouvelle fonction)

La policy INSERT interrogeait `household_members` elle-même sous FORCE RLS. Le premier owner
(0 entrée en base) ne pouvait jamais être créé — deadlock d'onboarding.

Fix appliqué :
- La policy `household_members_insert` pour le rôle `authenticated` est supprimée.
- La création du premier owner passe obligatoirement par `create_household_with_owner()`
  (SECURITY DEFINER, bypass RLS) appelée via service_role côté API FastAPI.
- La fonction est atomique : household + member créés en une seule transaction.

**Impact sur l'API :** l'endpoint `POST /api/households` doit utiliser `SUPABASE_SERVICE_ROLE_KEY`
et appeler `SELECT * FROM create_household_with_owner($name, $uid, $display_name)`.

### FIX #3 — Policies DELETE/UPDATE manquantes [CRITIQUE FONCTIONNEL]

**Fichier :** `03-rls-policies.sql`

Policies ajoutées :
- `weekly_plans_delete` : DELETE pour plans en `status = 'draft'` uniquement.
- `shopping_lists_update` : UPDATE pour cocher les items (JSONB patch) avec `WITH CHECK`.
- `planned_meals_update` : restriction ajoutée aux plans `draft` (cohérence avec le PDF déjà généré).
- `recipe_feedbacks` : DELETE volontairement absent — les feedbacks sont immuables (audit trail RGPD).

### FIX #4 — get_household_constraints() agrégation incorrecte [HIGH]

**Fichier :** `04-triggers-functions.sql`

Deux bugs corrigés :
1. Le `LEFT JOIN LATERAL` duplié produisait un produit cartésien allergies x diet_tags par membre.
   `MIN(cooking_time_max)` était correct par hasard ; `MIN(budget_pref)` était faux.
2. `MIN(TEXT)` sur `budget_pref` utilisait l'ordre lexicographique unicode (locale FR).
   `MIN` retournait `'moyen'` au lieu de `'économique'` pour les foyers mixtes.

Fix appliqué : réécriture en 3 CTEs indépendantes. Budget résolu par `CASE WHEN` avec rang sémantique
explicite (`économique=1, moyen=2, premium=3`) puis `MIN(INT)` — indépendant de la locale.

### OPT #1 — Dénormalisation recipe_embeddings pour pré-filtrage HNSW [PERFORMANCE]

**Fichiers :** `01-schema-core.sql`, `02-indexes.sql`, `04-triggers-functions.sql`

Problème : la query similarité du WEEKLY_PLANNER (`5 recettes filtrées par régime + temps`)
atteignait 150-400ms p95 (HNSW scan + JOIN recipes + filtre post-retrieval).
Avec 7 appels par génération de plan, le SLA <5s était compromis.

Fix appliqué :
- Colonnes dénormalisées dans `recipe_embeddings` : `tags text[]`, `total_time_min int`,
  `difficulty int`, `cuisine_type text` (maintenues par trigger `sync_recipe_embeddings_metadata`).
- Index GIN sur `tags` dénormalisé (`idx_recipe_embeddings_tags_gin`).
- Index BTREE partiel sur `total_time_min` (`idx_recipe_embeddings_total_time`).
- Index composite couvrant `(total_time_min, cuisine_type) INCLUDE (recipe_id)` pour la
  stratégie deux étapes : pré-filtrer les `recipe_id` éligibles, puis scan HNSW sur ce sous-ensemble.

Latence estimée post-fix : 50-100ms p95 (vs 150-400ms avant).

**Note importante :** lors du premier INSERT dans `recipe_embeddings` (RECIPE_SCOUT),
le pipeline doit renseigner les colonnes dénormalisées explicitement. Elles ne sont pas
auto-remplies à l'INSERT — uniquement synchronisées sur UPDATE recipes via le trigger.

### OPT #2 — Pattern auth.uid() dans les policies RLS [PERFORMANCE]

**Fichier :** `03-rls-policies.sql`

Problème : `auth.uid()` appelé directement dans les sous-requêtes USING est re-évalué
par PostgreSQL pour chaque ligne scannée (comportement non-STABLE).

Fix appliqué :
- `auth.uid()` remplacé par `(SELECT auth.uid())` dans les policies critiques
  (les parenthèses forcent l'évaluation scalaire et permettent le cache par le planner PG16).
- `get_current_household_id()` est marquée STABLE + SECURITY DEFINER : PostgreSQL met
  en cache le résultat pour la durée du statement (comportement documenté PG16).
- Pour les tables à très haute fréquence (>1M rows), vérifier avec `EXPLAIN ANALYZE`
  que PostgreSQL inline bien la fonction (pas de "Function Scan" visible).

---

## Pièges connus

### Piège 1 — Dimension du vecteur (CRITIQUE)

La dimension `vector(384)` correspond à `sentence-transformers/all-MiniLM-L6-v2`.
**Ne jamais mélanger des embeddings générés par des modèles différents dans la même colonne.**

Si une migration future passe à OpenAI `text-embedding-3-small` (1536 dims) :
1. `ALTER TABLE recipe_embeddings ALTER COLUMN embedding TYPE vector(1536)` -- casse tout
2. Il faut : créer une colonne `embedding_1536`, re-embedder, basculer, supprimer l'ancienne
3. L'index HNSW doit être recréé (DROP + CREATE — opération longue sur 50 000 lignes)

### Piège 2 — auth.uid() et RLS Supabase

`auth.uid()` retourne `NULL` dans deux cas :
- Requête sans JWT valide (anon non connecté)
- Requête via service_role (qui bypass RLS)

Conséquence : une policy `USING (household_id = get_current_household_id())` avec
`get_current_household_id()` retournant NULL bloquera TOUTES les lignes pour l'utilisateur anonyme.
C'est le comportement voulu pour les données privées.

Pour les tables publiques (recipes, ingredients), ne pas activer RLS — utiliser des GRANTs.

### Piège 3 — Realtime + RLS Supabase

Supabase Realtime applique les policies RLS pour filtrer les événements WebSocket.
Si la table `shopping_lists` a RLS mais que la policy SELECT manque → le client Realtime
ne reçoit aucun événement (pas d'erreur visible, juste silence).

Toujours tester Realtime avec un utilisateur authentifié après modification des policies.

### Piège 4 — pgBouncer Transaction mode

Supabase utilise pgBouncer en mode Transaction pooling sur le port 6543.
Alembic migrations NE FONCTIONNENT PAS via pgBouncer (les `SET session` ne persistent pas).
Utiliser la connexion directe port 5432 pour les migrations uniquement.

### Piège 5 — HNSW ef_search en runtime

L'index HNSW est créé avec `ef_construction=64` mais la précision de recherche runtime
est contrôlée par `SET hnsw.ef_search = 40` (valeur par défaut).
Pour augmenter la précision (au coût de la latence) : `SET hnsw.ef_search = 100`.
À configurer dans le contexte de connexion FastAPI, pas dans l'index.

### Piège 6 — FORCE ROW LEVEL SECURITY

L'instruction `FORCE ROW LEVEL SECURITY` empêche le propriétaire de la table de bypasser RLS.
Sans cette option, un superuser (ex: rôle postgres Supabase) voit toutes les lignes.
Dans Supabase, le rôle postgres est le propriétaire des tables → FORCE est nécessaire.

---

## Agents IA et tables concernées

| Agent | Tables lues | Tables écrites |
|-------|-------------|----------------|
| RECIPE_SCOUT | `recipes`, `ingredients` | `recipes`, `recipe_ingredients`, `ingredients`, `recipe_embeddings` |
| TASTE_PROFILE | `recipe_feedbacks`, `recipe_embeddings` | `member_taste_vectors` |
| WEEKLY_PLANNER | `member_preferences`, `member_taste_vectors`, `fridge_items`, `recipe_embeddings` | `weekly_plans`, `planned_meals` |
| CART_BUILDER | `planned_meals`, `recipe_ingredients`, `ingredients` | `shopping_lists` |
| BOOK_GENERATOR | `weekly_plans`, `planned_meals`, `recipes` | `weekly_books` |
| RETENTION_LOOP | `weekly_books`, `weekly_plans` | `weekly_books.notification_sent_at` |

Tous les agents IA utilisent le **service_role** (bypass RLS) via la variable `SUPABASE_SERVICE_ROLE_KEY`.
