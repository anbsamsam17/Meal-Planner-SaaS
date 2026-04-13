# Configuration Railway — MealPlanner SaaS (Backend)

> Guide de configuration des services Python sur Railway.
> La règle ROADMAP est claire : backend Python uniquement, pas de Node.js côté serveur.
> Railway est retenu pour sa simplicité de déploiement Dockerfile et son pricing prévisible.

---

## 1. Pourquoi Railway et pas Render

| Critère | Railway | Render |
|---------|---------|--------|
| Cold starts | Aucun (Starter+ plan) | Oui sur Free tier |
| Dockerfile custom | Natif | Natif |
| Redis plugin | Natif (inclus dans le projet) | Service séparé |
| Pricing | 5$/mois + usage | Free avec cold starts |
| Déploiement depuis GHCR | Oui | Oui |
| Logs streaming | Excellent | Correct |
| Volumes persistants | Oui | Oui |

**Décision :** Railway évite les cold starts qui dégraderaient l'expérience (FastAPI
met 2-4 secondes à démarrer avec ses imports). Le plan Starter à 5$/mois est obligatoire.

---

## 2. Structure du projet Railway

```
Projet Railway : mealplanner-saas
├── Service : api          (FastAPI — Dockerfile apps/api)
├── Service : worker       (Celery — Dockerfile apps/worker)
├── Service : worker-beat  (Celery Beat — même Dockerfile, commande différente)
└── Plugin  : Redis        (Redis 7 natif Railway)
```

**Pourquoi worker-beat séparé :**
Celery Beat (scheduler) doit tourner en singleton — un seul process dans tout le cluster.
Un service dédié garantit qu'il n'y a jamais deux schedulers actifs (sinon doublon de tâches).

---

## 3. Configuration du service `api`

### Source

- **Source** : GitHub Container Registry (GHCR)
- **Image** : `ghcr.io/<org>/mealplanner-api:latest`
- Mise à jour automatique via webhook GHCR → Railway

### Variables d'environnement

Les secrets sont injectés par Doppler (intégration Doppler → Railway disponible).
Variables minimales à configurer :

```bash
# Injectées par Doppler (ne pas copier-coller manuellement)
DATABASE_URL=postgresql+asyncpg://...  # Supabase connection string
REDIS_URL=${{Redis.REDIS_URL}}         # Variable Railway interne (auto)
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
SENTRY_DSN=...
POSTHOG_KEY=...
R2_ACCESS_KEY=...
R2_SECRET=...
R2_BUCKET=mealplanner-pdfs
R2_ENDPOINT=...
RESEND_API_KEY=...
FLAGSMITH_ENV_KEY=...

# Variables Railway spécifiques (à définir directement dans Railway)
ENVIRONMENT=production
PORT=8000
PYTHONUNBUFFERED=1
```

### Health check

- **Path** : `/health`
- **Interval** : 30s
- **Timeout** : 10s
- **Grace period** : 60s (temps de démarrage FastAPI + connexion DB)

### Domaine custom

- **Domain** : `api.mealplanner.fr`
- Configuration DNS : `api.mealplanner.fr CNAME <service>.railway.app`
- Railway génère automatiquement un certificat TLS Let's Encrypt

### Health check

- **Liveness** (`/health`) : retour immédiat 200, sans attendre DB ni modèle ML.
  Railway l'utilise pour détecter un process bloqué.
- **Readiness** (`/ready`) : vérifie DB + modèle sentence-transformers chargé.
  Railway doit pointer sur `/ready` pour ne pas router de trafic avant que le modèle
  soit opérationnel (sinon cold start → 503 pendant 3–5s).
  Voir section "Pattern liveness / readiness" ci-dessous pour le détail d'implémentation.

### Ressources Phase 0

<!-- FIX #6 (review 2026-04-12) : 512 MB insuffisant — sentence-transformers all-MiniLM-L6-v2
     charge ~350 MB en mémoire. FastAPI + LangGraph + modèle → OOM-kill sous charge.
     Minimum absolu : 1 GB RAM. -->
- **RAM** : **1 GB minimum** (sentence-transformers all-MiniLM-L6-v2 = ~350 MB en mémoire,
  FastAPI + LangGraph + overhead Python = ~300 MB → total ~650 MB hors cache OS).
  512 MB provoque un OOM-kill Railway sous charge effective.
- **CPU** : 0.5 vCPU (Phase 0) — passer à 1 vCPU à 500 users actifs simultanés
- À augmenter en Phase 2 quand la charge augmente

---

## 4. Configuration du service `worker`

### Source

- **Image** : `ghcr.io/<org>/mealplanner-worker:latest`

### Variables d'environnement

Identiques au service `api` — même Doppler config + variables Celery :

```bash
CELERY_CONCURRENCY=4
CELERY_PREFETCH_MULTIPLIER=1
CELERY_LOG_LEVEL=INFO
```

### Ressources Phase 0

<!-- FIX #6 (review 2026-04-12) : alignement avec le sizing réel — WeasyPrint + embedding
     sont RAM-intensive. 1 GB est le minimum documenté. -->
- **RAM** : **1 GB minimum** (WeasyPrint génération PDF ~200 MB, embedding batch ~300 MB,
  overhead Python + Celery = ~200 MB → total ~700 MB sous charge)
- **CPU** : 1 vCPU
- Workers parallèles : 4 (correspond à CELERY_CONCURRENCY)

### Pas de domaine custom

Le worker n'expose pas de port HTTP — pas de domaine à configurer.

---

## 5. Configuration du service `worker-beat`

### Source

Même image que `worker` mais ENTRYPOINT surchargé :

**Start Command (Railway) :**
```
celery -A src.app beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Ou si on utilise le scheduler fichier (plus simple en Phase 0) :
```
celery -A src.app beat --loglevel=INFO
```

### Ressources Phase 0

- **RAM** : 256 MB (Celery Beat est très léger — il envoie seulement des messages)
- **CPU** : 0.1 vCPU

---

## 6. Plugin Redis

Railway propose un plugin Redis natif qui s'intègre directement dans le projet.

### Configuration

1. Railway Dashboard > Projet > New Plugin > Redis
2. Railway injecte automatiquement `REDIS_URL` dans tous les services du projet
3. Pas besoin de configurer manuellement — utiliser `${{Redis.REDIS_URL}}` dans les env vars

**Version :** Redis 7 (spécifier dans la config Railway)
**Persistence :** AOF activé (configurer dans les settings du plugin)

---

## 7. Sizing recommandé — récapitulatif chiffré

<!-- FIX #6 et #7 (review 2026-04-12) : section ajoutée pour documenter le sizing minimum
     validé par l'audit mémoire sentence-transformers + WeasyPrint. -->

| Service | RAM Phase 0 | RAM Phase 2 (5k users) | Justification |
|---------|-------------|------------------------|---------------|
| `api` | **1 GB** | 2 GB | sentence-transformers ~350 MB + FastAPI + LangGraph |
| `worker` | **1 GB** | 2 GB | WeasyPrint ~200 MB + embedding ~300 MB + Celery overhead |
| `worker-beat` | 256 MB | 256 MB | Scheduleur léger, aucun modèle ML |
| Redis (plugin) | **512 MB** | 2 GB | Broker Celery + cache applicatif — volatile-lru actif |

**Avertissement :** 512 MB pour le service `api` provoque un OOM-kill Railway lors du
chargement du modèle `sentence-transformers/all-MiniLM-L6-v2` (~350 MB en RAM).
Ne pas descendre en dessous de 1 GB pour les services `api` et `worker`.

### Plugin Redis Railway : configuration minimale

```
Mémoire : 512 MB (plan Starter minimum)
Persistence : AOF activé (ne pas perdre les tâches Celery)
maxmemory-policy : volatile-lru (jamais allkeys-lru — risque de perte Celery)
```

---

## 7b. Pattern liveness / readiness — Convention /health vs /ready

<!-- FIX #7 (review 2026-04-12) : distinction liveness/readiness requise pour éviter que
     Railway route du trafic vers un pod qui charge encore sentence-transformers. -->

Le service `api` doit exposer deux endpoints distincts :

| Endpoint | Type | Vérifie | Temps de réponse |
|----------|------|---------|-----------------|
| `GET /health` | Liveness | Process vivant (aucune dépendance) | < 5ms |
| `GET /ready` | Readiness | DB accessible + modèle ML chargé | < 100ms |

**Convention de configuration Railway :**
- Healthcheck Railway → pointer sur `/ready`
- Le `HEALTHCHECK` Dockerfile → pointer sur `/health` (liveness, pour Docker lui-même)
- `start-period=40s` sur le Dockerfile laisse le temps au modèle de se charger

**Exemple d'implémentation (Backend developer — Phase 1) :**

```python
# apps/api/src/main.py
_model_loaded: bool = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_loaded
    # Charger sentence-transformers une seule fois au démarrage (singleton)
    SentenceTransformer("all-MiniLM-L6-v2")
    _model_loaded = True
    yield
    _model_loaded = False

@router.get("/health")
async def liveness():
    """Liveness check : répond 200 si le process est vivant (sans vérifier la DB)."""
    return {"status": "alive"}

@router.get("/ready")
async def readiness():
    """Readiness check : répond 200 uniquement quand le modèle ML et la DB sont prêts."""
    if not _model_loaded:
        raise HTTPException(503, detail="Model not loaded yet")
    await db.execute("SELECT 1")  # Vérifie la connectivité DB
    return {"status": "ready"}
```

---

## 8. Autoscaling (Phase 3+)
<!-- (ancienne section 7 — décalée suite à l'ajout des sections 7 et 7b) -->

En Phase 0, le scaling est manuel. En Phase 3 (5 000 utilisateurs), activer :

```yaml
# Règle d'autoscaling Railway (disponible sur plan Pro)
scaling:
  minInstances: 1
  maxInstances: 5
  metrics:
    - type: cpu
      target: 70  # Scale up si CPU > 70%
    - type: memory
      target: 80  # Scale up si RAM > 80%
```

---

## 9. Déploiement depuis GitHub Actions

Le workflow CI (livrable 05) pousse les images sur GHCR.
Railway est configuré pour détecter les nouveaux tags et redéployer automatiquement.

**Configuration Webhook Railway :**
1. Railway Dashboard > Service api > Settings > Webhooks
2. Copier l'URL du webhook Railway
3. Dans GitHub : Settings > Webhooks > Add webhook
4. Event : `registry_package` (quand une nouvelle image est poussée sur GHCR)

Ou utiliser la Railway CLI dans le workflow CI :

```yaml
# Extrait à ajouter dans ci.yml après build-docker (sur main uniquement)
- name: Deploy to Railway
  run: |
    npm install -g @railway/cli
    railway up --service api --detach
    railway up --service worker --detach
    railway up --service worker-beat --detach
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## 10. Monitoring Railway

- **Logs** : Railway Dashboard > Service > Logs (streaming en temps réel)
- **Métriques** : CPU, RAM, Network dans l'onglet Metrics
- **Alertes** : Configurer dans Settings > Notifications (email ou webhook Slack)

Ces métriques complètent Sentry (erreurs applicatives) et PostHog (analytics produit).
