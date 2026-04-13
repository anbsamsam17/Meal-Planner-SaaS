# PDF Generation Strategy — MealPlanner SaaS
> Document de design Phase 0 | Auteur : backend-developer
> Créé le 2026-04-12 | Répond à CRITIQUE-4 et OPT-5 du performance-audit.md
> Statut : DESIGN VALIDÉ — à implémenter en Phase 1

---

## 1. Problème identifié par le performance-audit

### Stratégie initiale ROADMAP : batch Celery beat dimanche soir

La ROADMAP initiale décrit l'agent `BOOK_GENERATOR` comme générant les PDFs hebdomadaires en batch le dimanche soir via Celery beat. C'est une approche simple qui semblait logique : attendre que tous les plans de la semaine soient validés, puis générer tous les livrets PDF en une seule vague.

### Calcul du problème à 5 000 utilisateurs

L'audit performance a établi le calcul suivant pour évaluer la faisabilité du batch :

```
5 000 users × 1 PDF/semaine
= 5 000 tâches Celery dimanche soir

Capacité worker Celery (config actuelle) :
4 concurrency × 1 instance Railway = 4 PDFs en simultané

Durée batch estimée :
5 000 PDFs ÷ 4 parallèles × 2s par PDF = 2 500 secondes ≈ 41 minutes
```

**Ce résultat de 41 minutes est incompatible avec le produit.** Les utilisateurs ouvrent l'application le dimanche soir pour consulter leur plan de la semaine suivante et télécharger leur livre de recettes. Si le PDF n'est pas disponible pendant 41 minutes après le début du batch, l'expérience est dégradée.

### Risques supplémentaires du batch dimanche

Au-delà du simple problème de durée, le batch dimanche concentre plusieurs risques techniques :

**Timeout Celery :** WeasyPrint peut dépasser le timeout par défaut (300s) sur des PDFs lourds (beaucoup de photos haute résolution). Sur une vague de 5 000 tâches, les timeouts s'accumulent et déclenchent des retries — aggravant la congestion.

**Retries en cascade :** Si Stability AI est lente le dimanche soir (ce service cloud peut être saturé le week-end), les photos de recettes prennent plus longtemps. Le worker attend, la tâche timeout, Celery retry trois fois. La queue grossit au lieu de se vider.

**Mémoire Redis broker saturée :** 5 000 tâches Celery simultanément en queue consomment de la mémoire Redis. Avec la configuration actuelle de 256 MB (`allkeys-lru`), certaines tâches pourraient être évincées (problème documenté dans HIGH-6 de l'audit et résolu dans OPT-6).

**Absence de feedback utilisateur :** Avec un batch purement backend, aucun mécanisme n'informe l'utilisateur de l'avancement. Il voit juste "PDF non disponible" sans ETA.

---

## 2. Nouvelle stratégie : génération à la validation du plan

### Principe fondamental

**Le PDF est généré au moment où l'utilisateur valide son plan semaine**, pas en batch le dimanche soir. L'événement déclencheur est `plan_validated` — quand l'utilisateur confirme son plan pour la semaine suivante.

### Distribution naturelle de la charge

L'insight clé de cette stratégie est que les utilisateurs ne valident pas tous leur plan le même dimanche soir à 20h00. En pratique, la validation est répartie sur une fenêtre de 48 à 72 heures :

| Moment de validation | Proportion estimée des users | Moment de disponibilité PDF |
|----------------------|-----------------------------|-----------------------------|
| Samedi après-midi | ~15% | Samedi soir |
| Samedi soir | ~20% | Samedi soir |
| Dimanche matin | ~25% | Dimanche matin |
| Dimanche après-midi | ~25% | Dimanche après-midi |
| Dimanche soir (20h-22h) | ~10% | Dimanche soir (~4 min) |
| Lundi matin (retardataires) | ~5% | Lundi matin |

**Impact sur le pic dimanche soir :**

```
Pic résiduel dimanche soir : ~10% de 5 000 = 500 PDFs
500 PDFs ÷ 4 parallèles × 2s = 250 secondes ≈ 4 minutes

Pic acceptable : 4 minutes vs 41 minutes initialement.
```

Le batch Celery beat du dimanche n'est plus qu'un filet de sécurité pour les retardataires et les re-générations.

### Avantages supplémentaires

**Feedback immédiat :** L'utilisateur qui valide son plan reçoit une notification "Votre livre de recettes est en cours de génération" puis "Votre livre est prêt" en moins de 2 secondes — expérience bien supérieure.

**Charge étalée naturellement :** Aucune surcharge d'infrastructure à prévoir pour le dimanche — la charge est distribuée sur la semaine selon les comportements utilisateurs.

**Isolation des erreurs :** Une erreur WeasyPrint sur le PDF d'un utilisateur n'impacte pas les PDFs des 4 999 autres. Les retries sont isolés.

---

## 3. Architecture technique

### Flux de données complet

```
POST /plans/{plan_id}/validate
  |
  v
FastAPI endpoint
  — Validation des droits (RLS : plan appartient au household)
  — weekly_plans.status = 'validated'
  — weekly_plans.validated_at = now()
  |
  v
Celery.send_task('book_generator.generate_weekly_book',
                  args=[plan_id],
                  queue='pdf_high',
                  priority=9)
  |
  v
[Redis broker — queue pdf_high]
  |
  v
BOOK_GENERATOR worker (Celery, queue pdf_high, concurrency 4)
  |
  +-- Récupère weekly_plan + planned_meals depuis Supabase
  |
  +-- Vérifie l'idempotence :
  |     hash = sha256(plan_content)
  |     Si weekly_books.content_hash == hash → skip (PDF déjà à jour)
  |
  +-- Assemble les photos recettes depuis Cloudflare R2
  |     (photos pré-générées par RECIPE_SCOUT, pas ici)
  |
  +-- Jinja2 → HTML template du livre de recettes
  |
  +-- WeasyPrint → PDF bytes (cible < 1.5s)
  |
  +-- Upload vers Cloudflare R2
  |     Clé : {household_id}/{plan_id}-{hash[:8]}.pdf
  |
  +-- UPDATE weekly_books SET pdf_r2_key = ..., content_hash = ..., generated_at = now()
  |
  v
Notification utilisateur
  — Web push (si permission accordée)
  — In-app badge "Livre prêt"
  — PostHog event 'pdf_generated' avec duration_ms
```

### Diagramme de séquence simplifié

```
User          FastAPI         Celery          WeasyPrint      R2
  |               |               |               |            |
  |--- validate ->|               |               |            |
  |               |-- send_task ->|               |            |
  |<-- 202 -------|               |               |            |
  |               |               |-- render ---->|            |
  |               |               |<-- PDF bytes -|            |
  |               |               |-- upload ----------------------->|
  |               |               |<-- R2 key ----------------------|
  |<-- push notif (< 2s total) ---|               |            |
```

---

## 4. Queue Celery dédiée

### Deux queues PDF avec des priorités séparées

La séparation en deux queues évite qu'un batch de retardataires du dimanche tarde une génération temps-réel déclenchée par une validation.

| Queue | Déclencheur | Concurrency | Workers | Priorité |
|-------|-------------|-------------|---------|----------|
| `pdf_high` | Validation plan utilisateur (temps-réel) | 4 | 1 instance Railway | High (9) |
| `pdf_low` | Batch dimanche résiduel, re-génération admin | 2 | 1 instance Railway partagée | Low (1) |

### Configuration Celery

```python
# apps/worker/src/celery_config.py

CELERY_TASK_ROUTES = {
    'book_generator.generate_weekly_book': {
        'queue': 'pdf_high',
        'priority': 9,
    },
    'book_generator.batch_generate_missing_books': {
        'queue': 'pdf_low',
        'priority': 1,
    },
}

CELERY_WORKER_QUEUES = {
    'pdf_high': {
        'concurrency': 4,
        'prefetch_multiplier': 1,  # 1 tâche à la fois par worker — PDFs lourds
    },
    'pdf_low': {
        'concurrency': 2,
        'prefetch_multiplier': 1,
    },
}
```

### Batch dimanche résiduel (Celery beat)

Le Celery beat du dimanche est conservé mais son rôle est réduit :

```python
# apps/worker/src/beat_schedule.py

CELERY_BEAT_SCHEDULE = {
    # Filet de sécurité : génère les PDFs manquants pour la semaine suivante
    # (plans validés mais dont le PDF a échoué ou n'a pas encore été généré)
    'batch-missing-pdfs-sunday': {
        'task': 'book_generator.batch_generate_missing_books',
        'schedule': crontab(hour=22, minute=0, day_of_week=0),  # Dimanche 22h
        'options': {'queue': 'pdf_low'},
    },
}
```

---

## 5. Idempotence et retries

### Hachage du contenu du plan

Chaque génération de PDF est identifiée par un hash SHA-256 du contenu du plan. Ce hash sert à deux choses :

1. **Idempotence :** si le PDF pour ce `plan_id` avec ce `content_hash` existe déjà dans R2, on ne régénère pas
2. **Versioning :** si l'utilisateur modifie son plan après validation (feature future), un nouveau hash déclenche une re-génération

```python
# apps/worker/src/agents/book_generator.py

import hashlib
import json

def compute_plan_hash(plan_data: dict) -> str:
    """
    Calcule un hash déterministe du contenu du plan.
    Tout changement dans les recettes ou le planning déclenche une re-génération.
    """
    canonical = json.dumps(plan_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # 30s entre les retries
    queue="pdf_high",
)
def generate_weekly_book(self, plan_id: str) -> None:
    """
    Génère le PDF du livre de recettes pour un plan validé.
    Idempotente : skip si le hash du plan n'a pas changé depuis la dernière génération.
    """
    plan = get_plan_with_meals(plan_id)
    content_hash = compute_plan_hash(plan.to_dict())

    # Vérification idempotence
    existing = get_weekly_book(plan_id)
    if existing and existing.content_hash == content_hash:
        logger.info("pdf_skip_idempotent", plan_id=plan_id, hash=content_hash[:8])
        return

    try:
        pdf_bytes = render_pdf(plan)
        r2_key = upload_to_r2(
            data=pdf_bytes,
            key=f"{plan.household_id}/{plan_id}-{content_hash[:8]}.pdf",
        )
        save_weekly_book(plan_id=plan_id, r2_key=r2_key, content_hash=content_hash)
        notify_user(plan.household_id, event="pdf_ready", r2_key=r2_key)

    except WeasyPrintError as exc:
        logger.error("pdf_weasyprint_error", plan_id=plan_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)

    except R2UploadError as exc:
        logger.error("pdf_r2_upload_error", plan_id=plan_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)
```

### Dead letter queue et alerte Sentry

Après 3 retries sans succès, la tâche passe dans la dead letter queue `pdf_dlq` :

```python
CELERY_TASK_ROUTES = {
    'book_generator.generate_weekly_book': {
        'queue': 'pdf_high',
        'dead_letter_queue': 'pdf_dlq',
    },
}
```

Un worker séparé consomme `pdf_dlq` toutes les heures et envoie une alerte Sentry pour chaque tâche en erreur :

```python
@celery_app.task(queue="pdf_dlq")
def handle_pdf_dlq(task_id: str, plan_id: str, last_error: str) -> None:
    sentry_sdk.capture_message(
        f"PDF non généré après 3 retries : plan_id={plan_id}",
        level="error",
        extra={"plan_id": plan_id, "last_error": last_error},
    )
```

---

## 6. Pré-génération d'assets (photos recettes)

### Principe

Les photos de recettes sont générées par Stability AI au moment de l'ajout de la recette en base (pipeline `RECIPE_SCOUT`), **pas au moment de la génération du PDF**. Cette séparation des responsabilités est fondamentale pour atteindre la cible < 1.5s par PDF.

### Flux de pré-génération

```
RECIPE_SCOUT ingère une nouvelle recette
  |
  v
Celery task 'recipe_scout.generate_photo'
  — Appel Stability AI (SDXL-Turbo, 512×512)
  — Durée : 5–30s (asynchrone, pas dans le flux utilisateur)
  — Upload vers Cloudflare R2 : photos/{recipe_id}.jpg
  — UPDATE recipes SET photo_r2_key = ...
```

### Impact sur la génération PDF

Au moment de la génération du PDF :
- `recipes.photo_r2_key` est déjà renseigné pour toutes les recettes
- Le BOOK_GENERATOR ne fait qu'assembler les images déjà en R2
- Temps d'assemblage photo dans le PDF : < 200ms (lectures R2 en parallèle)

### Cible de performance PDF

```
Fetch plan + meals depuis Supabase  :  ~30ms
Fetch photos depuis R2 (7 recettes) :  ~100ms (en parallèle)
Jinja2 → HTML rendering             :  ~50ms
WeasyPrint HTML → PDF               :  ~800ms-1200ms
Upload PDF vers R2                   :  ~100ms
Notification push                    :  ~50ms
----------------------------------------------
Total estimé p50                     :  ~1 130ms–1 530ms
Cible p95                            :  < 2s
```

---

## 7. Fallback si Stability AI est indisponible

### Principe du fallback gracieux

La génération d'un PDF ne doit **jamais bloquer** à cause d'une photo manquante. Le circuit breaker Stability AI (documenté dans `12-rate-limiting-design.md`) ouvre automatiquement si le service est dégradé.

### Photos par défaut par catégorie

Un ensemble de photos par défaut est stocké en R2 dans le dossier `photos/defaults/` :

| Catégorie de cuisine | Clé R2 par défaut |
|----------------------|-------------------|
| Asiatique | `photos/defaults/asian.jpg` |
| Italienne / méditerranéenne | `photos/defaults/mediterranean.jpg` |
| Mexicaine / latine | `photos/defaults/mexican.jpg` |
| Française | `photos/defaults/french.jpg` |
| Végétarienne / vegan | `photos/defaults/vegetarian.jpg` |
| Rapide (< 20 min) | `photos/defaults/quick.jpg` |
| Générique | `photos/defaults/generic.jpg` |

### Logique de sélection

```python
def get_recipe_photo_key(recipe: Recipe) -> str:
    """
    Retourne la clé R2 de la photo de la recette.
    Si la photo n'existe pas encore (Stability AI pas encore passé)
    ou si le circuit breaker est ouvert, utilise la photo par défaut
    de la catégorie correspondante.
    """
    if recipe.photo_r2_key:
        return recipe.photo_r2_key

    # Sélection de la photo par défaut selon les tags de la recette
    DEFAULT_PHOTOS = {
        "asiatique": "photos/defaults/asian.jpg",
        "méditerranéen": "photos/defaults/mediterranean.jpg",
        "mexicain": "photos/defaults/mexican.jpg",
        "français": "photos/defaults/french.jpg",
        "végétarien": "photos/defaults/vegetarian.jpg",
        "vegan": "photos/defaults/vegetarian.jpg",
    }
    for tag in recipe.tags:
        if tag.lower() in DEFAULT_PHOTOS:
            return DEFAULT_PHOTOS[tag.lower()]

    # Fallback générique
    return "photos/defaults/generic.jpg"
```

---

## 8. Coût budgété

### Calcul à 5 000 utilisateurs payants

| Poste | Calcul | Coût mensuel |
|-------|--------|-------------|
| WeasyPrint CPU | Self-hosted sur Railway, inclus dans le coût worker | ~0 € |
| Stability AI | 1 photo nouvelle toutes les 10 PDFs (le reste est en cache R2) = 5 000 × 4 semaines ÷ 10 = 2 000 générations × $0.002 | ~4 € |
| Cloudflare R2 stockage | 20 000 PDFs/mois × 500 KB = 10 GB × $0.015/GB | ~0.15 € |
| Cloudflare R2 lectures | 20 000 PDFs × $0.0004/1000 opérations | ~0.01 € |
| Redis broker (queues Celery) | Inclus dans l'instance Redis existante | ~0 € |
| **Total PDF generation** | | **~4.16 €/mois** |

### Budget Stability AI — détail de l'hypothèse "1 photo toutes les 10 PDFs"

Cette hypothèse repose sur le fait que :
- Le catalogue initial contient 500 recettes avec photos générées lors du seeding
- Les 5 000 users utilisent principalement des recettes du catalogue (pas de recettes custom)
- Seules les recettes custom (générées via `/recipe/generate`) nécessitent une photo Stability AI

En pratique, le coût Stability AI est piloté par l'adoption de la feature recette custom, pas par le volume de PDFs.

---

## 9. KPI techniques

### Métriques à exposer (Prometheus / Sentry custom)

| Métrique | Type | Labels | Cible |
|----------|------|--------|-------|
| `pdf_generation_duration_seconds` | Histogram | `queue`, `status` | p50 < 1.5s, p95 < 2s, p99 < 5s |
| `pdf_queue_depth` | Gauge | `queue` | Alerte si > 100 |
| `pdf_generation_total` | Counter | `status` (success/error/skip) | Taux succès > 99.5% |
| `pdf_retry_total` | Counter | `reason` | Alerte si > 1% |
| `pdf_dlq_depth` | Gauge | — | Alerte si > 0 |

### SLO (Service Level Objective)

**SLO principal :** 99.5% des PDFs disponibles dans les 30 secondes suivant la validation du plan par l'utilisateur.

**Décomposition :**
- `plan_validated` → `Celery.send_task` : < 100ms (synchrone dans l'endpoint FastAPI)
- Délai en queue `pdf_high` : < 5s (objectif p95)
- Génération WeasyPrint + upload R2 : < 2s (objectif p95)
- Notification push : < 500ms

**Total p95 attendu : < 7.6 secondes** après la validation.

### Monitoring queue depth

```python
# apps/worker/src/monitoring.py

import redis
from prometheus_client import Gauge

pdf_queue_depth = Gauge(
    "pdf_queue_depth",
    "Nombre de tâches en attente dans les queues PDF",
    labelnames=["queue"],
)

def update_pdf_queue_metrics():
    """
    À appeler toutes les 30s via un thread de monitoring Celery.
    """
    r = redis.Redis.from_url(REDIS_URL)
    for queue_name in ["pdf_high", "pdf_low", "pdf_dlq"]:
        depth = r.llen(queue_name)
        pdf_queue_depth.labels(queue=queue_name).set(depth)

        # Alerte si la queue pdf_high dépasse 100
        if queue_name == "pdf_high" and depth > 100:
            sentry_sdk.capture_message(
                f"Queue pdf_high saturée : {depth} tâches en attente",
                level="warning",
            )
```

---

## 10. Mise à jour du schéma DB

### Colonnes à ajouter

Ces modifications du schéma doivent être transmises au `database-administrator` pour implémentation en Phase 1 via une migration Alembic.

**Table `weekly_books` :**

```sql
-- Migration Phase 1 — PDF strategy update
-- Fichier : alembic/versions/0002_pdf_strategy_columns.py

ALTER TABLE weekly_books
    ADD COLUMN content_hash TEXT,
    ADD COLUMN generated_at TIMESTAMPTZ;

-- Index pour les lookups d'idempotence (book par plan_id + hash)
CREATE INDEX idx_weekly_books_plan_hash
    ON weekly_books (plan_id, content_hash)
    WHERE content_hash IS NOT NULL;

COMMENT ON COLUMN weekly_books.content_hash IS
    'SHA-256 du contenu du plan au moment de la génération. '
    'Permet l idempotence : re-génération uniquement si le plan a changé.';

COMMENT ON COLUMN weekly_books.generated_at IS
    'Timestamp de génération effective du PDF (pas de la validation du plan).';
```

**Table `weekly_plans` :**

```sql
ALTER TABLE weekly_plans
    ADD COLUMN validated_at TIMESTAMPTZ;

-- Index pour les requêtes batch dimanche (plans validés sans PDF)
CREATE INDEX idx_weekly_plans_validated_no_pdf
    ON weekly_plans (validated_at)
    WHERE status = 'validated' AND validated_at IS NOT NULL;

COMMENT ON COLUMN weekly_plans.validated_at IS
    'Timestamp de validation du plan par l utilisateur. '
    'Déclenche la génération PDF via BOOK_GENERATOR.';
```

### Trigger Supabase (option alternative au send_task FastAPI)

Une alternative à l'appel `Celery.send_task` dans l'endpoint FastAPI est d'utiliser un trigger Supabase pour déclencher la génération via `pg_notify` :

```sql
-- Option : trigger Supabase pour déclencher BOOK_GENERATOR
CREATE OR REPLACE FUNCTION notify_plan_validated()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path TO pg_catalog, public
AS $$
BEGIN
    IF NEW.status = 'validated' AND OLD.status != 'validated' THEN
        NEW.validated_at = now();
        PERFORM pg_notify(
            'plan_validated',
            json_build_object('plan_id', NEW.id, 'household_id', NEW.household_id)::text
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER plan_validated_trigger
    BEFORE UPDATE ON weekly_plans
    FOR EACH ROW
    EXECUTE FUNCTION notify_plan_validated();
```

**Note :** Cette option via `pg_notify` nécessite un listener Python (asyncpg LISTEN) dans le worker. Elle est plus couplée à Supabase. L'approche recommandée reste **l'appel direct `Celery.send_task` depuis l'endpoint FastAPI** — plus simple, plus testable, moins de dépendances.

---

## 11. Dépendances Phase 1

Ce document de design génère les actions suivantes pour la Phase 1 :

### Schéma DB (à transmettre au database-administrator)

- [ ] Ajouter colonne `weekly_books.content_hash TEXT`
- [ ] Ajouter colonne `weekly_books.generated_at TIMESTAMPTZ`
- [ ] Ajouter colonne `weekly_plans.validated_at TIMESTAMPTZ`
- [ ] Créer index `idx_weekly_books_plan_hash`
- [ ] Créer index `idx_weekly_plans_validated_no_pdf`
- [ ] Migration Alembic `0002_pdf_strategy_columns.py`

### Infrastructure Celery

- [ ] Configurer les queues `pdf_high`, `pdf_low`, `pdf_dlq` dans `celery_config.py`
- [ ] Configurer 2 workers séparés sur Railway (ou 1 worker avec multiple queues)
- [ ] Configurer Celery beat pour le batch dimanche résiduel (queue `pdf_low`)
- [ ] Implémenter le handler `pdf_dlq` avec alerte Sentry

### Endpoint FastAPI

- [ ] Modifier `POST /plans/{plan_id}/validate` pour déclencher `generate_weekly_book` en async
- [ ] Retourner `202 Accepted` immédiatement (la génération est asynchrone)
- [ ] Ajouter endpoint `GET /plans/{plan_id}/book/status` pour polling du statut PDF

### Agent BOOK_GENERATOR

- [ ] Implémenter `generate_weekly_book` avec logique d'idempotence (content_hash)
- [ ] Implémenter `get_recipe_photo_key` avec fallback par catégorie
- [ ] Intégrer WeasyPrint + Jinja2 pour le rendu HTML → PDF
- [ ] Intégrer l'upload Cloudflare R2 (`{household_id}/{plan_id}-{hash[:8]}.pdf`)
- [ ] Implémenter les métriques Prometheus (`pdf_generation_duration_seconds`, etc.)

### Monitoring

- [ ] Configurer alerte Sentry si `pdf_queue_depth > 100`
- [ ] Configurer alerte Sentry si `pdf_dlq_depth > 0`
- [ ] Dashboard queue depth dans Sentry/Grafana
- [ ] PostHog event `pdf_generated` avec `duration_ms` pour analyse produit

### Photos par défaut

- [ ] Uploader les photos par défaut dans R2 : `photos/defaults/{category}.jpg`
- [ ] Valider que chaque catégorie de cuisine du catalogue a une photo par défaut

---

*Document rédigé en Phase 0 — design uniquement, pas d'implémentation.*
*Transmis à : backend-developer (Phase 1), database-administrator (migrations DB), performance-engineer (validation SLO).*
