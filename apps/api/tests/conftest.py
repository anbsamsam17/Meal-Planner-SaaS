"""
Fixtures pytest pour les tests de l'API MealPlanner.

Organisation :
- client : AsyncClient httpx configuré pour les tests async
- mock_redis : mock du client Redis pour éviter la dépendance externe
- db_session : session DB en transaction (rollback automatique après chaque test)

Convention : tous les tests sont async (asyncio_mode = "auto" dans pyproject.toml).
Les fixtures de scope "session" sont partagées entre tous les tests d'une session.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Backend asyncio pour pytest-anyio (requis par pytest-asyncio)."""
    return "asyncio"


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Override les variables d'environnement pour les tests.

    Évite que les tests nécessitent un .env local complet.
    Les valeurs sont factices mais valides pour la validation Pydantic.
    """
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test_anon_key_" + "a" * 50,
        "SUPABASE_SERVICE_ROLE_KEY": "test_service_role_key_" + "b" * 50,
        "GOOGLE_AI_API_KEY": "test_google_ai_key_" + "c" * 30,
        "ANTHROPIC_API_KEY": "test_anthropic_key_" + "c" * 40,
        "SPOONACULAR_API_KEY": "test_spoonacular_key",
        "EDAMAM_APP_ID": "test_edamam_id",
        "EDAMAM_APP_KEY": "test_edamam_key",
        "ENV": "dev",
        "LOG_LEVEL": "DEBUG",
        # --- Variables Phase 2 : Stripe, MinIO ---
        # Valeurs factices mais valides pour la validation Pydantic.
        # Les endpoints Stripe retournent 503 si STRIPE_SECRET_KEY est vide (comportement testé).
        "STRIPE_SECRET_KEY": "sk_test_fake_key_for_tests",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_fake_secret",
        "STRIPE_PRICE_FAMILLE": "price_test_famille",
        "STRIPE_PRICE_COACH": "price_test_coach",
        "STRIPE_SUCCESS_URL": "http://localhost:3000/billing/success",
        "STRIPE_CANCEL_URL": "http://localhost:3000/billing/cancel",
        "MINIO_ENDPOINT": "http://localhost:9000",
        "MINIO_ACCESS_KEY": "test_access",
        "MINIO_SECRET_KEY": "test_secret",
        "MINIO_BUCKET_PDFS": "test-pdfs",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    # Invalide le cache lru_cache de get_settings pour qu'il recharge avec les nouvelles vars
    from src.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def app_no_lifespan():
    """
    Application FastAPI sans lifespan (startup/shutdown).

    Utilisé pour les tests unitaires qui ne nécessitent pas de vraie DB ou Redis.
    La connexion DB et Redis est mockée via request.app.state.

    FIX : utiliser un vrai Limiter slowapi en mode mémoire (storage_uri="memory://")
    au lieu d'un MagicMock. SlowAPIMiddleware attend un Limiter réel avec des méthodes
    awaitable — un MagicMock provoque TypeError ("object MagicMock can't be used in 'await'").
    """
    from src.main import create_app
    from src.core.rate_limit import create_limiter
    import src.core.rate_limit as _rate_limit_module

    # Créer l'app sans déclencher le lifespan
    application = create_app()

    # Limiter en mode mémoire pour les tests (pas de Redis requis)
    test_limiter = create_limiter(redis_url="memory://", redis_db=0)
    _rate_limit_module.limiter = test_limiter
    application.state.limiter = test_limiter

    # Simuler l'état post-startup
    application.state.model_loaded = True
    application.state.db_session_factory = None
    application.state.redis = None

    return application


@pytest_asyncio.fixture
async def client(app_no_lifespan):
    """
    AsyncClient httpx configuré pour les tests de l'API.

    Utilise ASGITransport pour appeler directement l'app ASGI
    sans démarrer un vrai serveur HTTP.

    Exemple d'utilisation :
        async def test_health(client):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_no_lifespan),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """
    Mock du client Redis aioredis.

    Simule les opérations Redis (ping, get, set) sans dépendance externe.
    Utilisé pour tester le rate limiting et le cache sans Redis réel.

    Exemple :
        async def test_ready(client, mock_redis, app_no_lifespan):
            app_no_lifespan.state.redis = mock_redis
            response = await client.get("/api/v1/ready")
            mock_redis.ping.assert_awaited_once()
    """
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.ttl.return_value = 60
    return mock


@pytest.fixture
def mock_db_session():
    """
    Mock d'une session SQLAlchemy async.

    Simule les opérations DB (execute, scalar, mappings) sans base de données réelle.
    Utile pour tester les endpoints sans Supabase/PostgreSQL local.
    """
    session = AsyncMock()

    # Mock du context manager async (async with db_session() as session)
    session_factory = AsyncMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    return session_factory, session


@pytest.fixture
def valid_jwt_token():
    """
    Token JWT valide pour les tests d'authentification.

    Construit un payload JWT minimal compatible avec le format Supabase.
    L'audience "authenticated" est requise car security.py fait verify_aud=True.
    Ne pas utiliser en production — clé de signature fictive.
    """
    import time
    from jose import jwt

    payload = {
        "sub": "test-user-uuid-1234",
        "email": "test@mealplanner.fr",
        # FIX : le champ "aud" est obligatoire — security.py vérifie audience="authenticated"
        "aud": "authenticated",
        "role": "authenticated",
        "app_metadata": {
            "household_id": "test-household-uuid-5678",
        },
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }

    # Clé fictive alignée avec SUPABASE_ANON_KEY dans mock_settings
    secret = "test_anon_key_" + "a" * 50
    return jwt.encode(payload, secret, algorithm="HS256")
