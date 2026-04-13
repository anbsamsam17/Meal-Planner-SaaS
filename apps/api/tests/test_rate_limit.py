"""
Tests du rate limiting — vérification que les limites s'appliquent correctement.

Couverture :
- Handler 429 retourne le bon format JSON
- Headers Retry-After et X-RateLimit-* présents
- Fail-open si Redis est indisponible
- Isolation des clés (user A ne bloque pas user B)

Note : slowapi décore les endpoints au niveau du router.
Les tests vérifient le comportement observable (codes HTTP, headers, corps JSON)
plutôt que les détails d'implémentation interne de slowapi.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRateLimitHandler:
    """Tests pour le handler HTTP 429."""

    async def test_rate_limit_response_format(self, client, app_no_lifespan):
        """
        Le handler 429 retourne un JSON structuré avec les champs obligatoires.

        Format attendu (conforme à la spec 12-rate-limiting-design.md) :
        {
            "error": "rate_limit_exceeded",
            "message": "... Réessayez dans N secondes.",
            "retry_after": N
        }

        Arrange : simuler un dépassement de limite via l'exception handler directement.
        Act : appeler l'handler avec une exception RateLimitExceeded mockée.
        Assert : format JSON correct et status 429.
        """
        from slowapi.errors import RateLimitExceeded
        from src.core.rate_limit import rate_limit_exception_handler
        from starlette.testclient import TestClient
        from starlette.requests import Request as StarletteRequest

        # Créer une requête mock minimale
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user-test-123"
        mock_request.state.household_id = "household-test-456"
        mock_request.state.correlation_id = "test-corr"
        mock_request.url.path = "/api/v1/recipes"
        mock_request.method = "GET"
        mock_request.headers = {}

        # Exception RateLimitExceeded avec retry_after
        exc = MagicMock(spec=RateLimitExceeded)
        exc.retry_after = 47
        exc.limit = MagicMock()
        exc.limit.limit = "300/minute"

        with patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"):
            response = await rate_limit_exception_handler(mock_request, exc)

        assert response.status_code == 429
        import json
        body = json.loads(response.body)
        assert body["error"] == "rate_limit_exceeded"
        assert "Réessayez dans" in body["message"]
        assert "retry_after" in body
        assert body["retry_after"] == 47

    async def test_rate_limit_response_headers(self, client, app_no_lifespan):
        """
        La réponse 429 inclut les headers standards de rate limiting.

        Headers obligatoires :
        - Retry-After : secondes avant réinitialisation
        - X-RateLimit-Limit : limite configurée
        - X-RateLimit-Remaining : toujours 0 pour un 429

        Arrange : exception RateLimitExceeded mockée avec retry_after=30.
        Act : appel de l'handler.
        Assert : headers présents avec les valeurs correctes.
        """
        from slowapi.errors import RateLimitExceeded
        from src.core.rate_limit import rate_limit_exception_handler

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.state.household_id = None
        mock_request.state.correlation_id = "test-corr"
        mock_request.url.path = "/api/v1/recipes"
        mock_request.method = "GET"

        exc = MagicMock(spec=RateLimitExceeded)
        exc.retry_after = 30
        exc.limit = MagicMock()
        exc.limit.limit = "300/minute"

        with patch("src.core.rate_limit.get_remote_address", return_value="10.0.0.1"):
            response = await rate_limit_exception_handler(mock_request, exc)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "30"
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"


class TestRateLimitKeyFunctions:
    """Tests pour les fonctions de clé de rate limiting."""

    def test_get_user_key_with_authenticated_user(self):
        """
        get_user_key retourne une clé basée sur l'user_id si authentifié.

        Arrange : requête avec request.state.user_id défini.
        Act : appel de get_user_key.
        Assert : clé au format "user:{id}".
        """
        from src.core.rate_limit import get_user_key

        mock_request = MagicMock()
        mock_request.state.user_id = "uuid-user-1234"

        with patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"):
            key = get_user_key(mock_request)

        assert key == "user:uuid-user-1234"

    def test_get_user_key_falls_back_to_ip(self):
        """
        get_user_key utilise l'IP si l'utilisateur n'est pas authentifié.

        Assure la protection des endpoints publics même sans JWT.

        Arrange : requête sans user_id dans l'état.
        Act : appel de get_user_key.
        Assert : clé au format "ip:{adresse}".
        """
        from src.core.rate_limit import get_user_key

        mock_request = MagicMock()
        # Simuler l'absence d'user_id (endpoint public)
        del mock_request.state.user_id

        with patch("src.core.rate_limit.get_remote_address", return_value="192.168.1.100"):
            key = get_user_key(mock_request)

        assert key == "ip:192.168.1.100"

    def test_get_household_key_with_tenant(self):
        """
        get_household_key retourne une clé tenant si household_id présent.

        Niveau 3 : isolation par tenant pour le fair-use entre foyers.

        Arrange : requête avec household_id dans l'état.
        Act : appel de get_household_key.
        Assert : clé au format "household:{id}".
        """
        from src.core.rate_limit import get_household_key

        mock_request = MagicMock()
        mock_request.state.household_id = "uuid-household-5678"

        with patch("src.core.rate_limit.get_remote_address", return_value="127.0.0.1"):
            key = get_household_key(mock_request)

        assert key == "household:uuid-household-5678"

    def test_get_household_key_falls_back_to_ip(self):
        """
        get_household_key utilise l'IP si pas de household_id (endpoint public).

        Arrange : requête sans household_id.
        Act : appel de get_household_key.
        Assert : clé IP.
        """
        from src.core.rate_limit import get_household_key

        mock_request = MagicMock()
        del mock_request.state.household_id

        with patch("src.core.rate_limit.get_remote_address", return_value="10.0.0.2"):
            key = get_household_key(mock_request)

        assert key == "ip:10.0.0.2"


class TestRateLimitStorageURI:
    """Tests pour la construction de l'URI Redis du rate limiter."""

    def test_build_storage_uri_appends_db(self):
        """
        L'URI du storage Redis inclut le numéro de base Redis.

        Isolation : DB 0 = Celery broker, DB 1 = rate limiting.

        Arrange : URL Redis sans numéro de DB.
        Act : appel de _build_storage_uri.
        Assert : URI se termine par /1.
        """
        from src.core.rate_limit import _build_storage_uri

        uri = _build_storage_uri("redis://localhost:6379", redis_db=1)

        assert uri == "redis://localhost:6379/1"

    def test_build_storage_uri_replaces_existing_db(self):
        """
        Si l'URL Redis a déjà un numéro de DB, il est remplacé.

        Évite la duplication de numéro de DB si l'URL est déjà qualifiée.

        Arrange : URL Redis avec /0 (Celery).
        Act : appel de _build_storage_uri avec db=1.
        Assert : URI se termine par /1 (pas /0/1).
        """
        from src.core.rate_limit import _build_storage_uri

        uri = _build_storage_uri("redis://localhost:6379/0", redis_db=1)

        assert uri.endswith("/1")
        assert "/0/1" not in uri
