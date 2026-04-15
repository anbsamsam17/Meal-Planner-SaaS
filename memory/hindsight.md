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

## 2026-04-15 — Migration SQL vers Supabase : 3 pièges d'export JSONB
**Erreur commise** : L'export pg_dump/psql des recettes vers des INSERT SQL a produit du JSON invalide pour Supabase : (1) U+2028 (LINE SEPARATOR) non échappé par `json.dumps(ensure_ascii=False)`, (2) `\r\n` bruts dans le texte des instructions, (3) backslashes orphelins `\ ` issus du scraping HTML. De plus, la colonne `language` n'existait pas en prod (migration Alembic jamais exécutée), et les UUID des ingrédients différaient entre dev et prod → conflit `canonical_name`.
**Règle à retenir** : Pour exporter des données JSONB vers SQL :
- TOUJOURS utiliser psycopg2 + `json.dumps()` natif (pas pg_dump texte)
- TOUJOURS sanitizer les strings AVANT json.dumps : supprimer CR (0x0d), U+2028, U+2029, tout char < 0x20
- `json.dumps(ensure_ascii=False)` ne protège PAS contre U+2028/U+2029
- Pour les ingrédients avec contrainte unique sur `canonical_name` : utiliser `ON CONFLICT (canonical_name) DO UPDATE SET id = EXCLUDED.id`
- Chaque fichier SQL doit être autonome : inclure `SET session_replication_role = replica` dans chaque fichier (pas seulement le premier)
- Supabase SQL Editor a une limite de ~1 Mo : découper les gros fichiers
**Comment l'éviter** : Utiliser `scripts/export_recipes_clean.py` pour tout export futur. La fonction `_sanitize_jsonb_value()` nettoie récursivement toute structure JSONB.

---

## 2026-04-15 — asyncpg ne supporte pas :param::type dans SQLAlchemy text()
**Erreur commise** : Les scripts de scraping utilisaient `:nutrition::jsonb` et `:tags::text[]` dans les requêtes `text()` de SQLAlchemy. asyncpg interprète `::` comme un cast PostgreSQL mais ne résout pas le `:name` avant → erreur de syntaxe SQL.
**Règle à retenir** : Avec asyncpg, utiliser `CAST(:param AS jsonb)` au lieu de `:param::jsonb`. Pour les arrays `text[]`, passer une Python `list` directement avec `CAST(:param AS text[])` — asyncpg encode nativement les listes Python en arrays PG.
**Comment l'éviter** : Chercher `::jsonb`, `::text[]`, `::int[]` dans tout script utilisant `text()` + asyncpg. Les remplacer systématiquement par `CAST(:param AS type)`.

---

## 2026-04-14 — REC-04/REC-05 : mismatch API→frontend dans hook et shopping list (fullstack-developer)

**REC-04 — Shopping list items non persistés** :
Le hook `useToggleItem` était en "Phase 1" localStorage uniquement. L'API backend stocke `checked` dans le JSON de `shopping_lists.items` (champ dans le tableau JSONB). Il manquait un endpoint `PATCH /plans/me/{plan_id}/shopping-list/{ingredient_id}` pour persister l'état coché. La clé naturelle de chaque item dans le JSON est `ingredient_id` (pas un UUID séparé).
**Règle à retenir** : Avant d'implémenter un toggle en localStorage, vérifier que la table DB a bien un identifiant stable par item. Si les items sont stockés comme JSON array dans une colonne JSONB, l'upsert se fait avec UPDATE SET items = CAST(:new_json AS jsonb) sur toute la liste — pas via SQL UPDATE ciblé sur un item.
**Comment l'éviter** : Un endpoint PATCH qui met à jour un champ dans un JSONB array doit chercher l'item dans le tableau Python/dict, le modifier, puis sérialiser et enregistrer tout le tableau. Ne pas tenter de JSONB path operators (complexes) si le volume est petit.

**REC-05 — Settings préférences non pré-remplies** :
Le hook `useHousehold` faisait `apiClient.get<HouseholdResponse>("/api/v1/households/me")` en supposant que l'API retournait `{household, members, preferences}`. Mais le backend retourne `HouseholdRead` = `{id, name, plan, members[{...preferences}]}`. Les préférences sont imbriquées dans chaque membre (`members[].preferences`), pas au niveau racine. Le `useEffect` de `settings-content.tsx` accédait à `household.preferences` qui était toujours `undefined`.
**Règle à retenir** : Toujours lire le schéma Pydantic de retour (`response_model=`) du backend avant de typer la réponse dans le hook frontend. Ajouter une fonction `normalizeXxx()` dans le hook pour mapper le format API brut vers le type normalisé attendu par les composants.
**Comment l'éviter** : Dans le hook, typer le retour brut de l'API avec `XxxRaw` et le résultat normalisé avec `XxxResponse`. Ne jamais caster `apiClient.get<FrontendType>()` directement sans normalisation quand les structures diffèrent.

---

## 2026-04-15 — CSP strict-dynamic incompatible avec Next.js 14
**Erreur commise** : Ajout de `'strict-dynamic'` au `script-src` CSP en production. Cela annule `'unsafe-inline'` (spec CSP3), bloquant les scripts d'hydration Next.js → page blanche.
**Règle à retenir** : `'strict-dynamic'` et `'unsafe-inline'` sont mutuellement exclusifs en CSP3. Next.js 14 nécessite `'unsafe-inline'` pour ses scripts d'hydration. Le seul moyen de supprimer `'unsafe-inline'` est d'implémenter des nonces dynamiques via middleware.
**Comment l'éviter** : Ne jamais ajouter `'strict-dynamic'` à un projet Next.js sans nonces. Toujours tester la CSP en staging avant prod.

---

## 2026-04-15 — Supabase utilise ES256 (ECDSA), pas HS256 (HMAC)
**Erreur commise** : On a supposé que Supabase signait les JWT avec HS256 (HMAC symétrique) et tenté de vérifier avec SUPABASE_JWT_SECRET et SUPABASE_ANON_KEY. 4 déploiements ont échoué avec des 401 sur toutes les requêtes.
**Règle à retenir** : Les projets Supabase récents utilisent ES256 (ECDSA P-256) pour signer les JWT. La vérification se fait avec la clé publique JWKS à `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, pas avec un secret symétrique. Toujours lire `jwt.get_unverified_header(token)` pour détecter l'algorithme avant de vérifier.
**Comment l'éviter** : Avant toute modification de `security.py`, vérifier l'en-tête `alg` d'un vrai token. Ne jamais hardcoder `algorithms=["HS256"]` sans diagnostic.

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

## 2026-04-12 — Fix crash /recipes/[id] — mismatch champ API photo_url vs image_url (nextjs-developer)

**Erreur commise** : Le type `Recipe` déclarait `image_url` comme non-nullable et `photo_url` absent. L'API retourne `photo_url` (null) au lieu de `image_url`. Le composant crashait silencieusement sans Error Boundary.
**Règle à retenir** : Toujours vérifier l'alias de champ entre le schéma Python (Pydantic) et le type TypeScript frontend avant de typer strictement. Un champ `image_url` côté TS peut correspondre à `photo_url` côté API. Normaliser dans la couche `fetchXxx()` côté serveur.
**Comment l'éviter** : (1) Lire le schéma Pydantic du backend avant d'écrire l'interface TypeScript. (2) Toujours créer un `error.tsx` dans chaque route `[id]` au moment de créer `page.tsx`. (3) Typer tous les champs textuels et numériques venant de l'API en `| null` par défaut — le backend Python peut retourner null sur n'importe quel champ optionnel.

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

## 2026-04-12 — Refonte page recettes — alignement types Recipe (nextjs-developer)

**Erreur potentielle évitée** : Le type `Recipe.difficulty` est `"easy" | "medium" | "hard" | null` (enum string), pas `1 | 2 | 3 | 4 | 5`. `RecipeFilters.difficulty` utilise l'échelle numérique 1-5 côté filtres API, mais la card reçoit une `Recipe` avec l'enum string. Ne jamais confondre les deux représentations — le filtre envoyé à l'API est numérique, la donnée reçue dans la Recipe est string.
**Règle à retenir** : Avant d'utiliser un champ de `Recipe` dans un nouveau composant, relire `apps/web/src/lib/api/types.ts` pour vérifier le type exact. Les champs `difficulty`, `dietary_tags` (pas `tags`), `total_time_minutes` (pas `total_time_min`) sont des pièges fréquents.
**Erreur potentielle évitée** : `useInfiniteQuery` agrège toutes les pages en mémoire — en remplaçant par `useQuery` + pagination classique, le `queryKey` doit inclure `page` sinon le cache retourne toujours la même page. Inclure `page` dans le `queryKey` est obligatoire.

---

## 2026-04-12 — Mismatch format ingrédients API brut vs type Ingredient frontend

**Erreur commise** : `IngredientList` attendait `{id, name, unit, note, category}` mais l'API catalogue retourne `{ingredient_id, canonical_name, unit, notes, position}`. Le composant tombait sur la branche vide (0 ingrédients) sans aucune erreur visible.
**Règle à retenir** : Toujours normaliser les données API dans la couche `fetchXxx()` côté serveur (Server Component) avant de les passer aux composants. Ne jamais adapter les composants UI au format brut de l'API — adapter dans la couche fetch.
**Comment l'éviter** : Lire le schéma Pydantic du backend (`RecipeIngredientOut`) avant d'écrire le type `Ingredient` TypeScript. Vérifier que chaque champ TS a un champ API correspondant.

## 2026-04-12 — has_next absent de la réponse API pagination recettes

**Erreur commise** : `getNextPageParam` utilisait `lastPage.has_next` qui n'existe pas dans la réponse `{results, total, page, per_page}` — `hasNextPage` était toujours `false`, infinite scroll jamais déclenché.
**Règle à retenir** : Toujours dériver `hasNextPage` depuis `totalLoaded < total` quand l'API ne retourne pas `has_next`. Ne jamais présupposer le format de pagination — le vérifier dans la réponse réseau réelle.
**Comment l'éviter** : Ajouter un bouton "Voir plus" visible en fallback de l'IntersectionObserver — permet de détecter visuellement si la pagination ne fonctionne pas.

---

## 2026-04-13 — Fix 5 bugs audit backend/DB (backend-developer)

**Erreur commise** : Premier script BUG 2 utilisait `ri.id` alors que `recipe_ingredients` a une cle composite `(recipe_id, ingredient_id)` sans colonne `id`.
**Regle a retenir** : Toujours lire le modele ORM (`apps/api/src/db/models/recipe.py`) avant d'ecrire du SQL sur les tables du catalogue. Les cles primaires composites ne sont pas evidentes.
**Comment l'eviter** : Verifier `__tablename__` + les `primary_key=True` dans le modele ORM.

**Erreur commise** : Le batch UPDATE via VALUES avec `::uuid` cast dans SQLAlchemy `text()` provoque une erreur de syntaxe asyncpg car `:` est interprete comme un parametre nomme.
**Regle a retenir** : Avec SQLAlchemy text() + asyncpg, eviter les casts `::type` dans des requetes dynamiques avec beaucoup de parametres. Utiliser une table temporaire + INSERT batch + UPDATE FROM a la place.
**Comment l'eviter** : Pour les mises a jour massives, toujours privilegier CREATE TEMP TABLE + INSERT par batch + UPDATE FROM (pattern fiable et performant).

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

## 2026-04-14 — Fix page /login bloquée indéfiniment sur le skeleton recettes (nextjs-developer)

**Erreur commise** : `LoginPage` était un Client Component (`"use client"`) qui appelait `useSearchParams()` directement dans le corps du composant export default, sans Suspense boundary. Next.js 14 App Router exige que tout composant utilisant `useSearchParams()` soit enveloppé dans `<Suspense>`. Sans ce wrapping, Next.js suspend l'hydratation de la page entière et utilise le `loading.tsx` le plus proche pour le streaming — qui était le `loading.tsx` root (skeleton grille de recettes), totalement inadapté à une page auth.

**Règle à retenir** : Chaque fois qu'un Client Component utilise `useSearchParams()`, `usePathname()`, ou tout hook de navigation qui lit les paramètres URL, il DOIT être dans un composant fils enveloppé par `<Suspense>`. L'export default de la page ne doit jamais appeler ces hooks directement — il doit se contenter de rendre `<Suspense fallback={...}><InnerComponent /></Suspense>`.

**Comment l'éviter** :
- Pattern systématique : `export default function XxxPage() { return <Suspense fallback={<XxxSkeleton />}><XxxForm /></Suspense>; }`
- `XxxForm` est le composant interne qui contient `useSearchParams()` et toute la logique
- `XxxSkeleton` doit avoir le même design que le layout parent (fond cream, carte blanche, etc.) — jamais réutiliser le loading.tsx root
- Toujours créer un `loading.tsx` dans chaque groupe de routes `(auth)`, `(dashboard)`, etc. pour court-circuiter le loading.tsx root inadapté
- Toujours créer un `error.tsx` dans chaque groupe pour un Error Boundary contextualisé

**Fichiers créés ou modifiés** :
- `apps/web/src/app/(auth)/login/page.tsx` — `LoginForm` + `LoginSkeleton` + `Suspense` wrapper
- `apps/web/src/app/(auth)/loading.tsx` — skeleton adapté au layout auth (fond cream, carte blanche)
- `apps/web/src/app/(auth)/error.tsx` — Error Boundary avec "Réessayer" + "Retour à l'accueil"

## 2026-04-13 — Debug bug critique : plan généré n'apparait jamais à l'écran (react-specialist)

**Erreur commise (Bug 1 — UTC/local mismatch dans getCurrentMonday)** :
`getCurrentMonday()` utilisait `today.getDay()` (heure locale) pour calculer le décalage, puis `toISOString()` (UTC) pour formater la date. Résultat : en UTC+1/+2, après minuit heure locale (ex : 00h30 lundi), `getDay()` retourne 1 (lundi) mais `toISOString()` retourne la date du dimanche UTC. Le backend enregistre le plan sous `week_start = dimanche UTC`, mais `GET /me/current` cherche le lundi UTC — le plan n'est jamais retrouvé.

**Règle à retenir** : Toute fonction qui calcule une date pour un backend UTC doit utiliser EXCLUSIVEMENT les méthodes UTC : `getUTCDay()`, `setUTCDate()`, `getUTCFullYear()`, `getUTCMonth()`, `getUTCDate()`. Ne jamais mélanger `getDay()` (local) avec `toISOString()` (UTC). Formatter manuellement `YYYY-MM-DD` via `getUTCFullYear/Month/Date` — jamais via `toISOString().split("T")[0]` si le calcul précédent utilise des méthodes locales.

**Comment l'éviter** : Ajouter un test unitaire pour `getCurrentMonday()` simulant l'heure 23h30 UTC (= minuit+heure locale UTC+1) et vérifier que la date retournée est bien le lundi UTC, pas le dimanche.

---

**Erreur commise (Bug 2 — onSuccess ignore la réponse et ne gère que le cas async)** :
`onSuccess` dans `useGeneratePlan` ignorait `_data` (le corps de la réponse). Si le backend génère le plan de façon synchrone et le retourne directement (PlanDetail complet au lieu de `{ task_id }`), le frontend lance quand même le polling, qui appelle `GET /me/current` — si ce endpoint a un comportement différent, le plan ne revient jamais. Et même si le plan est dans la réponse de la mutation, il est perdu.

**Règle à retenir** : Ne jamais nommer un paramètre `_data` dans `onSuccess` quand la réponse du backend peut contenir la donnée finale. Inspecter toujours `data` pour détecter si le backend est passé en mode synchrone. Pattern : vérifier si `data` contient un `id` (PlanDetail) ou un `task_id` (async) et traiter chaque cas séparément.

---

**Erreur commise (Bug 3 — `void queryClient.invalidateQueries()` avant `startPolling()`)** :
`invalidateQueries` était fire-and-forget (`void`). `startPolling` était appelé immédiatement après, de façon synchrone. Le premier refetch déclenché par `invalidateQueries` partait avec `refetchInterval: false` (car `isGenerating` était encore `false` dans le rendu courant). Ce refetch "orphelin" pouvait écraser le cache avant que le polling ne soit actif.

**Règle à retenir** : Quand `startPolling` (qui active `refetchInterval`) doit prendre effet AVANT le premier refetch forcé par `invalidateQueries`, enchaîner via `.then()` : `invalidateQueries(...).then(() => startPolling(...))`. Cela garantit que le rendu avec `isGenerating=true` et `refetchInterval=3000` est actif avant que le refetch ne parte.

---

**Règle générale retenue** : `startPolling` exposé depuis `useCurrentPlan` doit être wrappé dans `useCallback` pour éviter des références instables transmises à `useGeneratePlan`. Même si TanStack Query v5 re-lit les options à chaque render, une référence stable évite des re-renders inutiles en cascade dans les composants parents.

## 2026-04-14 — Diagnostic embeddings vides (591 recettes, 0 embedding) (backend-developer)

**Erreur commise (Bug 1 — CRITIQUE) : `embedder.embed()` n'existe pas** :
La tâche Celery `embed_recipe` dans `tasks.py` appelait `embedder.embed(text_to_embed)` (ligne 290). La méthode correcte est `embed_text()`. Cette erreur provoque un `AttributeError` à chaque exécution de la tâche, attrapé silencieusement par le `try/except Exception` du caller. Résultat : la Celery chain `validate → embed → tag` s'exécute sans crash visible mais n'insère rien dans `recipe_embeddings`.

**Règle à retenir** : Après toute refactorisation de méthode (rename), faire un grep global de l'ancien nom avant de committer. Pattern : `grep -r "embedder\.embed(" apps/worker/src/` pour vérifier qu'aucun appel résiduel subsiste. Les tâches Celery sont particulièrement dangereuses car elles ont des `try/except` larges pour survivre aux erreurs — un `AttributeError` peut passer sous le radar des logs si le caller le swallowe.

**Comment l'éviter** : Typer `RecipeEmbedder` avec Protocol ou Abstract Base Class pour que mypy détecte les appels à des méthodes inexistantes à la compilation. Ajouter un test d'intégration `test_embed_recipe_task` qui vérifie que la tâche insère réellement une ligne dans `recipe_embeddings` (pas seulement qu'elle ne crash pas).

---

**Erreur commise (Bug 2) : `_retrieve_by_quality` faisait un JOIN inutile sur `recipe_embeddings`** :
Le fallback "nouveaux foyers sans vecteur de goût" utilisait `JOIN recipe_embeddings re` pour filtrer sur `re.total_time_min` et `re.tags`. Comme `recipe_embeddings` est vide, ce fallback retourne 0 résultats → déclenchement du double-fallback `_retrieve_by_quality_no_embedding`. Ce chemin fonctionnait (grâce au double-fallback) mais de façon non intentionnelle et avec un log WARNING alarmant inutilement.

**Règle à retenir** : Un fallback qui ne joint pas une table facultative (embeddings) ne doit pas faire de JOIN sur cette table. `_retrieve_by_quality` est le fallback "sans embeddings" → il doit filtrer uniquement sur `recipes`. Les colonnes `total_time_min` et `tags` existent aussi sur `recipes` — pas besoin du JOIN.

**Comment l'éviter** : Tester le fallback avec une `recipe_embeddings` vide (état initial) dans les tests d'intégration. Un test `test_retrieve_by_quality_empty_embeddings_table` aurait détecté le JOIN inutile immédiatement.

---

**Erreur commise (Bug 3) : `import_sample_recipes.py` n'insère pas les embeddings** :
Le script de seed des 591 recettes insère dans `recipes` et `recipe_ingredients` mais pas dans `recipe_embeddings`. Les embeddings ne sont générés que par le pipeline Celery (`embed_recipe`). Comme le pipeline avait le Bug 1, aucun embedding n'a jamais été généré.

**Règle à retenir** : Tout script d'import de recettes (sample, Spoonacular, Marmiton) DOIT générer les embeddings si `sentence-transformers[ml]` est installé. Sinon, documenter explicitement que le backfill est requis après l'import. Le script de backfill `backfill_embeddings.py` est maintenant disponible pour corriger l'état actuel.

**Comment l'éviter** : Ajouter une vérification en fin de script : `SELECT COUNT(*) FROM recipes r LEFT JOIN recipe_embeddings re ON re.recipe_id = r.id WHERE re.recipe_id IS NULL` doit retourner 0. Si > 0, warning avec la commande de backfill.

---

## 2026-04-14 — Fix 3 bugs P1 frontend (IMP-04, IMP-05, IMP-08) — nextjs-developer

**IMP-04 — Quick filter écrasait les filtres sidebar via spread operator** :
La construction `{ ...filters, ...(activeQuickFilter === "dessert" && { diet: "dessert" }) }` écrasait silencieusement le champ `diet` déjà posé par la sidebar. Le spread operator avec une clé identique écrase la valeur précédente — jamais évident quand les deux branches touchent le même champ.
**Règle à retenir** : Quand un quick filter et un filtre avancé touchent le même champ (`diet`), fusionner explicitement les tableaux plutôt que d'utiliser le spread. Construire `activeFilters` dans une fonction dédiée `buildActiveFilters()` — plus lisible et testable qu'un objet littéral à 10 spreads conditionnels.

**IMP-05 — Tags FR/EN incompatibles entre frontend et DB** :
Le frontend envoyait des valeurs EN (`"gluten-free"`, `"lactose-free"`) mais la DB stocke des tags FR (`"sans-gluten"`, `"sans-lactose"`). Le mapping doit être côté API (serveur), pas côté frontend — le frontend ne connaît pas le format interne de la DB.
**Règle à retenir** : Tout mapping de valeurs liées à la langue (FR↔EN sur les tags, libellés d'enum) doit vivre côté API. Le frontend envoie ce qu'il affiche à l'utilisateur — c'est à l'API de normaliser. Placer le dict de mapping `_DIET_EN_TO_FR` au point d'utilisation, pas dans un fichier de config séparé — minimal et lisible.

**IMP-08 — Onboarding accessible sans auth (mauvaise UX 401 après submit)** :
Les routes `/onboarding/*` n'étaient pas dans `PROTECTED_ROUTES`. L'utilisateur remplissait tout le formulaire avant de recevoir un 401 — expérience catastrophique. La protection middleware est préférable à une vérification dans le layout (edge runtime = ultra rapide, redirect avant rendu).
**Règle à retenir** : Toute route qui appelle une API authentifiée DOIT être dans `PROTECTED_ROUTES` middleware. Vérifier systématiquement le middleware lors de l'ajout d'un nouveau groupe de routes `(onboarding)`, `(app)`, etc. La liste `PUBLIC_ROUTES` (commentaire documentation) ne doit jamais inclure des routes qui appellent des API protégées.
