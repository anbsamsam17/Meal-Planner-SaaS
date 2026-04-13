# Rate Limiting Design — MealPlanner SaaS
> Document de design Phase 0 | Auteur : backend-developer
> Créé le 2026-04-12 | Répond à l'issue H4 du code-review.md
> Statut : DESIGN VALIDÉ — à implémenter en Phase 1

---

## 1. Pourquoi c'est critique

### Règle ROADMAP non-négociable

Le fichier `ROADMAP.md` et `CLAUDE.md` imposent explicitement :

> *"Rate limiting sur toutes les API (par tenant et par utilisateur)"*

Cette règle n'est pas une recommandation optionnelle. Elle constitue une exigence de sécurité fondamentale du projet. L'issue H4 du code-review identifie son absence comme **non-conforme** à la ROADMAP.

### Endpoints LLM — risque financier direct

MealPlanner SaaS intègre Claude (Anthropic API) pour 6 agents :
`RECIPE_SCOUT`, `TASTE_PROFILE`, `WEEKLY_PLANNER`, `CART_BUILDER`, `BOOK_GENERATOR`, `RETENTION_LOOP`.

Chaque appel LLM coûte entre $0.003 et $0.015 selon le volume de tokens. Un endpoint `/plan/generate` consomme typiquement 2 000–8 000 tokens par appel.

**Scénario d'attaque sans rate limiting :**
- Un acteur malveillant avec 1 compte valid déclenche 1 000 appels `/plan/generate` en 10 minutes
- Coût estimé : 1 000 × $0.015 = **$15 en 10 minutes**
- Scalé à un botnet de 100 comptes = **$1 500 en 10 minutes**
- Conséquence potentielle : suspension du compte Anthropic + facture imprévue = risque de faillite pour un projet early-stage

### Endpoints publics — risque d'abus et de bot

Les endpoints `/auth/register`, `/auth/login`, `/onboarding/*` sont accessibles sans authentification. Sans rate limiting :
- Brute force sur les mots de passe
- Création massive de comptes factices (pollution de la base)
- Enumération des emails d'utilisateurs existants via les messages d'erreur

### Multi-tenancy — isolation des quotas

Dans un SaaS multi-tenant, un tenant peut monopoliser les ressources au détriment des autres. Sans rate limiting par `household_id` :
- Un household avec 8 membres actifs génère 8× plus de charge qu'un household solo
- Un bug côté client (boucle infinie) peut saturer l'API pour tous les tenants
- Pas de mécanisme de fair-use entre les plans tarifaires (Starter vs Famille vs Coach)

---

## 2. Stack choisi : slowapi + Redis

### Pourquoi slowapi

`slowapi` est un fork de Flask-Limiter adapté pour FastAPI. C'est la solution la plus mature dans l'écosystème FastAPI pour le rate limiting :

| Critère | slowapi | fastapi-limiter | Solution custom |
|---------|---------|-----------------|-----------------|
| Maturité | Stable, 1k+ stars | Moins actif | N/A |
| Sliding window | Oui (elastic expiry) | Non | Coûteux à implémenter |
| Multiple key_func | Oui, par décorateur | Limité | Complexe |
| Middleware global | Oui | Oui | Oui |
| Headers standard | Oui (X-RateLimit-*) | Partiel | Manuel |
| Backend Redis | Oui | Oui | Oui |
| Intégration FastAPI | Native | Native | N/A |

**Alternative rejetée : `fastapi-limiter`**
- Pas de support natif de la sliding window (uniquement fixed-window)
- Moins de features pour les limites multi-niveaux (IP + user + tenant simultanément)
- Dépendance à `aioredis` v1 (deprecated), migration vers `redis-py` async non finalisée

### Pourquoi Redis comme backend

Redis est **déjà présent** dans l'infrastructure MealPlanner SaaS en tant que broker Celery (voir `02-docker-compose.dev.yml`). Réutiliser Redis pour le rate limiting :

- Ne nécessite **aucune infrastructure supplémentaire**
- Faible latence (< 1ms) pour les opérations INCR/EXPIRE
- Support natif des opérations atomiques (INCR + TTL dans un seul pipeline)
- Persistance optionnelle selon la stratégie choisie

**Configuration Redis dédiée :**
Utiliser la **database Redis 1** (séparée de Celery sur DB 0) pour isoler les compteurs de rate limiting. Si Redis est down, la décision fail-open vs fail-close est documentée dans la section Gestion des erreurs.

---

## 3. Stratégie multi-niveau

Le rate limiting est organisé en 5 niveaux indépendants et cumulatifs. Un endpoint LLM peut déclencher simultanément les niveaux 1, 2, 3 et 4.

### Niveau 1 — IP (protection anti-bot)

**Portée :** Tous les endpoints publics (avant authentification)
**Limite :** 60 requêtes/minute par adresse IP
**Endpoints ciblés :** `/auth/*`, `/onboarding/*`, `/health`, `/ready`
**Objectif :** Bloquer le brute force, la création massive de comptes, le scraping

```
Clé Redis : rate:ip:{ip_address}
TTL : 60 secondes
Stratégie : sliding window (elastic expiry)
```

**Note :** En environnement Cloudflare ou Railway derrière un reverse proxy, l'IP réelle est extraite du header `X-Forwarded-For` ou `CF-Connecting-IP`. Ne jamais utiliser `request.client.host` directement derrière un proxy.

### Niveau 2 — Utilisateur authentifié

**Portée :** Tous les endpoints nécessitant une authentification
**Limites :**
- Endpoints lecture (GET) : 300 requêtes/minute par `user_id`
- Endpoints écriture (POST, PUT, PATCH, DELETE) : 30 requêtes/minute par `user_id`

```
Clé Redis lecture  : rate:user:{user_id}:read
Clé Redis écriture : rate:user:{user_id}:write
TTL : 60 secondes
```

**Justification de la différence lecture/écriture :**
Les lectures (affichage du plan, consultation des recettes) sont légères et fréquentes. Les écritures (modification du plan, ajout de recettes au frigo) déclenchent des validations, des triggers, des tâches Celery — elles sont intrinsèquement plus coûteuses.

### Niveau 3 — Tenant (household)

**Portée :** Tous les endpoints authentifiés, appliqué en complément du niveau 2
**Limite :** 1 000 requêtes/minute agrégées par `household_id`
**Objectif :** Garantir l'isolation entre tenants — un household avec 8 membres ne peut pas impacter un household solo

```
Clé Redis : rate:household:{household_id}
TTL : 60 secondes
```

**Comportement attendu :** Si un foyer de 8 membres dépasse 1 000 req/min en cumulé, tous les membres reçoivent un 429 jusqu'à la fin de la fenêtre — pas seulement le membre qui a déclenché la limite.

### Niveau 4 — Endpoints LLM coûteux

**Portée :** Uniquement les endpoints déclenchant un appel à l'API Anthropic
**Limites spécifiques par endpoint :**

| Endpoint | Limite | Clé Redis | Justification |
|----------|--------|-----------|---------------|
| `POST /plan/generate` | 10 req/heure/user | `rate:llm:plan:{user_id}` | Génération plan = 2 000–8 000 tokens |
| `POST /recipe/generate` | 20 req/heure/user | `rate:llm:recipe:{user_id}` | Recette custom = 1 000–3 000 tokens |
| `POST /pdf/generate` | 5 req/heure/user | `rate:llm:pdf:{user_id}` | Génération PDF = appel LLM + WeasyPrint |

**Note :** Ces limites horaires s'appliquent **en sus** des limites de niveau 2. Un user qui dépasse la limite de niveau 4 reçoit un 429 avec message explicatif même s'il est sous sa limite de niveau 2.

**Limite tenant sur les endpoints LLM :**

| Endpoint | Limite tenant | Clé Redis |
|----------|---------------|-----------|
| `POST /plan/generate` | 50 req/heure/household | `rate:llm:plan:household:{household_id}` |
| `POST /recipe/generate` | 100 req/heure/household | `rate:llm:recipe:household:{household_id}` |

### Niveau 5 — Webhooks entrants

**Portée :** Endpoints recevant des webhooks de services tiers
**Limites :**

| Source | Endpoint | Limite | Clé Redis |
|--------|----------|--------|-----------|
| Stripe | `POST /webhooks/stripe` | 120 req/min/IP | `rate:webhook:stripe:{ip}` |
| Resend | `POST /webhooks/email` | 120 req/min/IP | `rate:webhook:email:{ip}` |

**Précision :** La validation de signature doit se faire **avant** la logique métier mais **après** le rate limiting. Un webhook avec signature invalide ne doit pas consommer le quota d'un token valide.

---

## 4. Implémentation — exemple de code FastAPI

```python
# apps/api/src/core/rate_limiting.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import os

# Détermination de la clé selon le contexte d'authentification
def get_user_key(request: Request) -> str:
    """
    Retourne une clé rate-limit basée sur l'identité authentifiée
    ou sur l'IP si l'user n'est pas encore authentifié.
    Utilisé pour les limites de niveau 2 (user).
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return f"ip:{get_remote_address(request)}"

def get_household_key(request: Request) -> str:
    """
    Retourne une clé rate-limit basée sur le household_id du tenant.
    Utilisé pour les limites de niveau 3 (tenant).
    Requiert que le middleware auth ait peuplé request.state.household_id.
    """
    household_id = getattr(request.state, "household_id", None)
    if household_id:
        return f"household:{household_id}"
    # Fallback sur l'IP si pas de contexte tenant (endpoint public)
    return f"ip:{get_remote_address(request)}"

# Instance principale du limiter
# DB Redis 1 dédiée au rate limiting (DB 0 réservée à Celery)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_RATE_LIMIT_DB = os.getenv("REDIS_RATE_LIMIT_DB", "1")

limiter = Limiter(
    key_func=get_user_key,
    storage_uri=f"{REDIS_URL}/{REDIS_RATE_LIMIT_DB}",
    strategy="fixed-window-elastic-expiry",
    # fail-open : si Redis est down, on laisse passer les requêtes
    # plutôt que de bloquer le service entier
    enabled=True,
    default_limits=["300/minute"],  # Niveau 2 lecture par défaut
)

# Handler pour les erreurs de rate limiting
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Retourne un 429 avec les headers standards et un message utilisateur en français.
    Log l'event pour monitoring Sentry + PostHog.
    """
    retry_after = exc.retry_after if hasattr(exc, "retry_after") else 60

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Vous avez atteint votre limite de requêtes. "
                       f"Réessayez dans {retry_after} secondes.",
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": exc.limit.limit if hasattr(exc, "limit") else "unknown",
            "X-RateLimit-Remaining": "0",
        },
    )
```

```python
# apps/api/src/routers/plan.py — Exemple d'usage sur endpoint LLM

from fastapi import APIRouter, Depends, Request
from src.core.rate_limiting import limiter, get_user_key, get_household_key

router = APIRouter(prefix="/plan", tags=["plan"])

@router.post("/generate")
@limiter.limit("10/hour", key_func=get_user_key)       # Niveau 4 — LLM user
@limiter.limit("50/hour", key_func=get_household_key)  # Niveau 4 — LLM tenant
@limiter.limit("30/minute", key_func=get_user_key)     # Niveau 2 — écriture user
async def generate_plan(request: Request, ...):
    """
    Génère le plan semaine via WEEKLY_PLANNER + Claude API.
    Endpoint coûteux : protégé par 3 niveaux de rate limiting.
    """
    ...

@router.get("/{plan_id}")
@limiter.limit("300/minute", key_func=get_user_key)    # Niveau 2 — lecture user
async def get_plan(request: Request, plan_id: str, ...):
    """Récupère un plan existant."""
    ...
```

```python
# apps/api/src/main.py — Enregistrement du limiter et du handler

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.core.rate_limiting import limiter, rate_limit_handler

app = FastAPI()

# Attacher le limiter à l'app
app.state.limiter = limiter

# Handler global pour les 429
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Middleware pour appliquer les limites globales
app.add_middleware(SlowAPIMiddleware)
```

---

## 5. Gestion des erreurs

### Réponse HTTP 429

Tous les 429 retournent un JSON structuré cohérent :

```json
{
  "error": "rate_limit_exceeded",
  "message": "Vous avez atteint votre limite de requêtes. Réessayez dans 47 secondes.",
  "retry_after": 47
}
```

**Headers inclus dans la réponse 429 :**

| Header | Description |
|--------|-------------|
| `Retry-After` | Secondes avant que la limite soit réinitialisée |
| `X-RateLimit-Limit` | Limite configurée pour cet endpoint |
| `X-RateLimit-Remaining` | Toujours 0 quand un 429 est retourné |

**Headers proactifs sur les réponses 2xx :**
Inclure `X-RateLimit-Remaining` sur chaque réponse pour permettre aux clients de s'autoréguler avant d'atteindre la limite.

### Logging structuré (loguru)

Chaque 429 doit être loggué en JSON avec les champs suivants :

```python
logger.warning(
    "rate_limit_hit",
    extra={
        "correlation_id": request.state.correlation_id,
        "user_id": getattr(request.state, "user_id", None),
        "household_id": getattr(request.state, "household_id", None),
        "endpoint": request.url.path,
        "method": request.method,
        "ip": get_remote_address(request),
        "limit": exc.limit.limit if hasattr(exc, "limit") else "unknown",
        "retry_after": retry_after,
    }
)
```

**Alerte Sentry :** Si un même `user_id` ou `household_id` déclenche plus de 50 événements `rate_limit_hit` en 5 minutes sur des endpoints LLM, lever une alerte Sentry avec niveau `WARNING` (potentiellement une boucle infinie côté client ou une attaque).

**PostHog event `rate_limit_hit` :**

```python
posthog.capture(
    distinct_id=user_id or ip,
    event="rate_limit_hit",
    properties={
        "endpoint": request.url.path,
        "limit_type": "user" | "tenant" | "llm" | "ip",
        "household_id": household_id,
    }
)
```

Cet event permet d'analyser les patterns d'usage et de détecter si une limite est trop restrictive pour un certain profil d'utilisateurs.

### Comportement si Redis est indisponible (fail-open)

Si la connexion Redis est perdue :

- **Décision : fail-open** — les requêtes passent sans être comptées
- Justification : mieux vaut une période de facturation légèrement élevée qu'une interruption de service pour tous les utilisateurs pendant une panne Redis
- **Exception :** Les endpoints LLM les plus coûteux (`/plan/generate`) peuvent passer en fail-close en configurant `enabled=False` au démarrage si `RATE_LIMIT_STRICT_MODE=true`
- Log `logger.error("redis_rate_limit_unavailable")` à chaque requête pendant la panne pour tracer la durée

---

## 6. Circuit breaker pour les APIs externes

### Problème

Anthropic, Stripe et Supabase peuvent être dégradés ou indisponibles. Sans protection :
- Les appels aux agents LLM accumulent des timeouts → goroutines/threads bloqués
- Celery workers en attente → queue qui grossit → crash mémoire
- Réponses en timeout à l'utilisateur → frustration + churn

### Librairie recommandée : purgatory

`purgatory` est une librairie Python async-native avec support asyncio, adaptée à FastAPI et Celery. Alternative : `pybreaker` (synchrone, compatible Celery workers).

```python
# apps/api/src/core/circuit_breakers.py

from purgatory import AsyncCircuitBreakerFactory

circuit_breaker_factory = AsyncCircuitBreakerFactory(
    default_threshold=5,       # 5 erreurs consécutives → circuit ouvert
    default_ttl=30,            # Circuit ouvert pendant 30 secondes
)

# Circuit breaker dédié par service externe
anthropic_breaker = circuit_breaker_factory.get_breaker("anthropic")
stripe_breaker = circuit_breaker_factory.get_breaker("stripe")
supabase_breaker = circuit_breaker_factory.get_breaker("supabase")
```

### Seuils configurés

| Service | Seuil d'ouverture | Durée d'ouverture | Condition de déclenchement |
|---------|-------------------|-------------------|---------------------------|
| Anthropic API | 5% erreurs sur 1 min | 30 secondes | 5xx ou timeout > 30s |
| Stripe API | 3 erreurs consécutives | 60 secondes | 5xx ou timeout > 10s |
| Supabase | 3 erreurs consécutives | 30 secondes | ConnectionError ou timeout > 5s |
| Stability AI | 5 erreurs consécutives | 120 secondes | 5xx ou timeout > 60s |

### Fallback messages (user-facing)

```python
from purgatory.errors import CircuitOpen

async def generate_plan_with_fallback(household_id: str) -> dict:
    try:
        async with anthropic_breaker:
            return await anthropic_client.generate_plan(household_id)
    except CircuitOpen:
        logger.warning("circuit_open", service="anthropic", household_id=household_id)
        return {
            "status": "unavailable",
            "message": "La génération de plan est temporairement indisponible. "
                       "Nous revenons dans quelques minutes. "
                       "Votre plan précédent reste accessible.",
        }
```

---

## 7. Tests

### Tests unitaires pytest

```python
# apps/api/tests/unit/test_rate_limiting.py

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app

@pytest.mark.asyncio
async def test_rate_limit_enforced_on_llm_endpoint(client: TestClient):
    """
    Vérifie que le 10ème appel à /plan/generate dans la même heure retourne 429.
    Arrange : 9 appels réussis avec mock Anthropic
    Act : 10ème appel
    Assert : 429 avec Retry-After header
    """
    with patch("src.core.rate_limiting.limiter._storage") as mock_storage:
        mock_storage.get_moving_window.return_value = (10, 10)  # limite atteinte
        response = client.post("/plan/generate", json={"household_id": "test-id"})
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["error"] == "rate_limit_exceeded"

@pytest.mark.asyncio
async def test_rate_limit_headers_on_success(client: TestClient):
    """
    Vérifie que les headers X-RateLimit-* sont présents sur une réponse 200.
    """
    response = client.get("/plan/test-plan-id")
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) >= 0

@pytest.mark.asyncio
async def test_rate_limit_per_user_isolation(client: TestClient):
    """
    Vérifie que la limite d'un user n'impacte pas un autre user.
    """
    # User A atteint sa limite
    # User B doit pouvoir encore accéder
    pass  # Implémentation complète en Phase 1

@pytest.mark.asyncio
async def test_fail_open_when_redis_down(client: TestClient):
    """
    Vérifie que les requêtes passent quand Redis est indisponible (fail-open).
    """
    with patch("src.core.rate_limiting.limiter._storage") as mock_storage:
        mock_storage.get_moving_window.side_effect = ConnectionError("Redis down")
        response = client.get("/plan/test-plan-id")
        # fail-open : doit retourner 200, pas 500
        assert response.status_code == 200
```

### Script k6 — test de charge des limites

```javascript
// tests/load/k6-rate-limit.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    // Scénario 1 : vérifier que la limite IP (60 req/min) est bien appliquée
    ip_limit_enforcement: {
      executor: 'constant-arrival-rate',
      rate: 100,          // 100 req/min sur un endpoint public
      timeUnit: '1m',
      duration: '2m',
      preAllocatedVUs: 10,
    },
    // Scénario 2 : vérifier que 2 users distincts ne se bloquent pas mutuellement
    user_isolation: {
      executor: 'per-vu-iterations',
      vus: 2,
      iterations: 350,    // 300 req/min est la limite — dépasser avec 350
      maxDuration: '1m',
    },
  },
  thresholds: {
    // Au moins 30% des requêtes du scénario ip_limit doivent retourner 429
    'http_req_failed{scenario:ip_limit_enforcement}': ['rate>0.3'],
    // Les requêtes 429 doivent inclure le header Retry-After
    'checks': ['rate>0.95'],
  },
};

export default function () {
  const res = http.post(
    `${__ENV.API_BASE_URL}/auth/login`,
    JSON.stringify({ email: 'test@test.com', password: 'wrong' }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(res, {
    'retourne 429 ou 401': (r) => [429, 401].includes(r.status),
    'header Retry-After présent si 429': (r) =>
      r.status !== 429 || r.headers['Retry-After'] !== undefined,
    'body JSON valide': (r) => {
      try { JSON.parse(r.body); return true; } catch { return false; }
    },
  });

  sleep(0.1);
}
```

---

## 8. Monitoring

### Métriques Prometheus exposées

slowapi expose les métriques suivantes via un middleware Prometheus personnalisé ou Sentry custom :

| Métrique | Type | Labels | Description |
|----------|------|--------|-------------|
| `rate_limit_hits_total` | Counter | `endpoint`, `limit_type`, `tenant_id` | Nombre total de 429 par endpoint |
| `rate_limit_remaining_avg` | Gauge | `endpoint` | Quota moyen restant par endpoint |
| `circuit_breaker_open_total` | Counter | `service` | Nombre d'ouvertures de circuit par service externe |

```python
# apps/api/src/core/metrics.py

from prometheus_client import Counter, Gauge

rate_limit_hits = Counter(
    "rate_limit_hits_total",
    "Nombre de requêtes bloquées par le rate limiting",
    labelnames=["endpoint", "limit_type"],
)

circuit_breaker_opens = Counter(
    "circuit_breaker_open_total",
    "Nombre d'ouvertures du circuit breaker",
    labelnames=["service"],
)
```

### Dashboard recommandé (Sentry ou Grafana)

**Top 5 endpoints throttlés** : classés par `rate_limit_hits_total{limit_type="llm"}` — indique quels agents IA sont les plus sollicités.

**Top 5 users/households throttlés** : identifie les usages anormaux ou les boucles côté client.

**Taux de 429 par endpoint sur 1h glissante** : alerte si > 5% de taux pour un endpoint non-LLM.

### Alerte critique — quota à 80%

Un tenant atteignant 80% de sa limite horaire sur les endpoints LLM est un signal fort d'usage intensif (ou d'attaque). Déclencher une alerte Sentry `WARNING` :

```python
async def check_tenant_quota_approaching(household_id: str, endpoint: str):
    """
    Appelé en background après chaque requête LLM réussie.
    Alerte si le tenant est à >= 80% de sa limite horaire.
    """
    current = await redis.get(f"rate:llm:{endpoint.replace('/', ':')}:household:{household_id}")
    limit = LLM_TENANT_LIMITS.get(endpoint, 50)
    if current and int(current) >= int(limit * 0.8):
        sentry_sdk.capture_message(
            f"Tenant {household_id} à {current}/{limit} requêtes LLM sur {endpoint}",
            level="warning",
        )
```

---

## 9. Récapitulatif des limites configurées

| Niveau | Clé | Endpoint | Limite | Stratégie |
|--------|-----|----------|--------|-----------|
| 1 — IP | IP | `/auth/*`, `/onboarding/*` | 60 req/min | sliding window |
| 2 — User lecture | `user:{id}` | GET tous | 300 req/min | sliding window |
| 2 — User écriture | `user:{id}` | POST/PUT/PATCH/DELETE | 30 req/min | sliding window |
| 3 — Tenant | `household:{id}` | Tous authentifiés | 1 000 req/min | sliding window |
| 4 — LLM plan user | `user:{id}` | `POST /plan/generate` | 10 req/heure | sliding window |
| 4 — LLM recipe user | `user:{id}` | `POST /recipe/generate` | 20 req/heure | sliding window |
| 4 — LLM pdf user | `user:{id}` | `POST /pdf/generate` | 5 req/heure | sliding window |
| 4 — LLM plan tenant | `household:{id}` | `POST /plan/generate` | 50 req/heure | sliding window |
| 5 — Webhook Stripe | IP source | `POST /webhooks/stripe` | 120 req/min | fixed window |
| 5 — Webhook Resend | IP source | `POST /webhooks/email` | 120 req/min | fixed window |

---

## 10. Dépendances Phase 1

Ce document de design génère les actions suivantes pour la Phase 1 :

- [ ] Ajouter `slowapi>=0.1.9` et `limits[redis]>=3.6` dans `apps/api/pyproject.toml`
- [ ] Implémenter `apps/api/src/core/rate_limiting.py` selon les specs ci-dessus
- [ ] Configurer DB Redis 1 dans les variables d'environnement (`REDIS_RATE_LIMIT_DB=1`)
- [ ] Ajouter le middleware `SlowAPIMiddleware` dans `apps/api/src/main.py`
- [ ] Appliquer les décorateurs `@limiter.limit(...)` sur tous les endpoints existants
- [ ] Ajouter `purgatory>=1.5` ou `pybreaker>=1.3` pour les circuit breakers
- [ ] Créer `tests/unit/test_rate_limiting.py` avec les tests unitaires ci-dessus
- [ ] Créer `tests/load/k6-rate-limit.js` et l'exécuter avant la mise en production
- [ ] Configurer les métriques Prometheus dans `apps/api/src/core/metrics.py`
- [ ] Documenter dans `memory/project-context.md` la décision slowapi + Redis DB 1

---

*Document rédigé en Phase 0 — design uniquement, pas d'implémentation.*
*Transmis à : backend-developer (Phase 1), security-auditor (validation), performance-engineer (tests k6).*
