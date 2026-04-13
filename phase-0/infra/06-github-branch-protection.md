# Règles de protection des branches — MealPlanner SaaS

> Ce document décrit la stratégie de branches et les règles de protection à configurer
> manuellement dans GitHub (Settings > Branches > Branch protection rules).
> Ces règles ne peuvent pas être entièrement automatisées sans GitHub Enterprise ou
> un provider Terraform GitHub.

---

## Stratégie de branches

```
main
 │  Production — protégée, deploy auto sur Railway prod + Vercel prod
 │  Ne jamais committer directement sur main
 │
staging
 │  Staging — protégée, deploy auto sur Railway staging + Vercel preview
 │  Intégration continue : merge de feature branches via PR
 │
dev
    Développement — ouverte, pas de protection
    Sandbox d'expérimentation, jamais mergée directement sur main
```

### Flux de travail (GitFlow simplifié)

```
feature/ma-feature  →  PR  →  staging  →  PR  →  main
hotfix/bug-critique →  PR  →  main (merge direct si urgence + tests verts)
```

---

## Protection de la branche `main`

### Configuration GitHub (Settings > Branches > Add rule)

**Branch name pattern :** `main`

| Règle | Valeur | Justification |
|-------|--------|---------------|
| Require a pull request before merging | Activé | Aucun push direct — toute modification passe par review |
| Required approvals | 1 minimum | Solo dev Phase 0 : 1 auto-review + CI ; augmenter à 2 en Phase 2 |
| Dismiss stale reviews when new commits are pushed | Activé | Une review stale ne doit pas valider du code modifié |
| Require status checks to pass | Activé | Voir liste ci-dessous |
| Require branches to be up to date | Activé | Évite les merges de branches trop anciennes |
| Require linear history | Activé | Historique propre — rebase obligatoire avant merge |
| Do not allow bypassing | Activé | Même les admins sont soumis aux règles |
| Restrict who can push | Activé | Uniquement les membres de l'équipe (pas les bots) |
| Require signed commits | Recommandé en Phase 2 | À activer quand la clé GPG est configurée |

### Status checks requis (Require status checks to pass)

Ces jobs CI doivent être verts avant tout merge sur main :

```
- lint-web          (job lint-web du workflow CI)
- lint-api          (job lint-api du workflow CI)
- test-api          (job test-api du workflow CI)
- test-web          (job test-web du workflow CI)
- security          (job security du workflow CI)
```

Le job `build-docker` n'est pas requis pour merger (il s'exécute après le merge sur main).

---

## Protection de la branche `staging`

**Branch name pattern :** `staging`

| Règle | Valeur |
|-------|--------|
| Require a pull request before merging | Activé |
| Required approvals | 0 (auto-merge possible depuis feature branches) |
| Require status checks to pass | Activé |
| Status checks requis | `lint-web`, `lint-api`, `test-api` |
| Require linear history | Activé |
| Do not allow bypassing | Désactivé (staging est plus permissif) |

---

## Branche `dev` — aucune protection

La branche `dev` est volontairement non protégée :
- Sert de sandbox pour les expérimentations
- N'est jamais mergée directement dans `staging` ou `main`
- Les feature branches naissent depuis `staging`, pas depuis `dev`

---

## Conventions de nommage des branches

```
feature/<ticket-id>-description-courte
fix/<ticket-id>-description-du-bug
chore/<description>
refactor/<description>
docs/<description>
hotfix/<description>
```

Exemples valides :
```
feature/MP-42-weekly-planner-endpoint
fix/MP-51-celery-redis-connection-timeout
chore/update-dependencies-april-2026
```

---

## CODEOWNERS (fichier `.github/CODEOWNERS`)

```
# Par défaut, le propriétaire du projet est reviewer sur tout
* @mealplanner-saas/core-team

# Fichiers d'infrastructure — review obligatoire du responsable DevOps
/infra/ @mealplanner-saas/devops
/.github/ @mealplanner-saas/devops
/apps/api/ @mealplanner-saas/backend
/apps/web/ @mealplanner-saas/frontend
```

---

## Template de Pull Request (`.github/PULL_REQUEST_TEMPLATE.md`)

```markdown
## Description
<!-- Que fait cette PR ? Lien vers le ticket -->

## Type de changement
- [ ] feat: nouvelle fonctionnalité
- [ ] fix: correction de bug
- [ ] chore: maintenance / dépendances
- [ ] refactor: restructuration sans changement de comportement
- [ ] docs: documentation uniquement

## Checklist avant merge
- [ ] Tests ajoutés ou mis à jour
- [ ] Couverture > 80% maintenue
- [ ] Pas de secrets hardcodés (gitleaks validé)
- [ ] Documentation mise à jour si API modifiée
- [ ] Feature flag activé si déploiement progressif nécessaire
- [ ] `memory/project-context.md` mis à jour si décision architecturale
```

---

## Déploiement automatique

| Branche | Vercel | Railway |
|---------|--------|---------|
| `main` | Production (`app.mealplanner.fr`) | Prod (api + worker) |
| `staging` | Preview fixe (`staging.mealplanner.fr`) | Staging (api + worker) |
| `feature/*` | Preview dynamique (URL unique par PR) | Aucun déploiement |

Le déploiement sur Railway est déclenché via webhook GitHub → Railway,
configuré dans le dashboard Railway (Settings > Source > Deploy Triggers).
