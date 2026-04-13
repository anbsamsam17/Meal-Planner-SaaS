# TASTE_PROFILE v0 — Moteur de recommandation personnalisé

## Role

Met à jour le vecteur de goût de chaque membre à partir de ses feedbacks
sur les recettes. Ce vecteur est utilisé par le WEEKLY_PLANNER pour
prioriser les recettes les plus proches des préférences de l'utilisateur.

## Inputs

- `recipe_feedbacks` : table des interactions utilisateur (rating, skip, favori)
- `recipe_embeddings` : vecteurs 384 dims des recettes (all-MiniLM-L6-v2)

## Outputs

- `member_taste_vectors` : vecteur de goût normalisé (384 dims) par membre

## Algorithme v0 — Content-based filtering simple

```
Pour chaque feedback du membre :
  1. Récupère l'embedding de la recette (384 dims depuis recipe_embeddings)
  2. Applique un poids selon le type de feedback :
     - "favorited"          → poids +1.0 (signal fort positif)
     - "cooked" + rating>=4 → poids +0.8
     - "cooked" + rating<4  → poids +0.4 (signal faible)
     - "skipped"            → poids -0.2 (signal légèrement négatif)
  3. Calcule la moyenne pondérée de tous les vecteurs
  4. Normalise (norme L2) → vecteur unitaire 384 dims
  5. UPSERT dans member_taste_vectors
```

## Déclenchement

- **Après chaque feedback** : tâche Celery `taste_profile.update_member_taste`
  déclenchée depuis `POST /api/v1/feedbacks`
- **Queue** : `embedding` (même ressources CPU/numpy que les embeddings)
- **Durée estimée** : < 2 secondes (quelques dizaines de feedbacks)

## Limitations v0

Ces limitations sont documentées et prévues pour Phase 2 :

- **Cold-start** : pas de recommandation si aucun feedback (retourne `no_feedback`)
- **Poids statiques** : pas d'apprentissage — les poids sont définis en dur
- **Pas de décroissance temporelle** : un feedback ancien pèse autant qu'un récent
- **Pas de collaborative filtering** : pas de "utilisateurs similaires"

## Tables modifiées

```sql
-- Mise à jour ou création du vecteur de goût
INSERT INTO member_taste_vectors (member_id, taste_vector, num_feedbacks_used, updated_at)
ON CONFLICT (member_id) DO UPDATE SET ...
```

## Tests

```bash
cd apps/worker
uv run pytest tests/agents/taste_profile/ -v
```

## Usage manuel

```python
from uuid import UUID
from src.agents.taste_profile.agent import TasteProfileAgent

agent = TasteProfileAgent()
result = await agent.run(member_id=UUID("..."))
# {"status": "updated", "vector_updated": True, "num_feedbacks": 12}
```
