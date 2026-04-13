# Code Review v2 — Phase 0 MealPlanner (post-fixes)

> Reviewer : senior code reviewer (Claude Opus 4.6 1M)
> Date : 2026-04-12
> Scope : re-review des fichiers modifiés par les 4 agents de fix (DBA, DevOps, UI designer, backend-developer)

---

## Score v1 → v2 : **82 → 93 / 100**

Répartition :

| Dimension | v1 | v2 | Commentaire |
|---|---|---|---|
| Sécurité | 17/25 | 23/25 | WITH CHECK partout, SECURITY DEFINER + search_path partout (sauf 2 triggers secondaires), $PORT fixé |
| Cohérence architecturale | 22/25 | 24/25 | Flux onboarding documenté, deux nouveaux designs docs très solides |
| Qualité code | 21/25 | 23/25 | CTEs explicites, commentaires "FIX #N" traçables, ESM propre côté Tailwind |
| Conformité ROADMAP | 14/20 | 18/20 | Rate limiting 5 niveaux documenté, PDF batch remplacé par eager streaming |
| Complétude | 8/10 | 5/5 (scope re-review) | Tous les livrables attendus produits et cohérents entre eux |

---

## Issues v1 résolues

**Critiques :**
- **C3** — policies DELETE/UPDATE user-facing : `weekly_plans_delete` (status='draft'), `shopping_lists_update`, `planned_meals_update/delete` (restreints draft), `fridge_items_delete` présents et correctement commentés. Flux cocher shopping list / reset plan débloqué.
- **C4** — récursion `household_members_insert` : policy INSERT supprimée et remplacée par la fonction `create_household_with_owner()` en SECURITY DEFINER + search_path vide, avec garde UNIQUE sur `supabase_user_id`. Flux d'onboarding documenté étape par étape.
- **C5** — `get_household_constraints()` réécrit en 3 CTEs séparées (allergies, diet_tags, scalars). Plus de produit cartésien JSONB. Budget_pref mappé sur 1/2/3 via CASE WHEN et reconverti en TEXT, résolvant le bug lexicographique locale FR.

**WITH CHECK manquants (remonté par debugger) :** ajoutés sur `household_members_update`, `member_preferences_update`, `planned_meals_update`, `fridge_items_update`. Commentaires FIX #1 explicitant l'attaque cross-tenant bloquée.

**High :**
- **H2** — `CMD uvicorn ... --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}` en shell form, HEALTHCHECK idem. Compatible Railway.
- **H4** — `12-rate-limiting-design.md` livré (628 lignes) : slowapi + Redis DB 1, 5 niveaux (IP, user, tenant, LLM user, LLM tenant), clés Redis nommées, fallback fail-open documenté avec exception strict pour `/plan/generate`, tests pytest inclus, checklist implémentation.
- **H6** — Tailwind : screens, fontFamily, fontSize, spacing, borderRadius, colors, boxShadow, zIndex sont tous dans `theme.extend`. Tokens custom (terracotta hsl 14, olive hsl 78, cream hsl 38) correctement préservés. Imports ESM `typography`/`forms`.
- **H9** — MinIO healthcheck `curl -f http://localhost:9000/minio/health/live` (curl présent dans l'image minio/minio), worker Celery healthcheck en shell form avec `$(hostname)` interpolé.

**Perf (non demandé explicitement mais fixé) :**
- PDF strategy `13-pdf-generation-strategy.md` : passage de batch dimanche 41 min → eager on `plan_validated` + queue résiduelle `pdf_low`, pic dimanche ≈ 4 min (500 PDFs × 2s / 4 workers). Deux queues `pdf_high`/`pdf_low` + DLQ, idempotence par hash de contenu, circuit breaker Stability AI, métriques Prometheus.

---

## Issues v1 non résolues / partielles

- **H1** `.dockerignore` — non re-scopé dans les fichiers à reviewer, probablement toujours absent.
- **H3** `planned_meals` restriction draft — **résolu** (USING et WITH CHECK filtrent status='draft').
- **H5** Doppler CI, **H7** avertissements mots de passe dev, **H8** SQL realtime publication — hors scope v2.
- **C2 / MEDIUM search_path sur `validate_recipe_quality()` et `trigger_set_updated_at()`** — **toujours absent**. `cleanup_old_embeddings` et `recipe_embeddings_sync_metadata` ont bien `SET search_path TO ''`, mais les deux premiers triggers ont été oubliés. Fix trivial (2 lignes), à traiter avant Phase 1.

---

## Nouvelles issues introduites par les fixes

- **N1 (LOW)** `13-pdf-generation-strategy.md` référence `weekly_plans.validated_at` qui n'existe pas dans `01-schema-core.sql`. Le document propose lui-même le `ALTER TABLE` dans sa checklist, mais la colonne doit être ajoutée en Phase 0.x avant que les exemples de code ne compilent. Cohérence fichier→fichier à surveiller.
- **N2 (LOW)** MinIO healthcheck : `curl` est effectivement présent dans `minio/minio:latest` aujourd'hui mais ce n'est pas une API publique garantie. Alternative plus robuste : healthcheck Python via `mc ready` depuis un sidecar, ou downgrade à `CMD-SHELL` avec `bash -c '</dev/tcp/localhost/9000'`. Non bloquant.
- **N3 (INFO)** Policy `weekly_plans_delete` limitée à `status='draft'` — correct, mais l'UI devra explicitement griser le bouton "supprimer" pour les plans validated/archived, sinon l'utilisateur reçoit un 403 opaque. À noter dans le backlog Phase 1 UI.
- **N4 (INFO)** `create_household_with_owner()` ne logge pas dans `audit_log` (qui n'existe pas encore — H9 v1). Quand la table sera créée, la fonction devra être mise à jour pour tracer la création de foyer.
- **Aucune régression RLS détectée** : les 11 policies existantes préservent l'isolation par `household_id = get_current_household_id()`, les nouveaux WITH CHECK sont identiques aux USING correspondants (pas de relaxation).

---

## Issues MEDIUM toujours ouvertes (non fixées opportunistement)

- **M6** `weekly_plans.week_start CHECK (EXTRACT(ISODOW FROM week_start) = 1)` — toujours absent dans `01-schema-core.sql`. Le commentaire dit "contrainte applicative" mais aucune validation DB. À ajouter (1 ligne).
- **MEDIUM search_path** `validate_recipe_quality()` et `trigger_set_updated_at()` (cf. supra) — règle défensive universelle violée pour deux fonctions.
- **M4** JSONB vs TEXT[] pour `diet_tags` — hors scope.
- **M5** `planned_meals.slot` CHECK vs commentaire — hors scope.
- **M7** unique owner par foyer — hors scope.
- **M8** unique feedback par jour — hors scope.

---

## Non-régression — questions posées

- **Policies RLS** : aucune régression, toutes les policies existantes v1 conservent leur sémantique, les 4 nouvelles WITH CHECK sont strictement égales à leur USING (pas de bypass).
- **Tokens Tailwind custom** : terracotta (primary 14°), olive (secondary 78°), cream (neutral 38°) correctement préservés, palette complète HSL intacte. Aliases shadcn (`background`, `foreground`, `card`, ...) en place.
- **Rate limiting ↔ monorepo FastAPI** : cohérent — `src/core/rate_limiting.py` placé dans `apps/api`, slowapi ajouté à `pyproject.toml`, clés Redis sur `REDIS_URL` avec `db=1` (Celery sur `db=0`). Middleware global FastAPI, pas de conflit avec le pattern auth documenté.
- **Fichiers 12 et 13 ↔ schéma** : le fichier 12 ne touche qu'à Redis, OK. Le fichier 13 référence `weekly_plans`, `planned_meals`, `recipes`, `households` (OK) et `weekly_plans.validated_at` (à créer, cf. N1).

---

## Verdict v2 : **GO pour Phase 1** (avec 2 fixes triviaux à enchaîner)

La Phase 0 a absorbé proprement **tous les 4 bloquants critiques** (C3, C4, C5, et les WITH CHECK cross-tenant) ainsi que les 4 HIGH demandés (H2, H4, H6, H9). Les deux nouveaux design docs (12 rate limiting, 13 PDF strategy) sont d'un niveau staff engineer : analyse d'impact chiffrée, alternatives rejetées justifiées, checklist d'implémentation, tests, métriques. Le PDF design résout élégamment le pic dimanche via eager generation sur `plan_validated`.

**Avant de lancer Phase 1 (1 heure de travail au total) :**

1. Ajouter `SET search_path TO ''` sur `validate_recipe_quality()` et `trigger_set_updated_at()` (`04-triggers-functions.sql`).
2. Ajouter `CONSTRAINT weekly_plans_week_start_is_monday CHECK (EXTRACT(ISODOW FROM week_start) = 1)` sur `weekly_plans` (`01-schema-core.sql`) — M6 v1.
3. Ajouter `ALTER TABLE weekly_plans ADD COLUMN validated_at TIMESTAMPTZ` avant d'implémenter `13-pdf-generation-strategy.md` — N1.

Le reste (H1 .dockerignore, H5 Doppler, H7 avertissements dev, H8 realtime SQL, H9 audit_log) reste au backlog début Phase 1 tel que prévu en v1. Aucun de ces items n'empêche d'attaquer l'implémentation des agents FastAPI ni l'onboarding UX.
