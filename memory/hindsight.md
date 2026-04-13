---
project: "MealPlanner SaaS"
domain: "saas"
type: "hindsight"
created: "2026-04-11"
tags: [project/mealplanner-saas, memory/hindsight, retrospective]
links:
  - "[[memory/MOC]]"
  - "[[memory/session-context]]"
  - "[[CLAUDE]]"
---

# Hindsight — MealPlanner SaaS

> Journal de rétrospectives du projet.
> Après chaque session ou milestone important, Claude (ou toi) ajoute une entrée ICI.
> Ces notes sont re-lues au début de chaque nouvelle session pour éviter de répéter les erreurs.

---

## Comment utiliser ce fichier

Claude doit ajouter une entrée à la fin de chaque session significative :

```
## [Date] — [Titre de la session]
**Ce qui a bien marché** : ...
**Ce qui n'a pas marché** : ...
**Décision prise** : ...
**À ne pas répéter** : ...
**À refaire** : ...
```

---

## 2026-04-12 — Landing enrichie + Auth callback (nextjs-developer)

**Erreur commise** : Dans `StaticRecipeCard`, `recipe.rating_average.toFixed()` a planté au prerender car les recettes de l'API retournent parfois `undefined` (pas `null`) sur ce champ.
**Règle à retenir** : Toujours protéger les appels de méthode numérique avec `!= null` (pas `!== null` — couvre undefined ET null) avant d'appeler `.toFixed()`, `.toFixed()`, etc. Utiliser `Number(val).toFixed()` comme double protection.
**Comment l'éviter** : Tester le prerender statique en local (`pnpm build` + vérifier "Generating static pages") avant de déclarer terminé — même si `pnpm typecheck` passe.

**Erreur commise** : `role="list"` sur un `<ul>` est redondant et bloque le build ESLint a11y.
**Règle à retenir** : Ne jamais ajouter `role="list"` sur un `<ul>` ou `<ol>` — c'est leur rôle implicite. L'utiliser seulement sur des `<div>` qui jouent le rôle d'une liste.

**Erreur commise** : `output: "standalone"` dans next.config.mjs crée des symlinks lors du build, ce qui échoue sur Windows sans droits admin (EPERM). Ce n'est pas une erreur de code.
**Règle à retenir** : Sur Windows en dev, ignorer l'erreur EPERM symlink si les 17/17 pages sont générées avec succès. Le build standalone est conçu pour Linux/Docker. Confirmer le prerender avec `grep "Generating static pages"`.

**Ce qui a bien marché** : Lire les fichiers préexistants avant d'écrire → éviter les doublons (value props existaient déjà). Corriger les bugs ESLint préexistants dans la même passe pour débloquer le build.

---

## 2026-04-12 — Refonte design food premium (nextjs-developer)

**Ce qui a bien marché** : Lire le type `Recipe` existant avant d'écrire la nouvelle interface RecipeCard → découvrir que `recipe.image_url`, `recipe.total_time_minutes`, `recipe.rating_average`, `recipe.rating_count` existent déjà, évitant une duplication de type.
**Décision prise** : Conserver la prop `variant` dans `RecipeCardProps` pour ne pas casser `PlanWeekGrid` qui l'utilise, même si elle n'est plus utilisée dans le rendu (compatibilité descendante sans breaking change).
**Erreur potentielle évitée** : `DIFFICULTY_LABELS` déclaré mais rendu inutile après la refonte de `StaticRecipeCard` — supprimé proprement avant le typecheck.
**Règle à retenir** : Toujours vérifier les imports devenus inutilisés après une refonte partielle d'un fichier existant. `pnpm typecheck` ne catch pas toujours les unused imports si `noUnusedLocals` n'est pas activé en strict.
**À ne pas répéter** : Oublier d'ajouter `images.unsplash.com` dans `next.config.mjs` avant d'utiliser `next/image` avec des URLs Unsplash → erreur runtime `hostname not configured`.

---

## 2026-04-12 — Import Spoonacular (backend-developer)

**Erreur potentielle évitée** : La colonne `category` de la table `ingredients` est NOT NULL sans valeur par défaut en base — une insertion naive sans ce champ aurait levé une erreur PostgreSQL. Lire le modèle ORM avant d'écrire le SQL est obligatoire.
**Règle à retenir** : Toujours lire `apps/api/src/db/models/recipe.py` avant d'écrire des INSERT sur les tables du catalogue (ingredients, recipe_ingredients, recipes). Les contraintes NOT NULL et CHECK ne sont pas toujours évidentes depuis le schéma SQL seul.

**Erreur potentielle évitée** : La colonne `source` dans `recipes` (pas `source_name` comme dans le script `import_sample_recipes.py`). Le modèle ORM fait foi sur les noms de colonnes.

**Erreur potentielle évitée** : `recipe_ingredients.quantity` est Numeric NOT NULL avec `CHECK (quantity > 0)`. Spoonacular peut renvoyer `amount: 0` ou `null` — forcer `quantity = 1.0` comme fallback défensif.

**Ce qui a bien marché** : Exposer `run_import()` comme coroutine async réutilisable — la tâche Celery s'y branche proprement sans dupliquer la logique.
**À ne pas répéter** : Oublier d'ajouter le domaine image dans le CSP `img-src` de `next.config.mjs` en même temps que le `remotePatterns` — les deux sont nécessaires pour que `next/image` fonctionne correctement.

---

## 2026-04-11 — Initialisation du projet

**Ce qui a bien marché** : Génération automatique de la structure de fichiers via Claude Prompt Optimizer.

**À faire en priorité** :
- Compléter les `[PLACEHOLDERS]` dans `memory/project-context.md`
- Définir la stack technique définitive
- Configurer l'environnement de développement

**Points de vigilance identifiés dès le départ** :

- [À documenter au fil du projet]

---

## 2026-04-12 — Phase 0 Database Foundation

**Ce qui a bien marché** : Organisation en domaines fonctionnels dans le SQL,
séparation recipe_embeddings de recipes pour la performance, FORCE ROW LEVEL SECURITY.

**Décisions prises** :
- Embedding 384 dims (all-MiniLM-L6-v2, gratuit) plutôt que 1536 (OpenAI, payant)
- 04-triggers-functions.sql doit s'exécuter AVANT 03-rls-policies.sql
- Connexion directe port 5432 pour Alembic (pas pgBouncer port 6543)

**Pièges documentés** :
- auth.uid() retourne NULL en service_role → comportement voulu, ne pas confondre
- Changer vector(384) → vector(1536) impose re-embed complet + reconstruction index HNSW
- Realtime Supabase silence si RLS policy SELECT manquante (pas d'erreur visible)
- HNSW ef_search est un paramètre runtime (SET hnsw.ef_search), pas de l'index

**À ne pas répéter** :
- Ne jamais mélanger embeddings de modèles différents dans la même colonne vector
- Ne jamais exécuter 07-seed-data.sql en production

---

## 2026-04-12 — Performance Audit Phase 0

**Ce qui a bien marché** : Analyse systématique par couche (DB → Infra → Frontend).
Les calculs de mémoire HNSW (50k × 384 × 4 bytes × overhead) permettent une estimation
concrète et actionnables des besoins Supabase.

**Problèmes identifiés** :
- `allkeys-lru` Redis : anti-pattern pour Celery broker (évincement silencieux des tâches)
- Query vectorielle filtrée : HNSW sans pré-filtrage = latence 150–400ms vs cible 100ms
- `planned_meals` sans `household_id` : double sous-requête RLS coûteuse à 25k users
- 512 MB RAM Railway API : insuffisant avec sentence-transformers (~350 MB en mémoire)
- Batch PDF dimanche : 5k PDFs / 4 concurrency × 2s = 41 min — SLA impossible

**Règles à retenir** :
- Ne JAMAIS utiliser `allkeys-lru` sur un Redis servant de broker Celery
- Tout index HNSW pgvector doit s'accompagner d'une stratégie de pré-filtrage des IDs
  si la query combine filtre métier + similarité vectorielle
- La dénormalisation d'une FK de tenancy (`household_id`) dans les tables enfants
  est obligatoire pour des policies RLS performantes à grande échelle
- Documenter explicitement l'incompatibilité Supabase Free vs 50k embeddings HNSW

**À ne pas répéter** :
- Ne pas dimensionner la RAM Railway sans compter la mémoire des modèles ML chargés
- Ne pas concevoir un batch dimanche sans calculer le throughput max du worker

---

## 2026-04-12 — Design Documents Rate Limiting + PDF Strategy

**Ce qui a bien marché** :
- Lecture des audits avant design → les décisions sont directement ancrées dans les findings mesurés
- Séparation claire fail-open (Redis down) vs fail-close (mode strict) — évite les décisions implicites
- Calcul explicite du pic PDF (41 min → 4 min) pour justifier la décision architecturale

**Règles à retenir** :
- Tout endpoint LLM doit avoir un rate limit dédié (req/heure, pas req/minute) — les coûts sont horaires
- Ne jamais laisser un batch nocturne unique sans calculer le throughput max du worker avant de l'approuver
- Les circuit breakers et le rate limiting sont deux mécanismes distincts : le rate limiting protège contre l'abus intentionnel, le circuit breaker protège contre les défaillances cascadantes des services tiers
- Redis utilisé pour deux rôles (broker Celery + rate limiting) doit utiliser des databases séparées (DB 0 et DB 1) pour éviter les collisions de clés et les évictions croisées

**À ne pas répéter** :
- Ne pas valider un design de batch sans calculer le temps d'exécution à charge nominale
- Ne pas laisser un middleware critique (rate limiting) comme "à documenter plus tard" — si c'est une règle ROADMAP non-négociable, le design doit exister avant Phase 1

---

## 2026-04-12 — Corrections bugs critiques Phase 1 (multi-agent review)

**Ce qui a causé le plus de bugs** : 4 agents travaillant en parallèle sans contrat d'interface partagé.
Résultat : difficulty 1-3 vs 1-5 sur 4 fichiers, rate-limit importé mais jamais appliqué, book_generator
référencé mais inexistant, worker sans accès aux modèles DB.

**Règles à retenir** :
- Ne jamais référencer dans Celery task_routes/beat_schedule un module qui n'existe pas encore — le Beat crashe au premier tick.
- Quand plusieurs agents codent en parallèle, définir un contrat d'interface AVANT (ex: difficulty = 1-5, pas 1-3).
- `allow_headers=["*"]` + `allow_credentials=True` est REJETÉ par tous les navigateurs modernes (spec CORS).
- `anthropic.Anthropic` (sync) dans une coroutine `async def` bloque l'event loop — toujours utiliser `AsyncAnthropic`.
- pgvector HNSW : le filtre `WHERE distance >= seuil` désactive l'index. Toujours ORDER BY + LIMIT, filtrer en Python.
- Les imports de variables de rate-limiting ne suffisent pas — slowapi exige soit `default_limits` dans Limiter(), soit un décorateur `@limiter.limit()` sur chaque route.
- Le contenu scrapé web injecté dans un prompt LLM sans délimiteurs = surface d'attaque prompt injection.

**Décision architecturale : packages/db partagé vs copie dans worker** :
- Choix : package partagé `packages/db` (ré-exports vers apps/api/src/db/).
- Raison : source de vérité unique, pas de maintenance double, cohérence garantie lors des migrations.
- Condition devops : ajouter packages/db dans [tool.uv.workspace] members + `uv sync`.

**À déléguer (ne pas oublier)** :
- devops-engineer : corriger .env.example (SPOONACULAR_KEY → SPOONACULAR_API_KEY, ajouter SUPABASE_JWT_SECRET)
- devops-engineer : ajouter packages/db dans workspace uv racine
- database-administrator : passer constraint `difficulty CHECK BETWEEN 1 AND 3` → 1 AND 5
- database-administrator : vérifier RLS policy SELECT sur table recipes (catalogue global)

## 2026-04-12 — Corrections 5 bugs critiques frontend Phase 1 Mature (nextjs-developer)

**Ce qui a causé le plus de bugs** : 3 agents codant le frontend, le backend et le contrat d'interface en parallèle sans synchronisation. Les 5 mismatches (member/first_member, loved/cooked, low/économique, planned_meals/meals, body vide/{week_start}) ont tous la même cause racine : absence de contrat d'interface partagé (OpenAPI spec ou fichier types partagé) avant le développement parallèle.

**Règles à retenir** :
- **Contrat d'interface d'abord** : quand frontend et backend codent en parallèle, définir un fichier OpenAPI ou un fichier `contracts.ts` partagé AVANT. Même 30 minutes de sync contractuelle évite 5 mismatches bloquants.
- **Polling par état, pas par ID** : ne jamais poller `/resource/{task_id}` quand `task_id` est un ID externe (Celery, SQS). Toujours poller via une ressource DB (`/resource/me/current`) et attendre un état stable. Un ID de tâche async n'est PAS un ID de ressource.
- **Submit orchestré = idempotence obligatoire** : toute séquence d'étapes API côté client (créer household → créer membres → créer plan) doit commencer par une vérification d'existence. Sans ça, un retry après échec partiel génère des données orphelines impossibles à résoudre sans intervention backend.
- **Open redirect** : tout paramètre `redirect` dans une URL de login doit être validé AVANT injection dans `emailRedirectTo`. Un `startsWith("/")` et un blocage des `://` suffisent. Ne jamais passer le paramètre brut.
- **next-intl en Phase 1 = sur-ingénierie** : si l'app n'a qu'une locale, next-intl ajoute 28 KB gzip et un middleware inutile. Utiliser un helper `t(key: string)` sur `fr.json`. Réinstaller next-intl en Phase 4.
- **`import type { Metadata }` dans un Client Component** : TypeScript ne lève pas d'erreur mais Next.js ignore silencieusement l'export. Les métadonnées dans un `"use client"` ne fonctionnent jamais — les mettre dans un `layout.tsx` ou `metadata.ts` séparé.

**À ne pas répéter** :
- Ne pas coder un store Zustand avec une fonction de polling sans vérifier que l'endpoint attend le bon type d'ID.
- Ne pas valider un submit multi-étapes comme "terminé" sans avoir testé le scénario d'échec partiel + retry.
- Ne pas déployer sans avoir aligné les enums frontend ↔ backend via un contrat écrit (même minimal).

## 2026-04-12 — Migration LLM Anthropic → Google Gemini (RECIPE_SCOUT)

**Contexte** : Propriétaire a abonnement Claude Max ($180/mois). Payer l'API Anthropic en plus
serait une double facturation inutile pour du batch nocturne qui n'a pas besoin de latence faible.

**Décision** : Gemini 2.0 Flash (free tier 15 req/min, 1 500 req/jour) remplace
`claude-sonnet-4-6` dans `validator.py` et `tagger.py`.

**Ce qui a bien marché** :
- `response_schema` Gemini est un équivalent direct du `tool_use` Anthropic — structured output
  JSON garanti, même logique de parsing, pas de texte libre à parser.
- `client.aio.models.generate_content()` conserve l'async natif — pas de blocage event loop.
- `google-genai>=1.0` (SDK officiel 2025) confirme son existence sur PyPI (v1.72.0 au 2026-04-12).

**Règles à retenir** :
- `google-genai` (nouveau SDK unifié 2025) ≠ `google-generativeai` (ancien, déprécié).
  Toujours utiliser `google-genai>=1.0` dans les nouvelles intégrations.
- Le singleton `_gemini_client` doit être `None` au niveau module, réinitialisé dans les tests
  unitaires pour éviter la pollution entre tests (état global partagé).
- `rejection_reason` de Gemini peut être une chaîne vide `""` (pas `null`) — normaliser
  en `None` côté Python : `result.get("rejection_reason") or None`.
- Conserver `[project.optional-dependencies] anthropic = ["anthropic>=0.34"]` dans pyproject.toml
  pour le fallback — permet un `uv pip install 'mealplanner-worker[anthropic]'` sans modifier le code.

**À ne pas répéter** :
- Ne pas supprimer complètement le package `anthropic` des dépendances — garder en optionnel.
- Ne pas oublier de réinitialiser le singleton client dans les tests d'intégration.

## 2026-04-12 — Automatisation Init Docker + Colonnes OFF manquantes

**Ce qui a bien marché** :
- Assemblage des 5 fichiers SQL Phase 0 en un seul fichier 02-schema.sql ordonné et idempotent.
- Utilisation de `CREATE OR REPLACE FUNCTION` + `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` pour rendre les triggers idempotents (PostgreSQL ne supporte pas `CREATE OR REPLACE TRIGGER` sur tous les contextes).
- Index pg_trgm sur recipes.title déjà présent dans 02-indexes.sql — pas de gap, alias idx_ ajouté via bloc DO$$ idempotent.

**Problèmes identifiés** :
- Colonnes OFF (off_id, off_last_checked_at, off_match_confidence, off_product_name, off_brand) absentes du fichier 01-schema-core.sql original — les migrations Alembic 0004/0005 n'avaient pas tourné sur Windows. Corrigé directement dans 02-schema.sql.
- content_hash absent de weekly_books dans le schéma core original (prévu dans 13-pdf-generation-strategy.md uniquement) — intégré dans 02-schema.sql.
- Docker non accessible depuis le shell bash en session Windows/Git Bash. Validation effectuée par lecture croisée sources SQL + modèles SQLAlchemy.

**Règles à retenir** :
- Quand les migrations Alembic ne peuvent pas tourner (asyncpg Windows), le fichier 02-schema.sql est LA migration. Toute colonne ajoutée via migration Alembic doit être propagée dans 02-schema.sql immédiatement.
- Idempotence triggers PostgreSQL : `DROP TRIGGER IF EXISTS nom ON table; CREATE TRIGGER nom...`. Pas de `CREATE OR REPLACE TRIGGER` (syntaxe PostgreSQL 14+ non universelle).
- Un index pg_trgm sur une colonne de recherche critique (recipes.title) doit être nommé de façon stable dans tous les fichiers qui le référencent (commentaires, EXPLAIN ANALYZE, rapports perf).
- Les colonnes de "migrations futures" (OFF, content_hash, validated_at) doivent être incluses dans le schéma d'init Docker dès leur conception, sans attendre que les migrations Alembic soient jouées.

**À ne pas répéter** :
- Ne pas laisser des colonnes de migrations "flottantes" non propagées dans le fichier d'init Docker. Toute nouvelle colonne Alembic → mise à jour immédiate de 02-schema.sql.

## 2026-04-12 — DB Phase 2 : enrichissements Stripe + Mode frigo + RETENTION_LOOP

**Ce qui a bien marché** :
- Créer un fichier `04-phase2-schema.sql` distinct plutôt que modifier `02-schema.sql` : préserve la cohérence de l'historique Phase 0, s'exécute automatiquement après dans l'ordre alphabétique.
- Utiliser les préfixes différents (ix_ vs idx_) pour les index Phase 2 vs Phase 0 : coexistence sans conflit, traçabilité par phase.
- TYPE_CHECKING pour la relation bidirectionnelle Household ↔ Subscription : évite l'import circulaire tout en gardant la type safety Mypy.

**Pièges identifiés** :
- `from __future__ import annotations` DOIT être la première ligne du module Python (avant tout autre import). Une erreur de placement silencieuse en VSCode mais bloquante à l'import.
- PostgreSQL ne supporte pas `CREATE OR REPLACE TRIGGER` dans les versions < 14 — continuer avec le pattern DROP + CREATE.
- `ix_subscriptions_household_active` (index partiel unique) COEXISTE avec la contrainte `UNIQUE(household_id)` Phase 0 — ils ne s'annulent pas. Si on veut permettre plusieurs rows canceled par foyer à terme, il faudra supprimer la contrainte UNIQUE Phase 0 via migration Alembic.

**Règles à retenir** :
- Toute nouvelle colonne Phase N doit être dans un fichier `0N-phase-N-schema.sql` distinct, pas dans le fichier Phase 0. Facilite les rollbacks et la lisibilité de l'historique des migrations.
- SECURITY DEFINER sur une fonction SQL + SET search_path TO '' : combo obligatoire pour prévenir le search_path hijacking en PostgreSQL. Ne pas omettre le SET search_path même si ça semble redondant.
- Les index partiels WHERE status IN (...) doivent lister les valeurs littérales, pas une sous-requête — PostgreSQL évalue la condition à la création, pas à la requête.

**À ne pas répéter** :
- Ne pas oublier de mettre à jour DEUX fichiers `__init__.py` (apps/api + packages/db) quand un nouveau modèle est créé — les deux sont des sources de vérité pour Alembic et le worker respectivement.

## 2026-04-12 — Phase 2 Frontend : Billing, Frigo, Livres PDF, Filtres (nextjs-developer)

**Ce qui a bien marché** :
- Séparation page.tsx (Server Component + metadata) + *-content.tsx (Client Component) : pattern propre, pas d'erreur "metadata dans Client Component".
- UpgradeGate générique avec PLAN_HIERARCHY numérique : extensible proprement à un plan "coach" sans if/else en dur.
- useRemoveFridgeItem avec optimistic update complet (cancelQueries + snapshot + rollback on error) : pattern à réutiliser systématiquement sur tous les DELETE.

**Règles à retenir** :
- Ne JAMAIS mettre `export const metadata` dans un fichier avec `"use client"` — Next.js l'ignore silencieusement. Toujours dans page.tsx (Server Component) ou layout.tsx.
- `useInfiniteQuery` TanStack Query v5 : utilise `initialPageParam` (pas `defaultPageParam`), et `getNextPageParam` retourne `undefined` (pas `null`/`false`) pour signaler la fin.
- Swipe Framer Motion : `useMotionValue` + `useTransform` bypasse React render loop — plus performant que useState pour les gestes. Pattern à conserver pour tous les swipe-to-action.
- `localStorage.getItem` peut throw en navigation privée (Firefox strict) ou en SSR — toujours wrapper dans try/catch silencieux.
- Ne pas importer une icône Lucide inutilisée : ESLint `no-unused-vars` bloque le build. Supprimer l'import directement plutôt que de le commenter ou d'utiliser `void`.

**À ne pas répéter** :
- Ne pas ajouter `void IconName;` pour désactiver les warnings d'imports inutilisés — supprimer l'import directement.

## 2026-04-12 — Phase 2 Backend : BOOK_GENERATOR + Stripe + Frigo + RETENTION_LOOP (backend-developer)

**Ce qui a bien marché** :
- Lecture préalable de `13-pdf-generation-strategy.md` : toute la décision architecturale (génération à la validation vs batch) était déjà documentée → implémentation directe sans redécider.
- Isolation des modules par responsabilité (agent/template/renderer/storage/tasks) : chaque fichier est < 200 lignes, testable indépendamment.
- `_compute_plan_hash` avec exclusion de `generated_at` : garantit la stabilité du hash entre deux runs sur le même plan sans changement.

**Règles à retenir** :
- **WeasyPrint est synchrone** : en contexte Celery (pas d'event loop), c'est acceptable. Mais si appelé depuis FastAPI async, utiliser `loop.run_in_executor(None, ...)`.
- **Stripe webhook : jamais de auth JWT ni de rate limit**. Un 401 ou 429 retourné à Stripe déclenche des retries infinis qui saturent les logs. La sécurité se fait uniquement via `stripe.Webhook.construct_event()`.
- **require_plan() doit être une factory** qui retourne un `async def` — pas directement un `async def`. FastAPI injecte les dépendances en appelant l'objet retourné par la factory.
- **DELETE fridge_items** : vérifier `household_id` dans la même requête SQL (`WHERE id = :item_id AND household_id = :hid`) — jamais en deux requêtes séparées (vulnérabilité TOCTOU).
- **Celery Beat `hour="*/4"`** est la syntaxe crontab correcte pour "toutes les 4 heures". `range(0, 24, 4)` fonctionne aussi mais est moins idiomatique.

**À ne pas répéter** :
- Ne pas activer les routes book_generator dans `app.py` sans implémenter le module complet — le Beat crashe au premier tick si la tâche est introuvable.
- Ne pas appeler `stripe.api_key = ...` dans les tests — mocker le client Stripe ou utiliser les fixtures Stripe test.
- Ne pas oublier de décommenter les entrées `task_routes` ET `beat_schedule` en même temps — un seul suffit à crasher le Beat.

## 2026-04-12 — Nettoyage final Phase 2 : tests, deps, sample recipes

**Erreur commise** : `UNIT_CONVERSIONS` indexé `dict[str, dict[str, float]]` avec la clé externe = unité source et la clé interne = unité cible, mais les valeurs étaient inversées (1 kg = 0.001 dans la table alors que 1 kg = 1000 g). La structure dict imbriquée prête à confusion.
**Règle à retenir** : Préférer `dict[tuple[str, str], float]` pour les tables de conversion — `(source, cible) → facteur`. Plus lisible, moins sujet aux inversions.
**Comment l'éviter** : Écrire les tests de conversion en parallèle avec la table (kg→g, cl→ml, l→ml). Un test unitaire sur `_normalize_unit(1.5, "kg")` aurait détecté l'inversion immédiatement.

**Erreur commise** : Import `mealplanner_db` dans le corps d'une coroutine mockée dans un test qui ne l'utilise pas réellement. Le mock échouait à l'import avant même d'atteindre le `raise ValueError`.
**Règle à retenir** : Dans un test mock qui simule un comportement (ex: lever une exception), ne jamais importer des modules réels dont la disponibilité est incertaine. Si le test est "je veux vérifier que ValueError est propagée", la coroutine mock ne doit contenir que le `raise`.
**Comment l'éviter** : Lire chaque import dans les fonctions mock avec la question "cet import est-il nécessaire pour ce que le test vérifie ?".

**Erreur commise** : Test `test_limite_max_2_par_cuisine` supposait que la contrainte MAX_SAME_CUISINE est toujours respectée, même quand le pool est mathématiquement insuffisant. Avec 4 italiennes + 1 française + 1 mexicaine pour 5 dîners, le fallback (documenté et intentionnel) dépasse la limite.
**Règle à retenir** : Les tests de contraintes de diversité doivent prendre en compte les conditions de fallback. Si l'algorithme a un fallback documenté qui relâche la contrainte, le test doit soit (a) tester avec un pool assez diversifié, soit (b) valider uniquement que le fallback ne dépasse pas raisonnablement.
**Comment l'éviter** : Concevoir le fixture de test avec au moins `(num_cuisines_non_dominantes × MAX_SAME_CUISINE) >= num_dinners_demandés` pour éviter le fallback dans les tests de contrainte.

**Ce qui a bien marché** :
- Imports conditionnels `try: import stripe / except ImportError: stripe = None` : pattern propre qui évite les crashes au démarrage en test sans casser la logique métier.
- La garde `_check_stripe_configured()` dans les endpoints billing : retourne 503 proprement sans crash AttributeError si stripe est None ou clé absente.
- `uv sync` depuis la racine du workspace installe automatiquement tous les packages des 3 membres (api + worker + db) en un seul run.

## 2026-04-12 — Fix connexion prod Vercel ↔ Railway (backend-developer)

**Erreur commise** : `stripe_config.py` appelait `get_settings()` au niveau module-level sans try/except. Si STRIPE_SECRET_KEY est vide en production, l'import du module ne crashe pas (car get_settings() tolère la valeur vide avec `default=""`), mais le pattern est risqué — toute validation Pydantic qui échoue arrête le serveur entier.
**Règle à retenir** : Tout appel à `get_settings()` dans un module importé au démarrage doit être dans une fonction (lazy), pas au niveau module. Utiliser `_get_plans()` et `_init_stripe_if_needed()` comme pattern.
**Comment l'éviter** : Wraper `get_settings()` dans try/except dans tous les fichiers de configuration secondaires (stripe_config, billing, webhooks).

**Erreur commise** : `session.py` ne configurait pas SSL pour les connexions asyncpg vers Supabase. asyncpg en production sans SSL = connexion refusée par Supabase (`SSL connection is required`).
**Règle à retenir** : Toute connexion asyncpg vers Supabase (ou tout PostgreSQL en production) doit passer `ssl=ssl.create_default_context()` dans `connect_args`. Détecter automatiquement via `"supabase" in DATABASE_URL` ou `ENV in ("prod", "production", "staging")`.
**Comment l'éviter** : Ajouter une fonction `_build_connect_args()` dans session.py qui encapsule la logique SSL — pattern réutilisable pour tous les projets Supabase.

**Erreur commise** : Les endpoints recipes lançaient une `HTTPException 503` (ou propagaient un 500 non catchée) si la DB Supabase était inaccessible. Côté frontend, cela affiche "Impossible de charger les recettes" même si le service API tourne bien.
**Règle à retenir** : Les endpoints de catalogue public (recettes, produits, contenu) doivent retourner une liste vide avec HTTP 200 si la DB est inaccessible, pas un 5xx. Le 5xx est réservé aux mutations critiques (POST/PUT/DELETE).
**Comment l'éviter** : Wrapper les SELECT dans un try/except global avec `logger.error()` + retour de la structure vide attendue par le schéma Pydantic.

**Ce qui a bien marché** :
- Vérifier l'absence de `Depends(get_current_user)` sur les endpoints publics via grep avant de coder — évite une fausse piste sur l'auth.
- `logger.info("cors_origins_configured", origins=..., raw_value=...)` au démarrage : diagnostic CORS en 1 ligne dans les logs Railway sans déploiement de debug supplémentaire.

## 2026-04-12 — Fix 7 bugs production frontend Presto (nextjs-developer)

**Erreur commise** : `getRecipes()` référençait `FALLBACK_RECIPES` avant sa déclaration `const` — temporal dead zone (TDZ) qui aurait causé un `ReferenceError` au prerender.
**Règle à retenir** : Dans un Server Component avec `const` au niveau module, déclarer les dépendances AVANT la fonction qui les utilise. Structurer dans cet ordre : imports → types → constantes statiques (FALLBACK_*) → fonctions async de fetch → composants → page export.
**Comment l'éviter** : Relire l'ordre des déclarations dans page.tsx avant de submit. Si une fonction `async` référence une constante, la constante doit être au-dessus dans le fichier.

**Erreur commise** : `API_BASE_URL = process.env.NEXT_PUBLIC_API_URL` sans fallback — si la variable n'est pas configurée sur Vercel, tous les appels API échouent silencieusement avec une URL `undefined`.
**Règle à retenir** : Toute variable `NEXT_PUBLIC_*` utilisée comme base URL doit avoir un fallback hardcodé vers la production. Pattern : `process.env.NEXT_PUBLIC_API_URL || "https://..."`. Vérifier dans `lib/api/client.ts` ET dans chaque RSC qui fait des fetches.

**Erreur commise** : Routes `/feed` et `/profile` dans la navigation pointaient vers des pages inexistantes. La sidebar et le bottom nav généraient des 404 sur des liens utilisateur critiques.
**Règle à retenir** : Après la création de nouvelles pages, toujours auditer TOUS les `href` des composants de navigation. Matcher chaque href contre un `page.tsx` existant dans `app/(app)/`. Un lien cassé dans la nav = bug critique (découvrabilité zéro).

**Ce qui a bien marché** :
- Pattern Server Component (fetch + token) + Client Component (*-content.tsx) : conservé systématiquement pour account/settings — cohérent avec billing, books, fridge.
- `AbortSignal.timeout(5000)` sur les fetch RSC + `setTimeout(() => controller.abort(), 15_000)` dans apiClient : protège contre les cold starts Railway sans bloquer le rendu.
- Deux modes d'auth sur signup/login (password + magic link) sans duplication de logique : state machine `mode: "password" | "magic-link" | "forgot-password"` — extensible proprement.

## 2026-04-12 — Fix CORS prod Railway : ne pas dépendre uniquement de CORS_ORIGINS env var

**Erreur commise** : Le middleware CORS de `main.py` ne lisait que `settings.cors_origins_list` (issue de `CORS_ORIGINS` env var). Si Railway parse mal la variable (espace résiduel, guillemet, slash final), la liste est vide ou invalide et aucun `access-control-allow-origin` n'est renvoyé.
**Règle à retenir** : Toujours hardcoder les domaines de production critiques en plus de la variable d'env. Pattern : `_ALWAYS_ALLOWED_ORIGINS` fusionné avec `settings.cors_origins_list` avant `add_middleware`. Le log `cors_origins_configured` au démarrage doit afficher la liste finale (après merge) pour diagnostic Railway sans redéploiement.
**Comment l'éviter** : Tester le CORS sur chaque nouveau déploiement avec `curl -I -H "Origin: https://..."` avant de fermer la PR.

**Erreur commise** : Le format loguru dev utilisait `{extra[correlation_id]}` dans la format string, mais les logs émis pendant le lifespan/startup n'ont pas encore de correlation_id dans `extra` (le middleware HTTP n'a pas encore tourné). Résultat : `KeyError: 'correlation_id'` sur chaque log de démarrage.
**Règle à retenir** : Dès qu'un format loguru référence une clé `extra`, ajouter un filtre (`filter=...`) qui injecte un défaut via `record["extra"].setdefault(...)`. Ne jamais supposer qu'un champ `extra` est présent pour tous les logs, en particulier ceux du lifespan.
**Comment l'éviter** : Tester le démarrage à froid (`uvicorn src.main:app`) en local et vérifier l'absence de KeyError dans les premières lignes de log.

## 2026-04-12 — Fix 6 bugs frontend production Presto (nextjs-developer)

**Erreur commise** : Deux items de navigation pointant vers la même route (`/dashboard`) — "Accueil" ET "Planning" — constituent un bug UX critique (désorientation, état actif dupliqué, doublon SEO).
**Règle à retenir** : Avant de déclarer une navigation terminée, vérifier l'unicité des `href` dans tous les items. Un item dupliqué = supprimer le moins descriptif.
**Comment l'éviter** : `new Set(NAV_ITEMS.map(i => i.href)).size === NAV_ITEMS.length` doit être vrai.

**Erreur commise** : Import `CalendarDays` conservé dans `app-bottom-nav.tsx` après suppression de l'item "Planning" qui l'utilisait — ESLint `no-unused-vars` aurait bloqué le build.
**Règle à retenir** : Quand on supprime un item qui utilise une icône Lucide, supprimer l'import en même temps dans la même passe.

**Erreur commise** : `budget_pref: "low" | "medium" | "high"` dans `use-household.ts` ne correspondait pas au contrat backend `"économique" | "moyen" | "premium"` déjà aligné dans `endpoints.ts`.
**Règle à retenir** : Tout enum partagé frontend↔backend doit avoir une source unique dans `endpoints.ts` ou `types.ts` et être importé depuis là. Ne jamais re-déclarer un enum dans un hook.
**Comment l'éviter** : Grep l'enum dans tout `apps/web/src` après chaque contrat résolu pour vérifier la propagation.

**Ce qui a bien marché** :
- `generateMutation.mutate(undefined, { onError })` permet de surcharger le gestionnaire d'erreur au call-site sans modifier le hook — pattern propre pour des cas spéciaux (CORS/réseau) sans casser les autres usages.
- `useRef<ReturnType<typeof setTimeout>>` pour le retry timer : évite les setState dans un timeout (stale closure) et permet l'annulation propre si l'utilisateur re-clique.

## 2026-04-12 — Migration police Fraunces → Noto Serif (design premium)

**Ce qui a bien marché** :
- Conserver `display` comme alias dans `fontFamily` du tailwind.config.ts → assure la rétro-compatibilité avec tous les composants qui utilisent encore `font-display` sans casser le build.
- `sed -i 's/font-display/font-serif/g'` sur 16 fichiers en une passe — plus rapide et sans risque d'oubli vs édition manuelle fichier par fichier.
- Vérifier `pnpm typecheck` en fin de migration : confirme l'absence de régression TypeScript avant de déclarer terminé.

**Règles à retenir** :
- Quand on change une variable de font CSS (`--font-fraunces` → `--font-serif`), vérifier immédiatement que ZERO fichier référence encore l'ancienne variable via grep (`--font-fraunces` dans src/).
- Les commentaires peuvent mentionner l'ancien nom (ex: "remplace Fraunces") — seules les classes CSS et les imports importent.
- `primary.DEFAULT` dans tailwind doit correspondre exactement à la couleur CSS `--color-primary` — sinon `bg-primary` et `text-primary` donnent des couleurs différentes.

**À ne pas répéter** :
- Ne pas oublier de mettre à jour `layout.tsx` quand on change le nom d'export dans `fonts.ts` — l'import `fraunces` → `notoSerif` doit être propagé dans la même passe.

<!-- Les entrées suivantes seront ajoutées automatiquement par Claude après chaque session -->
