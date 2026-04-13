# Agent WEEKLY_PLANNER

Documentation de l'agent de génération de plans hebdomadaires.

---

## Vue d'ensemble

L'agent `WEEKLY_PLANNER` génère un plan de 5 dîners personnalisés pour un foyer,
en tenant compte des contraintes alimentaires de tous les membres, de leur historique,
et de leur vecteur de goût.

Le chemin nominal n'appelle **pas** de LLM — il repose sur la recherche vectorielle
pgvector (HNSW) et un scoring heuristique. Le LLM (Claude) intervient uniquement
en fallback si moins de 5 recettes éligibles sont trouvées.

---

## Inputs

| Paramètre | Type | Description |
|---|---|---|
| `household_id` | `UUID` | Identifiant du foyer (clé de tenant). |
| `week_start` | `date` | Lundi de la semaine cible (ISO 8601, ISODOW=1 vérifié). |
| `num_dinners` | `int` | Nombre de dîners à planifier (défaut : 5, plage : 3–7). |

### Sources de données lues

- `household_members` — liste des membres du foyer.
- `member_preferences` — régimes, allergies, aversions, temps de cuisson max, budget.
- `member_taste_vectors` — vecteur de goût 384 dims (résultat agrégé TASTE_PROFILE).
- `planned_meals` (3 dernières semaines) — anti-répétition.
- `fridge_items` — exclusion des ingrédients déjà en stock.
- `recipes` + `recipe_embeddings` + `recipe_ingredients` — corpus de recettes éligibles.

---

## Outputs

### `WeeklyPlanResult` (objet Python)

```python
@dataclass
class WeeklyPlanResult:
    plan_id: str               # UUID du plan inséré en base
    household_id: str
    week_start: date
    selected_recipes: list[ScoredRecipe]  # 5 recettes scorées
    shopping_list: list[dict]  # Items consolidés par rayon
    constraints: HouseholdConstraints | None
    used_llm_fallback: bool    # True si Claude a été sollicité
    errors: list[str]
```

### Structure JSON retournée par la tâche Celery

```json
{
  "status": "completed",
  "plan_id": "uuid",
  "household_id": "uuid",
  "week_start": "2026-04-14",
  "recipes_count": 5,
  "shopping_items_count": 23,
  "used_llm_fallback": false,
  "errors_count": 0,
  "duration_seconds": 1.42
}
```

---

## Effets de bord (écriture base de données)

L'agent persiste **3 tables** dans une seule transaction atomique :

1. **`weekly_plans`** — ligne de plan (household_id, week_start, status='draft').
2. **`planned_meals`** — 1 ligne par dîner (day_of_week 1–7, slot='dinner', recipe_id).
3. **`shopping_lists`** — 1 ligne avec la liste de courses JSONB consolidée.

Si la transaction échoue, aucune donnée partielle n'est écrite (rollback complet).

---

## Pipeline interne

```
build_household_constraints()
        ↓
retrieve_candidate_recipes()   ← pgvector HNSW ORDER BY distance
        ↓
score_candidates()             ← quality_score, cuisine_diversity, temps, enfants
        ↓
select_diverse_plan()          ← max 2 recettes par type de cuisine
        ↓
build_shopping_list()          ← consolidation unités, groupement rayons, exclusion frigo
        ↓
_persist_plan()                ← INSERT atomique weekly_plans + planned_meals + shopping_lists
```

---

## Agrégation des contraintes

| Contrainte | Règle d'agrégation |
|---|---|
| `diet_tags` | UNION de tous les membres (le plus restrictif gagne). |
| `allergies` | UNION de tous les membres. |
| `dislikes` | UNION de tous les membres. |
| `cooking_time_max` | MINIMUM parmi les membres ayant défini une limite. |
| `budget_pref` | MINIMUM (économique < moyen < premium). |

---

## Coûts estimés

| Ressource | Chemin nominal | Avec fallback LLM |
|---|---|---|
| Appels LLM | 0 | 1 appel Claude claude-3-5-haiku |
| Coût LLM | 0 € | ~0.05 € par plan |
| Durée | ~500 ms | ~3–8 s |
| Requêtes SQL | ~6 requêtes | ~6 requêtes + 1 appel API |

Le fallback LLM est déclenché uniquement quand `len(candidates) < num_dinners`
après filtrage des contraintes et de l'anti-répétition (cas rare).

---

## Tâche Celery

```python
# Déclenchement depuis l'API
from src.agents.weekly_planner.tasks import generate_plan_task

task = generate_plan_task.apply_async(
    kwargs={
        "household_id": str(household_id),
        "week_start_iso": "2026-04-14",
        "num_dinners": 5,
    },
    queue="llm",
)
```

- **Queue** : `llm` (partagée avec RECIPE_SCOUT validate/embed — à séparer en Phase 2).
- **Timeout** : 300 s (soft) / 600 s (hard).
- **Retry** : 2 tentatives, backoff exponentiel, sur `Exception` uniquement.
- **Idempotence** : une double exécution crée un second plan `draft` — idempotence à gérer côté API (409 si plan déjà existant pour la semaine en Phase 2).

---

## Limitations Phase 0 (MVP)

- Pas de personnalisation par slot (déjeuner/dîner) — uniquement `slot='dinner'`.
- Pas de planification petits-déjeuners / déjeuners.
- Pas de recettes suggérées par Claude dans le chemin nominal.
- La diversité nutritionnelle n'est pas vérifiée (scores uniquement heuristiques).
- `used_llm_fallback` est toujours `False` en v0 (stub).
