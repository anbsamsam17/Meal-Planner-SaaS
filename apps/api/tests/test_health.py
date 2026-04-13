"""
Tests des endpoints de santé : GET /api/v1/health et GET /api/v1/ready.

Couverture :
- /health : liveness ultra-rapide, toujours 200 (3 cas)
- /ready  : readiness avec vérification des dépendances (4 cas)

Convention AAA (Arrange → Act → Assert) appliquée sur chaque test.
"""

import pytest
from unittest.mock import AsyncMock


class TestLiveness:
    """Tests pour GET /api/v1/health — liveness check."""

    async def test_health_returns_200(self, client):
        """
        Cas nominal : /health retourne toujours 200 quel que soit l'état.

        Arrange : application démarrée sans dépendances externes.
        Act : requête GET /api/v1/health.
        Assert : statut 200, corps {"status": "ok"}.
        """
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_health_response_time_acceptable(self, client):
        """
        Contrainte de performance : /health doit répondre en < 100ms.

        Le endpoint ne fait aucun I/O, sa latence est purement liée
        à l'overhead de l'application (routing FastAPI).
        Cible réelle < 5ms, mais 100ms est la limite de test acceptable.

        Arrange : application démarrée.
        Act : mesure du temps de réponse.
        Assert : réponse en moins de 100ms.
        """
        import time

        start = time.monotonic()
        response = await client.get("/api/v1/health")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 100, f"Health trop lent : {elapsed_ms:.1f}ms (limite 100ms)"

    async def test_health_no_db_dependency(self, client, app_no_lifespan):
        """
        Isolation : /health fonctionne même si la DB n'est pas configurée.

        /health ne doit JAMAIS dépendre d'une connexion externe.
        Si la DB est down, /health doit quand même répondre 200
        (pour permettre à Railway de distinguer un process bloqué d'une DB down).

        Arrange : état DB = None (pas de pool configuré).
        Act : requête GET /api/v1/health.
        Assert : statut 200 malgré l'absence de DB.
        """
        app_no_lifespan.state.db_session_factory = None
        app_no_lifespan.state.redis = None

        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_health_returns_correlation_id_header(self, client):
        """
        Le middleware correlation ID injecte X-Correlation-ID dans toutes les réponses.

        Vérifie que le header est présent (tracing distribué).

        Arrange : requête sans header X-Correlation-ID (le middleware en génère un).
        Act : requête GET /api/v1/health.
        Assert : header X-Correlation-ID présent dans la réponse.
        """
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert "x-correlation-id" in response.headers


class TestReadiness:
    """Tests pour GET /api/v1/ready — readiness check."""

    async def test_ready_returns_200_when_model_loaded(self, client, app_no_lifespan):
        """
        Cas nominal : /ready retourne 200 quand le modèle ML est chargé.

        Simule l'état post-startup complet (modèle chargé, pas de DB/Redis
        en mode test unitaire → les vérifications DB/Redis sont skippées quand None).

        Arrange : model_loaded = True, db = None, redis = None.
        Act : requête GET /api/v1/ready.
        Assert : statut 200, corps contenant status="ready".
        """
        app_no_lifespan.state.model_loaded = True
        app_no_lifespan.state.db_session_factory = None
        app_no_lifespan.state.redis = None

        response = await client.get("/api/v1/ready")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["model"] is True

    async def test_ready_returns_503_when_model_not_loaded(self, client, app_no_lifespan):
        """
        Cas d'erreur critique : /ready retourne 503 si le modèle n'est pas encore chargé.

        Simule le démarrage en cours où sentence-transformers charge encore.
        Railway ne doit pas router de trafic dans cet état.

        Arrange : model_loaded = False.
        Act : requête GET /api/v1/ready.
        Assert : statut 503, message d'erreur explicatif.
        """
        app_no_lifespan.state.model_loaded = False

        response = await client.get("/api/v1/ready")

        assert response.status_code == 503
        body = response.json()
        assert "detail" in body

    async def test_ready_returns_503_when_db_down(self, client, app_no_lifespan):
        """
        Cas d'erreur : /ready retourne 503 si la DB est inaccessible.

        Simule une panne de la base de données PostgreSQL.
        L'API ne doit pas recevoir de trafic si elle ne peut pas écrire en DB.

        Arrange : modèle chargé, DB mock qui lève une exception.
        Act : requête GET /api/v1/ready.
        Assert : statut 503.
        """
        app_no_lifespan.state.model_loaded = True

        # Mock d'une session DB qui lève une exception à l'exécution
        failing_session = AsyncMock()
        failing_session.execute.side_effect = ConnectionError("DB connection refused")

        failing_factory = AsyncMock()
        failing_factory.return_value.__aenter__ = AsyncMock(return_value=failing_session)
        failing_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        app_no_lifespan.state.db_session_factory = failing_factory

        response = await client.get("/api/v1/ready")

        assert response.status_code == 503

    async def test_ready_returns_503_when_redis_down(self, client, app_no_lifespan):
        """
        Cas d'erreur : /ready retourne 503 si Redis est inaccessible.

        Redis est critique pour le rate limiting. Une panne Redis doit
        être signalée via /ready même si la DB fonctionne.

        Arrange : modèle chargé, DB None, Redis mock qui lève une exception.
        Act : requête GET /api/v1/ready.
        Assert : statut 503.
        """
        app_no_lifespan.state.model_loaded = True
        app_no_lifespan.state.db_session_factory = None

        failing_redis = AsyncMock()
        failing_redis.ping.side_effect = ConnectionError("Redis connection refused")
        app_no_lifespan.state.redis = failing_redis

        response = await client.get("/api/v1/ready")

        assert response.status_code == 503

    async def test_ready_includes_latency_metrics(self, client, app_no_lifespan):
        """
        /ready inclut les latences DB et Redis dans sa réponse pour le monitoring.

        Ces métriques permettent de détecter une dégradation progressive
        avant qu'elle ne devienne une panne complète.

        Arrange : modèle chargé, Redis mock opérationnel.
        Act : requête GET /api/v1/ready.
        Assert : champs redis_latency_ms présents si redis configuré.
        """
        app_no_lifespan.state.model_loaded = True
        app_no_lifespan.state.db_session_factory = None

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        app_no_lifespan.state.redis = mock_redis

        response = await client.get("/api/v1/ready")

        assert response.status_code == 200
        body = response.json()
        assert "redis_latency_ms" in body
        assert body["redis"] is True
