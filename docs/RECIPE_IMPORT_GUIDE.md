# Guide d'import de recettes — Presto (MealPlanner SaaS)

> Ce document est la **source de vérité** pour ajouter des recettes au catalogue.
> Une recette mal importée sera invisible dans les filtres, absente du planning
> hebdomadaire, ou cassera la liste de courses.

---

## Philosophie qualité — tolérance zéro

Presto est un **livre de recettes premium**. Chaque recette dans le catalogue doit
donner envie de cuisiner. L'utilisateur paie un abonnement — il attend un niveau
de curation comparable à un livre de cuisine professionnel, pas un dump de base
de données.

**Avant d'importer une recette, pose-toi ces 5 questions :**

| Question | Si la réponse est non → ne pas importer |
|----------|-----------------------------------------|
| Est-ce un **vrai bon plat** que je recommanderais à un ami ? | Pas de recettes médiocres, banales, ou de remplissage |
| La **photo** est-elle appétissante et de haute qualité ? | Pas d'image floue, mal cadrée, stock photo générique, ou absente |
| La recette est-elle **intégralement en français** ? | Titre, ingrédients, instructions — tout en FR. Pas de recettes EN non traduites |
| Les **valeurs nutritionnelles** sont-elles disponibles ? | Calories, protéines, glucides, lipides minimum. Presto affiche ces données |
| Les **instructions** sont-elles détaillées et testables ? | Pas de "faites cuire" sans temps ni température. Un débutant doit pouvoir suivre |

### Critères d'excellence obligatoires

**Langue :** Français uniquement. Les recettes importées depuis des sources anglaises
(TheMealDB, Spoonacular) **doivent être traduites** avant insertion. Le titre,
la description, les noms d'ingrédients et chaque étape des instructions doivent
être en français correct et naturel.

**Photo :** Chaque recette **doit** avoir une `photo_url` pointant vers une image :
- Haute résolution (minimum 800x600)
- Bien éclairée, appétissante, montrant le plat fini
- Pas de watermark, pas de stock photo générique
- Format paysage ou carré de préférence (rendu optimal sur les cards)

**Nutrition :** Le champ `nutrition` (JSONB) **doit** contenir au minimum :
```json
{
  "calories": 450,
  "protein_g": 32,
  "carbs_g": 45,
  "fat_g": 18,
  "fiber_g": 6
}
```
Sources fiables : Open Food Facts, Spoonacular nutrition API, tables Ciqual (ANSES).
En cas de doute, estimer à partir des ingrédients plutôt que laisser vide.

**Qualité du plat :** Importer uniquement des recettes qui sont :
- Des plats savoureux, testés, avec des proportions qui fonctionnent
- Variées (pas 15 variantes de pâtes carbonara)
- Réalisables par un cuisinier amateur avec du matériel standard
- Avec des ingrédients trouvables en supermarché français

**Instructions :** Chaque étape doit inclure :
- L'action précise (couper, faire revenir, enfourner...)
- Les temps et températures quand applicable
- Les indicateurs visuels ("jusqu'à dorure", "quand ça frémit")
- L'ordre logique avec numérotation

### Recettes à ne PAS importer

- Recettes en anglais non traduites
- Recettes sans photo ou avec photo de mauvaise qualité
- Recettes incomplètes (pas d'instructions, ingrédients vagues)
- Recettes avec des ingrédients introuvables en France
- Recettes dupliquées ou trop similaires à une existante
- Recettes "filler" qui n'apportent rien au catalogue (ex: "salade verte", "riz blanc")
- Recettes dont les proportions n'ont pas été vérifiées

---

## Table des matières

1. [Vue d'ensemble du pipeline](#1-vue-densemble-du-pipeline)
2. [Schéma de données obligatoire](#2-schéma-de-données-obligatoire)
3. [Tags — format et valeurs acceptées](#3-tags--format-et-valeurs-acceptées)
4. [Ingrédients — règles de canonicalisation](#4-ingrédients--règles-de-canonicalisation)
5. [Embeddings — recherche sémantique](#5-embeddings--recherche-sémantique)
6. [Méthodes d'import disponibles](#6-méthodes-dimport-disponibles)
7. [Checklist de validation](#7-checklist-de-validation)
8. [Erreurs fréquentes et pièges](#8-erreurs-fréquentes-et-pièges)

---

## 1. Vue d'ensemble du pipeline

```
Recette brute (JSON, API, scraping)
        │
        ▼
┌─────────────────┐
│  1. Validation   │  quality_score >= 0.6 (obligatoire, trigger DB)
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. Ingrédients  │  Canonicalisation + insertion dans `ingredients`
│                  │  Liaison via `recipe_ingredients` (quantité, unité, position)
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. Tags         │  Flat, sans préfixe : "vegan", "dessert", "économique"
│                  │  Alimentent TOUS les filtres frontend
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. Embedding    │  Vecteur 384-dim (all-MiniLM-L6-v2)
│                  │  Stocké dans `recipe_embeddings`
│                  │  Utilisé par le planificateur hebdomadaire
└────────┬────────┘
         ▼
   Recette opérationnelle
   (filtrable + planifiable + liste de courses)
```

**Si une étape manque :**

| Étape manquante | Conséquence |
|-----------------|-------------|
| `quality_score < 0.6` | INSERT rejeté par trigger DB |
| Pas de `recipe_ingredients` | Liste de courses vide pour cette recette |
| Tags absents ou préfixés | Recette invisible dans les filtres |
| Pas d'embedding | Planificateur utilise le fallback (quality_score), recette moins bien classée |

---

## 2. Schéma de données obligatoire

### Table `recipes`

| Colonne | Type | Obligatoire | Règles |
|---------|------|:-----------:|--------|
| `id` | UUID | Auto | Généré par `gen_random_uuid()` |
| `title` | TEXT | **OUI** | Titre lisible en français, pas "Recipe 1" |
| `slug` | TEXT | **OUI** | Unique, URL-safe. Ex: `poulet-roti-aux-herbes` |
| `source` | TEXT | **OUI** | Origine : `"spoonacular"`, `"marmiton"`, `"manual"`, `"sample"` |
| `source_url` | TEXT | Non | URL d'origine (attribution, debug) |
| `description` | TEXT | Non | Résumé court (1-2 phrases) |
| `instructions` | JSONB | **OUI** | Format : `[{"step": 1, "text": "Préchauffer le four..."}, ...]` |
| `servings` | INT | **OUI** | Nombre de portions (> 0). **Critique pour la liste de courses** |
| `prep_time_min` | INT | Non | Temps de préparation en minutes (>= 0) |
| `cook_time_min` | INT | Non | Temps de cuisson en minutes (>= 0) |
| `total_time_min` | INT | **Auto** | **NE PAS REMPLIR** — calculé par PostgreSQL : `prep + cook` |
| `difficulty` | INT | Non | 1 à 5 (1=très facile, 5=expert) |
| `cuisine_type` | TEXT | Non | Type de cuisine en français. Ex: `"française"`, `"italienne"` |
| `photo_url` | TEXT | **OUI** | URL haute qualité (min 800x600), appétissante, plat fini visible |
| `nutrition` | JSONB | **OUI** | `{"calories": N, "protein_g": N, "carbs_g": N, "fat_g": N, "fiber_g": N}` |
| `tags` | TEXT[] | **OUI** | Voir section 3. **Format strict obligatoire** |
| `quality_score` | NUMERIC | **OUI** | **>= 0.6** sinon rejeté. Plage : 0.00 à 1.00 |

**Contraintes critiques :**
- `quality_score >= 0.6` : un **trigger PostgreSQL** rejette toute recette en dessous
- `total_time_min` : colonne **GENERATED ALWAYS** — ne jamais l'inclure dans un INSERT/UPDATE
- `slug` : **UNIQUE** — un doublon cause `ON CONFLICT DO NOTHING` (recette ignorée silencieusement)
- `servings` : doit être > 0 — utilisé comme diviseur pour le scaling de la liste de courses

### Table `ingredients`

| Colonne | Type | Obligatoire | Règles |
|---------|------|:-----------:|--------|
| `id` | UUID | Auto | |
| `canonical_name` | TEXT | **OUI** | **UNIQUE.** Singulier, minuscule. Ex: `"carotte"` pas `"Carottes"` |
| `category` | TEXT | **OUI** | Catégorie rayon. Défaut: `"other"` |
| `unit_default` | TEXT | **OUI** | Unité de base. Défaut: `"g"` |

**Catégories valides :** `vegetables`, `fruits`, `meat`, `fish`, `dairy`, `grains`, `legumes`, `condiments`, `herbs`, `other`

### Table `recipe_ingredients` (liaison)

| Colonne | Type | Obligatoire | Règles |
|---------|------|:-----------:|--------|
| `recipe_id` | UUID | **OUI** | FK → `recipes.id` (CASCADE) |
| `ingredient_id` | UUID | **OUI** | FK → `ingredients.id` (RESTRICT) |
| `quantity` | NUMERIC(10,3) | **OUI** | Doit être > 0 |
| `unit` | TEXT | **OUI** | Unité normalisée (voir tableau ci-dessous) |
| `notes` | TEXT | Non | Ex: `"finement haché"`, `"optionnel"` |
| `position` | INT | **OUI** | Ordre d'affichage (0, 1, 2, ...) |

**Clé primaire composite :** `(recipe_id, ingredient_id)` — un ingrédient ne peut apparaître qu'une fois par recette.

**Unités normalisées :**

| Unité | Signification | Exemple |
|-------|---------------|---------|
| `g` | grammes | 200g de farine |
| `kg` | kilogrammes | 1.5kg de pommes de terre |
| `ml` | millilitres | 100ml de lait |
| `cl` | centilitres | 25cl de crème |
| `l` | litres | 1l d'eau |
| `u` | unité / pièce | 3 oeufs, 1 oignon |
| `cs` | cuillère à soupe | 2 cs d'huile |
| `cc` | cuillère à café | 1 cc de sel |

### Table `recipe_embeddings` (1:1 avec recipes)

| Colonne | Type | Obligatoire | Règles |
|---------|------|:-----------:|--------|
| `recipe_id` | UUID | **OUI** | PK, FK → `recipes.id` (CASCADE) |
| `embedding` | vector(384) | **OUI** | Vecteur pgvector, modèle `all-MiniLM-L6-v2` |
| `tags` | TEXT[] | **OUI** | **Copie dénormalisée** de `recipes.tags` |
| `total_time_min` | INT | Non | **Copie dénormalisée** de `recipes.total_time_min` |
| `difficulty` | INT | Non | **Copie dénormalisée** |
| `cuisine_type` | TEXT | Non | **Copie dénormalisée** |

> Un trigger PostgreSQL `recipe_embeddings_sync_metadata` synchronise automatiquement
> les colonnes dénormalisées quand `recipes` est modifié. Mais l'embedding lui-même
> doit être généré explicitement.

---

## 3. Tags — format et valeurs acceptées

### Règles de format (non négociables)

```
✅ CORRECT : tags = ARRAY['vegan', 'dessert', 'économique', 'rapide']
❌ FAUX    : tags = ARRAY['regime:vegan', 'occasion:dessert']     -- préfixe cassé
❌ FAUX    : tags = ARRAY['sans_gluten']                          -- underscore au lieu de tiret
❌ FAUX    : tags = ARRAY['Vegan', 'DESSERT']                     -- majuscules
```

**Règles :**
1. **Pas de préfixe** (`regime:`, `occasion:`, `budget:`, `cuisine:`) — les filtres font `= ANY(tags)` directement
2. **Tirets**, pas underscores : `sans-gluten` pas `sans_gluten`
3. **Minuscules** : `vegan` pas `Vegan`
4. **Français** : `végétarien` pas `vegetarian` (le backend normalise les tags EN→FR venant du frontend)

### Tags reconnus par les filtres

#### Régime alimentaire (filtres frontend)

| Tag DB | Label frontend | Filtre envoyé |
|--------|----------------|---------------|
| `végétarien` | Végétarien | `diet=végétarien` |
| `vegan` | Vegan | `diet=vegan` |
| `sans-gluten` | Sans gluten | `diet=gluten-free` → normalisé en `sans-gluten` |
| `sans-lactose` | Sans lactose | `diet=lactose-free` → normalisé en `sans-lactose` |
| `sans-porc` | Sans porc | `diet=no-pork` → normalisé en `sans-porc` |
| `sans-fruits-de-mer` | Sans fruits de mer | `diet=no-seafood` → normalisé |
| `sans-fruits-à-coque` | Sans fruits à coque | `diet=nut-free` → normalisé |
| `halal` | Halal | `diet=halal` |

#### Budget (filtres frontend)

| Tag DB | Label frontend |
|--------|----------------|
| `économique` | Économique |
| `moyen` | Moyen |
| `premium` | Premium |

#### Catégorie de plat (quick filter + explorateur)

| Tag DB | Usage |
|--------|-------|
| `dessert` | Quick filter "Desserts" dans l'explorateur |
| `plat` | Plat principal (viande/poisson/protéine) |
| `entrée` | Salade, soupe, velouté, tartare, etc. |
| `accompagnement` | Purée, gratin, riz, légumes rôtis, etc. |
| `petit-déjeuner` | Porridge, smoothie, granola, pancake, etc. |

#### Saison (tags DB, pas encore de filtre frontend)

| Tag DB | Saison |
|--------|--------|
| `hiver` | Hiver |
| `printemps` | Printemps |
| `ete` | Été |
| `automne` | Automne |

#### Tags libres (non filtrés, mais utilisés pour l'embedding)

Exemples : `rapide`, `familial`, `classique`, `comfort-food`, `one-pot`, `batch-cooking`

### Comment attribuer les tags ?

**Option A — Automatique (recommandé) :** Le tagger LLM (`tagger.py`) génère les tags via Gemini 2.0 Flash. Utilisé par le recipe_scout et l'import Spoonacular.

**Option B — Manuel :** Lors d'un import SQL ou JSON, attribuer les tags selon ces critères :

| Tag | Critère d'attribution |
|-----|----------------------|
| `végétarien` | Aucun ingrédient viande, poisson, ou fruits de mer |
| `vegan` | Végétarien + aucun produit animal (oeuf, lait, beurre, fromage, miel) |
| `sans-gluten` | Aucun blé, farine, pâtes, pain, couscous, semoule, orge, seigle, avoine |
| `sans-lactose` | Aucun lait, beurre, crème, fromage, yaourt |
| `sans-porc` | Aucun porc, bacon, jambon, lard, saucisse, chorizo, pancetta |
| `sans-fruits-de-mer` | Aucune crevette, moule, huître, crabe, homard, calamari |
| `sans-fruits-à-coque` | Aucune noix, amande, noisette, cajou, pistache, cacahuète, sésame |
| `halal` | Sans-porc + aucun alcool (vin, bière, rhum, etc.) |
| `économique` | <= 6 ingrédients ET difficulté <= 2 |
| `moyen` | 7 à 10 ingrédients |
| `premium` | > 10 ingrédients OU difficulté >= 4 |
| `dessert` | Titre contient cake/gâteau/tarte/mousse/tiramisu/chocolat/etc. |
| `plat` | Contient une protéine principale (viande, poisson, tofu, légumineuses) |
| `entrée` | Salade, soupe, velouté, bruschetta, carpaccio, etc. |

**Option C — Scripts SQL post-import :** Exécuter les scripts dans cet ordre après un import brut :

```bash
# 1. Tags régime + budget (analyse des ingrédients)
scripts/add_diet_budget_tags.sql

# 2. Tags saisonniers
scripts/add_seasonal_tags.sql

# 3. Tags manquants (restrictions + catégories)
scripts/add_missing_tags.sql
```

---

## 4. Ingrédients — règles de canonicalisation

### Pourquoi c'est critique

La **liste de courses** agrège les quantités par `canonical_name`. Si la même chose est nommée différemment dans deux recettes, l'utilisateur verra deux lignes au lieu d'une :

```
❌ "farine" (200g) + "farine de blé" (150g) = 2 lignes séparées
✅ "farine" (200g) + "farine" (150g) = "farine (350g)" consolidé
```

### Règles de canonicalisation

| Règle | Exemple |
|-------|---------|
| **Singulier** | `carotte` pas `carottes` |
| **Minuscule** | `carotte` pas `Carotte` |
| **Sans quantité** | `farine` pas `200g farine` |
| **Nom générique** | `poulet` pas `blancs de poulet fermier bio` |
| **Français** | `beurre` pas `butter` (sauf si source EN uniquement) |
| **Conserver les accents** | `crème` pas `creme` |

### Processus d'insertion

```
1. Recevoir l'ingrédient brut : "200 g de farine T55 (tamisée)"
2. Parser :
   - quantity = 200
   - unit = "g"
   - raw_name = "farine T55 (tamisée)"
3. Canonicaliser :
   - Retirer parenthèses : "farine T55"
   - Minuscule + trim : "farine t55"
   - Simplifier : "farine"
4. Chercher dans `ingredients` WHERE canonical_name = 'farine'
   - Trouvé → utiliser l'id existant
   - Pas trouvé → INSERT INTO ingredients (canonical_name, category, unit_default)
5. INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, position)
```

### Table de synonymes courante

| Variantes | canonical_name |
|-----------|----------------|
| poule, poulet, volaille | `poulet` |
| boeuf, bœuf | `boeuf` |
| huile d'olive, olive oil | `huile d'olive` |
| oignon, oignon jaune | `oignon` |
| ail, gousse d'ail | `ail` |
| sel, sel fin, sel de mer | `sel` |
| poivre, poivre noir, poivre moulu | `poivre` |

---

## 5. Embeddings — recherche sémantique

### Modèle

- **all-MiniLM-L6-v2** (sentence-transformers)
- Dimension : **384**
- Coût : **gratuit** (modèle local)
- Vitesse : ~5ms/recette en CPU

### Texte source de l'embedding

```python
"{title} | cuisine {cuisine_type} | {tags[:5]} | ingrédients : {ingredients[:10]}"
```

Exemple :
```
"Poulet rôti aux herbes | cuisine française | économique rapide plat | ingrédients : poulet, herbes de provence, huile d'olive, ail, sel"
```

### Comment les générer

**Automatique (recipe_scout) :** L'embedding est généré en même temps que la recette.

**Backfill (recettes existantes sans embedding) :**
```bash
cd apps/worker
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  uv run python -m src.scripts.backfill_embeddings \
  BATCH_SIZE=32 \
  DRY_RUN=false
```

### Impact sur le planificateur

| Embedding présent | Comportement du planificateur |
|:-----------------:|-------------------------------|
| **Oui** | Recherche par similarité HNSW (personnalisée au profil de goûts du foyer) |
| **Non** | Fallback sur `ORDER BY quality_score DESC, RANDOM()` (aléatoire pondéré) |

Le planificateur fonctionne **sans embeddings**, mais les suggestions sont moins personnalisées.

---

## 6. Méthodes d'import disponibles

### A. Import Spoonacular (API)

```bash
cd apps/worker
DATABASE_URL=postgresql+asyncpg://... \
SPOONACULAR_API_KEY=... \
  uv run python -m src.scripts.import_spoonacular \
  MAX_RECIPES=50 \
  CUISINES=french,italian \
  DRY_RUN=false
```

- Quality score : 0.80 (hardcodé)
- Tags : générés automatiquement par heuristiques
- Ingrédients : parsés depuis `extendedIngredients`
- Embedding : **non généré** → lancer `backfill_embeddings.py` après

### B. Import JSON manuel

```bash
cd apps/worker
DATABASE_URL=postgresql+asyncpg://... \
  uv run python -m src.scripts.import_sample_recipes \
  DRY_RUN=false
```

Format du fichier `sample_recipes.json` :
```json
[
  {
    "title": "Poulet rôti aux herbes de Provence",
    "description": "Un classique dominical simple et savoureux, doré à la perfection.",
    "servings": 4,
    "prep_time_min": 15,
    "cook_time_min": 60,
    "difficulty": "facile",
    "cuisine_type": "française",
    "photo_url": "https://images.unsplash.com/photo-example-poulet-roti.jpg",
    "nutrition": {
      "calories": 380,
      "protein_g": 42,
      "carbs_g": 2,
      "fat_g": 22,
      "fiber_g": 0.5
    },
    "tags": ["plat", "économique", "sans-gluten", "sans-fruits-de-mer", "hiver"],
    "ingredients": [
      "1 poulet entier (~1.5 kg)",
      "3 cs d'huile d'olive",
      "2 gousses d'ail",
      "1 cc d'herbes de Provence",
      "sel, poivre"
    ],
    "instructions": [
      "Préchauffer le four à 200°C (thermostat 6-7).",
      "Frotter le poulet avec l'huile d'olive, l'ail écrasé et les herbes de Provence. Saler et poivrer généreusement.",
      "Placer dans un plat à rôtir et enfourner pendant 1h en arrosant avec le jus toutes les 20 minutes.",
      "Le poulet est prêt quand le jus de cuisson est clair (piquer la cuisse). Laisser reposer 10 minutes avant de découper."
    ]
  }
]
```

> **Rappel :** `photo_url` et `nutrition` sont **obligatoires**. Une recette sans
> photo appétissante ou sans données nutritionnelles ne doit pas être importée.

- Quality score : 1.0 (recettes manuelles curatées)
- Tags : ceux fournis dans le JSON (doivent respecter le format section 3)
- Embedding : **non généré** → lancer `backfill_embeddings.py` après

### C. Recipe Scout (agent automatique)

Le recipe scout fait tout automatiquement :
1. Scrape/API → collecte les recettes
2. Validation LLM → quality_score
3. Normalisation → ingrédients canoniques
4. Tagging LLM → tags structurés
5. Embedding → vecteur 384-dim
6. Insertion → tout en une transaction

Rien à faire manuellement.

### D. Import SQL direct

Pour insérer directement dans Supabase SQL Editor :

```sql
-- 1. Insérer la recette
INSERT INTO recipes (
  id, title, slug, source, description, instructions,
  servings, prep_time_min, cook_time_min, difficulty,
  cuisine_type, photo_url, nutrition, tags, quality_score
) VALUES (
  gen_random_uuid(),
  'Poulet rôti aux herbes',
  'poulet-roti-aux-herbes',
  'manual',
  'Un classique dominical.',
  '[{"step": 1, "text": "Préchauffer le four à 200°C."},
    {"step": 2, "text": "Frotter le poulet avec les herbes."},
    {"step": 3, "text": "Enfourner 1h."}]'::jsonb,
  4,        -- servings
  15,       -- prep_time_min
  60,       -- cook_time_min
  2,        -- difficulty (1-5)
  'française',
  'https://images.unsplash.com/photo-example-poulet-roti.jpg',
  '{"calories": 380, "protein_g": 42, "carbs_g": 2, "fat_g": 22, "fiber_g": 0.5}'::jsonb,
  ARRAY['plat', 'économique', 'sans-gluten', 'hiver'],
  0.85      -- quality_score (>= 0.6 obligatoire)
)
RETURNING id;
-- → noter l'id retourné, ex: 'abc-123-...'

-- 2. Insérer les ingrédients (upsert — idempotent)
INSERT INTO ingredients (id, canonical_name, category, unit_default)
VALUES
  (gen_random_uuid(), 'poulet', 'meat', 'g'),
  (gen_random_uuid(), 'huile d''olive', 'condiments', 'ml'),
  (gen_random_uuid(), 'ail', 'vegetables', 'u'),
  (gen_random_uuid(), 'herbes de provence', 'herbs', 'g'),
  (gen_random_uuid(), 'sel', 'condiments', 'g')
ON CONFLICT (canonical_name) DO NOTHING;

-- 3. Lier les ingrédients à la recette
INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, position)
SELECT
  'abc-123-...'::uuid,  -- ← remplacer par l'id de l'étape 1
  i.id,
  v.quantity,
  v.unit,
  v.position
FROM (VALUES
  ('poulet', 1500, 'g', 0),
  ('huile d''olive', 45, 'ml', 1),
  ('ail', 2, 'u', 2),
  ('herbes de provence', 5, 'g', 3),
  ('sel', 5, 'g', 4)
) AS v(canonical_name, quantity, unit, position)
JOIN ingredients i ON i.canonical_name = v.canonical_name;
```

**Après un import SQL, lancer les scripts de tagging :**
```sql
-- Dans Supabase SQL Editor, dans cet ordre :
-- 1. scripts/add_diet_budget_tags.sql
-- 2. scripts/add_seasonal_tags.sql
-- 3. scripts/add_missing_tags.sql
```

**Puis backfill les embeddings :**
```bash
cd apps/worker
DATABASE_URL=... uv run python -m src.scripts.backfill_embeddings DRY_RUN=false
```

---

## 7. Checklist de validation

Après chaque import, vérifier ces points :

### Qualité et complétude ?

```sql
-- Recettes sans photo (interdit)
SELECT id, title FROM recipes WHERE photo_url IS NULL OR photo_url = '';
-- → doit retourner 0 lignes

-- Recettes sans nutrition (interdit)
SELECT id, title FROM recipes WHERE nutrition IS NULL OR nutrition = '{}'::jsonb;
-- → doit retourner 0 lignes

-- Recettes sans instructions (interdit)
SELECT id, title FROM recipes WHERE instructions IS NULL OR instructions = '[]'::jsonb;
-- → doit retourner 0 lignes

-- Recettes en anglais (titre contient des mots EN courants)
SELECT id, title FROM recipes
WHERE title ~* '\m(chicken|beef|pork|cake|salad|soup|roasted|grilled|baked)\M'
  AND title !~* '\m(poulet|boeuf|porc|gâteau|salade|soupe|rôti|grillé)\M';
-- → vérifier manuellement et traduire si nécessaire

-- Recettes avec quality_score faible (proche du seuil)
SELECT id, title, quality_score FROM recipes
WHERE quality_score < 0.7
ORDER BY quality_score;
-- → considérer supprimer ou améliorer ces recettes
```

### Recette visible dans les filtres ?

```sql
-- Vérifier que la recette a les bons tags
SELECT id, title, tags, quality_score
FROM recipes
WHERE slug = 'poulet-roti-aux-herbes';

-- Vérifier que les tags sont dans le bon format (pas de préfixe, pas d'underscore)
SELECT id, title, tag
FROM recipes, UNNEST(tags) AS tag
WHERE tag LIKE 'regime:%'
   OR tag LIKE 'occasion:%'
   OR tag LIKE 'budget:%'
   OR tag LIKE '%\_%';  -- underscore
-- → doit retourner 0 lignes
```

### Ingrédients correctement liés ?

```sql
-- Doit retourner >= 1 ligne par recette
SELECT r.title, COUNT(ri.*) AS nb_ingredients
FROM recipes r
LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
WHERE r.slug = 'poulet-roti-aux-herbes'
GROUP BY r.title;
-- → nb_ingredients doit être > 0

-- Vérifier les quantités et unités
SELECT i.canonical_name, ri.quantity, ri.unit, ri.position
FROM recipe_ingredients ri
JOIN ingredients i ON i.id = ri.ingredient_id
WHERE ri.recipe_id = (SELECT id FROM recipes WHERE slug = 'poulet-roti-aux-herbes')
ORDER BY ri.position;
```

### Embedding présent ?

```sql
-- Vérifier la présence d'un embedding
SELECT r.title,
       CASE WHEN re.recipe_id IS NOT NULL THEN 'OUI' ELSE 'NON' END AS has_embedding
FROM recipes r
LEFT JOIN recipe_embeddings re ON re.recipe_id = r.id
WHERE r.slug = 'poulet-roti-aux-herbes';
```

### Éligible pour le planificateur ?

```sql
-- La recette doit passer TOUS ces critères pour être sélectionnée par le planner
SELECT
  title,
  quality_score >= 0.6 AS "quality OK",
  tags IS NOT NULL AND array_length(tags, 1) > 0 AS "tags OK",
  servings > 0 AS "servings OK",
  instructions != '[]'::jsonb AS "instructions OK"
FROM recipes
WHERE slug = 'poulet-roti-aux-herbes';
-- → toutes les colonnes doivent être TRUE
```

### Comptage global des tags

```sql
-- Audit des tags après import
SELECT tag, COUNT(*) AS nb_recettes
FROM recipes, UNNEST(tags) AS tag
WHERE tag IN (
  'végétarien', 'vegan', 'sans-porc', 'halal',
  'sans-gluten', 'sans-lactose', 'sans-fruits-de-mer', 'sans-fruits-à-coque',
  'économique', 'moyen', 'premium',
  'dessert', 'plat', 'entrée', 'accompagnement', 'petit-déjeuner',
  'hiver', 'printemps', 'ete', 'automne'
)
GROUP BY tag
ORDER BY nb_recettes DESC;
```

---

## 8. Erreurs fréquentes et pièges

### "La recette n'apparaît pas dans les filtres"

| Cause probable | Vérification | Fix |
|----------------|--------------|-----|
| `quality_score < 0.6` | `SELECT quality_score FROM recipes WHERE slug = '...'` | Mettre à jour à >= 0.6 |
| Tags avec préfixe | `SELECT tag FROM ..., UNNEST(tags) AS tag WHERE tag LIKE '%:%'` | Exécuter `add_missing_tags.sql` bloc 3 |
| Tags avec underscore | `WHERE tag LIKE '%\_%'` | Remplacer `_` par `-` |
| Tag absent | `SELECT tags FROM recipes WHERE slug = '...'` | Exécuter les scripts SQL de tagging |

### "La liste de courses est vide"

| Cause probable | Vérification | Fix |
|----------------|--------------|-----|
| Pas de `recipe_ingredients` | `SELECT COUNT(*) FROM recipe_ingredients WHERE recipe_id = '...'` | Insérer les liaisons |
| `quantity` = NULL ou 0 | `SELECT * FROM recipe_ingredients WHERE quantity IS NULL OR quantity <= 0` | Corriger les quantités |
| `servings` = 0 | `SELECT servings FROM recipes WHERE ...` | Mettre à jour servings > 0 |

### "Le planificateur ne sélectionne jamais cette recette"

| Cause probable | Vérification | Fix |
|----------------|--------------|-----|
| `quality_score < 0.6` | Voir ci-dessus | Augmenter le score |
| Recette planifiée récemment | Anti-repeat 3 semaines | Attendre |
| Tags exclus par le foyer | Vérifier les allergies du foyer | Normal |
| Pas d'embedding | `SELECT * FROM recipe_embeddings WHERE recipe_id = '...'` | Lancer `backfill_embeddings.py` |

### "INSERT rejeté par le trigger"

```
ERROR: Recette rejetée : quality_score=0.45 insuffisant (seuil=0.6)
```

→ Le trigger `validate_recipe_quality` rejette tout INSERT/UPDATE avec `quality_score < 0.6`. Augmenter le score ou désactiver temporairement le trigger (non recommandé).

### "total_time_min error on INSERT"

```
ERROR: column "total_time_min" can only be updated to DEFAULT
```

→ `total_time_min` est une colonne **GENERATED ALWAYS**. Ne jamais l'inclure dans un INSERT ou UPDATE. PostgreSQL la calcule automatiquement.

### "duplicate key value violates unique constraint on slug"

→ Une recette avec ce slug existe déjà. Si c'est un import batch, utiliser `ON CONFLICT (slug) DO NOTHING` ou `DO UPDATE SET`.
