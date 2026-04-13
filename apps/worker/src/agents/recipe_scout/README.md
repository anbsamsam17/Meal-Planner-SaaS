# RECIPE_SCOUT — Agent de collecte et enrichissement de recettes

## Role

Collecte des recettes depuis plusieurs sources (Marmiton scraping, Spoonacular API,
Edamam API), les normalise, les déduplique, les valide via LLM, les tague, et les
vectorise avant insertion en base PostgreSQL.

## Déclenchement

- **Batch nocturne** : chaque nuit à 02h00 via Celery Beat
  (`run_recipe_scout_nightly` → queue `default`)
- **À la demande** : appel direct de `RecipeScoutAgent().run()` pour les tests

## Inputs

| Paramètre | Type | Description |
|---|---|---|
| `url_list` | `list[str]` | URLs Marmiton à scraper |
| `max_recipes` | `int` | Limite de recettes par source (défaut 100) |
| `sources` | `list[str]` | Sources à activer (`marmiton`, `spoonacular`, `edamam`) |

## Outputs

Recettes normalisées insérées dans les tables PostgreSQL :
- `recipes` : métadonnées, instructions, temps, difficulté
- `recipe_ingredients` : ingrédients normalisés avec quantités
- `recipe_embeddings` : vecteur 384 dimensions (all-MiniLM-L6-v2)

## Pipeline interne

```
Sources (Scrapy Marmiton + Spoonacular API + Edamam API)
  |
  v
Normalisation (normalizer.py)
  — Ingrédients → format canonique (nom, unité, catégorie)
  — Slugification du titre
  — Calcul total_time_min
  |
  v
Déduplication (dedup.py)
  — Embedding temporaire du titre + ingrédients
  — Requête pgvector cosine similarity ≥ 0.92
  — Rejet si doublon trouvé
  |
  v
Validation qualité LLM (validator.py)
  — Appel Claude claude-sonnet-4-5
  — Score 0.0-1.0 sur complétude et cohérence
  — Rejet si score < 0.6 (règle ROADMAP non-négociable)
  |
  v
Tagging LLM (tagger.py)
  — Appel Claude pour extraction de tags structurés
  — cuisine, régime, temps, difficulté, budget
  |
  v
Embedding définitif (embedder.py)
  — sentence-transformers all-MiniLM-L6-v2
  — Dimension 384 — compatible pgvector
  |
  v
Insertion PostgreSQL (service_role → bypass RLS)
  — recipes, recipe_ingredients, recipe_embeddings
```

## Effets de bord

- Consomme des appels API Spoonacular (150 req/jour free tier)
- Consomme des appels API Edamam (surveillance quota)
- Appels Claude API (coût ~$0.003-0.015 par recette validée)
- Respecte les robots.txt Marmiton (throttling 1 req/s)
- Insère en DB via `SUPABASE_SERVICE_ROLE_KEY` (bypass RLS — agents Presto)

## Coûts estimés par nuit (100 recettes)

| Poste | Coût |
|---|---|
| Spoonacular API | ~$0 (free tier 150 req/j) |
| Claude validation (100 recettes) | ~$0.30-1.50 |
| Claude tagging (100 recettes) | ~$0.15-0.75 |
| sentence-transformers | $0 (local) |
| **Total** | **~$0.45-2.25/nuit** |

## Contraintes de qualité

- Toute recette avec `quality_score < 0.6` est **rejetée** avant insertion
- Toute recette dupliquée (cosine ≥ 0.92 avec une existante) est **ignorée**
- Les ingrédients sans `canonical_name` reconnu sont logués en WARNING

## Variables d'environnement requises

```bash
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_SERVICE_ROLE_KEY=...  # Bypass RLS pour insertion
ANTHROPIC_API_KEY=...          # Validation + tagging LLM
SPOONACULAR_API_KEY=...        # Source de recettes
EDAMAM_APP_ID=...
EDAMAM_APP_KEY=...
```

## Tests

```bash
uv run pytest apps/worker/tests/ -v
```

## Développement Phase 1 (TODO)

- [ ] Spider Allrecipes, NYT Cooking, 750g
- [ ] Mapping ingrédient → Open Food Facts
- [ ] Génération de photos via Stability AI
- [ ] Gestion des recettes existantes (UPDATE si nouvelle source de meilleure qualité)
- [ ] Couverture de tests à 80%+
