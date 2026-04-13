"""
Configuration centralisée de l'API Presto.

Utilise Pydantic Settings v2 pour charger et valider toutes les variables d'environnement
au démarrage. Une erreur de configuration arrête l'application immédiatement avec un
message clair — évite les erreurs silencieuses en production.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Paramètres globaux de l'application.

    Chaque variable est documentée avec son usage. Les variables marquées
    comme obligatoires (sans valeur par défaut) arrêtent le démarrage si absentes.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Permet les variables d'env supplémentaires non déclarées ici
        extra="ignore",
        # Validation stricte : un int attendu refuse une chaîne non numérique
        validate_default=True,
    )

    # -------------------------------------------------------------------------
    # Base de données
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        description="URL de connexion PostgreSQL asyncpg. "
        "Format : postgresql+asyncpg://user:pass@host:port/db"
    )

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="URL Redis principale. DB 0 réservée à Celery broker.",
    )
    RATE_LIMIT_REDIS_DB: int = Field(
        default=1,
        description="Numéro de la base Redis dédiée au rate limiting (DB 0 = Celery).",
    )

    # -------------------------------------------------------------------------
    # Supabase Auth
    # -------------------------------------------------------------------------
    SUPABASE_URL: str = Field(
        description="URL de l'instance Supabase. Format : https://<project>.supabase.co"
    )
    SUPABASE_ANON_KEY: str = Field(
        description="Clé publique Supabase (JWT anon). Utilisée côté client web."
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        description="Clé service-role Supabase. Bypass RLS. "
        "JAMAIS exposée au frontend. Réservée au backend et aux agents IA."
    )

    # -------------------------------------------------------------------------
    # LLM — Provider principal (Gemini par défaut, Anthropic optionnel)
    # Swap Anthropic → Gemini (2026-04-12) : free tier 15 req/min suffisant pour batch nocturne
    # Pour revenir à Anthropic : LLM_PROVIDER=anthropic + remplir ANTHROPIC_API_KEY
    # -------------------------------------------------------------------------
    LLM_PROVIDER: Literal["gemini", "anthropic"] = Field(
        default="gemini",
        description="Provider LLM actif. 'gemini' (défaut, gratuit 15 req/min) ou 'anthropic' (payant).",
    )
    GOOGLE_AI_API_KEY: str = Field(
        description="Clé API Google AI Studio pour Gemini. "
        "Obtenir sur : https://aistudio.google.com/apikey. "
        "Obligatoire si LLM_PROVIDER=gemini."
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Modèle Gemini à utiliser. gemini-2.0-flash = free tier jusqu'à 15 req/min.",
    )
    # Anthropic conservé en optionnel — plus obligatoire depuis la migration Gemini
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Clé API Anthropic (optionnel). "
        "Uniquement requis si LLM_PROVIDER=anthropic. "
        "Laisser vide pour le provider Gemini par défaut.",
    )

    # -------------------------------------------------------------------------
    # Sources de recettes
    # -------------------------------------------------------------------------
    # FIX #11 (review Phase 1 2026-04-12) : SPOONACULAR_API_KEY est le nom correct dans config.py
    # devops-engineer doit corriger .env.example : SPOONACULAR_KEY → SPOONACULAR_API_KEY
    SPOONACULAR_API_KEY: str = Field(
        description="Clé API Spoonacular. Free tier = 150 req/jour. Surveiller le quota."
    )
    EDAMAM_APP_ID: str = Field(description="Application ID Edamam.")
    EDAMAM_APP_KEY: str = Field(description="Application Key Edamam.")

    # -------------------------------------------------------------------------
    # Stripe Billing — Phase 2
    # Mode test : sk_test_... (dashboard test.stripe.com)
    # -------------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = Field(
        default="",
        description="Clé secrète Stripe. Format sk_test_... (test) ou sk_live_... (prod). "
        "Obligatoire en Phase 2 pour les endpoints billing. "
        "Laisser vide → les endpoints billing retournent HTTP 503.",
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="",
        description="Secret de vérification des webhooks Stripe. "
        "Format whsec_... Obtenir dans Dashboard Stripe > Webhooks. "
        "Laisser vide → webhook endpoint retourne HTTP 500.",
    )
    STRIPE_PRICE_FAMILLE: str = Field(
        default="",
        description="Price ID Stripe du plan Famille (price_...). "
        "Créer dans Dashboard Stripe > Products.",
    )
    STRIPE_PRICE_COACH: str = Field(
        default="",
        description="Price ID Stripe du plan Coach Nutrition (price_...).",
    )
    # URLs de redirection Stripe Checkout (optionnelles — défaut localhost pour le dev)
    STRIPE_SUCCESS_URL: str = Field(
        default="http://localhost:3000/billing/success",
        description="URL de redirection après paiement Stripe réussi.",
    )
    STRIPE_CANCEL_URL: str = Field(
        default="http://localhost:3000/billing/cancel",
        description="URL de redirection si l'utilisateur annule le paiement Stripe.",
    )

    # -------------------------------------------------------------------------
    # Stockage objet — MinIO (dev) / Cloudflare R2 (prod)
    # -------------------------------------------------------------------------
    STORAGE_BACKEND: str = Field(
        default="minio",
        description="Backend de stockage : 'minio' (dev local) ou 'r2' (prod Cloudflare).",
    )
    MINIO_ENDPOINT: str = Field(
        default="http://localhost:9000",
        description="URL du serveur MinIO local.",
    )
    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin",
        description="Clé d'accès MinIO.",
    )
    MINIO_SECRET_KEY: str = Field(
        default="minioadmin",
        description="Clé secrète MinIO.",
    )
    MINIO_BUCKET: str = Field(
        default="mealplanner-pdfs",
        description="Nom du bucket MinIO pour les PDFs.",
    )
    # Alias explicite MINIO_BUCKET_PDFS → pointe vers le même bucket
    # Utilisé dans le worker (BOOK_GENERATOR) et dans les tests via conftest.py
    MINIO_BUCKET_PDFS: str = Field(
        default="mealplanner-pdfs",
        description="Nom du bucket MinIO/R2 dédié aux PDFs générés (alias de MINIO_BUCKET).",
    )

    # -------------------------------------------------------------------------
    # Monitoring (optionnels — startup ne plante pas si absents)
    # -------------------------------------------------------------------------
    SENTRY_DSN: str | None = Field(
        default=None,
        description="DSN Sentry pour le monitoring des erreurs. "
        "Optionnel en dev, obligatoire en prod.",
    )
    POSTHOG_KEY: str | None = Field(
        default=None,
        description="Clé PostHog pour les analytics produit. Optionnel.",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    # FIX #12 (review Phase 1 2026-04-12) : accepter "test" (CI) et les deux noms de variable ENV/ENVIRONMENT
    # Le CI utilise ENVIRONMENT=test, le .env.example utilise ENVIRONMENT=development.
    # AliasChoices (Pydantic v2) accepte les deux noms de variable d'environnement.
    # "test" ajouté au Literal pour éviter ValidationError au démarrage CI.
    ENV: Literal["dev", "test", "staging", "prod", "production"] = Field(
        default="dev",
        description="Environnement d'exécution. Contrôle le format des logs et Sentry.",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Niveau de log loguru. DEBUG en dev, INFO en prod.",
    )
    PORT: int = Field(
        default=8000,
        description="Port d'écoute uvicorn. Surchargé par Railway via la variable $PORT.",
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Origines CORS séparées par des virgules. "
        "Ex: https://hop-presto.vercel.app,http://localhost:3000",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Retourne CORS_ORIGINS comme liste."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Vérifie que la DATABASE_URL est au format asyncpg attendu par SQLAlchemy.
        Alembic utilise une URL synchrone (postgresql://), l'API utilise asyncpg.
        """
        if not v.startswith(("postgresql+asyncpg://", "postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL doit commencer par postgresql+asyncpg://, "
                "postgresql:// ou postgres://. "
                f"Valeur reçue : {v[:30]}..."
            )
        return v



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retourne l'instance singleton des settings.

    Le décorateur @lru_cache garantit qu'une seule instance est créée
    et que les variables d'environnement sont lues une seule fois au démarrage.
    Injecter via FastAPI Depends(get_settings) dans les routes.
    """
    return Settings()
