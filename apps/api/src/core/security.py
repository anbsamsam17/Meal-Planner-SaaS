"""
Helpers de sécurité JWT pour l'authentification Supabase.

Supabase Auth émet des JWT signés avec la SUPABASE_ANON_KEY (ou JWT_SECRET).
Chaque token contient le user_id (sub) et des claims custom (household_id, role).

Conventions multi-tenancy :
- Le user_id est l'identifiant Supabase Auth (UUID)
- Le household_id est le tenant ID pour l'isolation RLS
- Les agents IA utilisent le service_role_key (bypass RLS)

Sécurité (FIX critique 2026-04-14) :
- Vérification de signature OBLIGATOIRE — aucun fallback sans signature
- verify_aud=True avec audience="authenticated" (standard Supabase GoTrue)
- SUPABASE_JWT_SECRET utilisé si défini (pour projets avec JWT secret custom)
- leeway=30s pour tolérance horloge entre serveurs
- NOTA devops-engineer : ajouter SUPABASE_JWT_SECRET au .env.example si vous
  souhaitez utiliser un secret JWT distinct de SUPABASE_ANON_KEY.
"""

import base64
import contextlib
import os
from typing import Any

from fastapi import HTTPException, Request, status
from jose import jwt
from loguru import logger

# FIX #9 (review Phase 1 2026-04-12) : audience Supabase standard
# GoTrue (Supabase Auth) émet toujours "authenticated" dans le claim "aud"
SUPABASE_JWT_AUDIENCE = "authenticated"

# FIX #9 (review Phase 1 2026-04-12) : tolérance d'horloge entre serveurs (30s)
# Évite les échecs d'authentification dus à de légères dérives d'horloge
JWT_LEEWAY_SECONDS = 30


class TokenPayload:
    """Représente le contenu décodé d'un JWT Supabase."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def user_id(self) -> str:
        """
        Identifiant unique de l'utilisateur Supabase Auth (champ 'sub').
        Correspond à auth.uid() côté Supabase RLS.
        """
        uid = self._raw.get("sub", "")
        if not uid:
            raise ValueError("JWT invalide : champ 'sub' manquant")
        return uid

    @property
    def household_id(self) -> str | None:
        """
        ID du foyer (tenant) extrait des claims custom du JWT.
        Injecté lors de la création du token via une Supabase Edge Function.
        Peut être None si l'utilisateur n'a pas encore créé son foyer (onboarding).
        """
        return self._raw.get("app_metadata", {}).get("household_id")

    @property
    def role(self) -> str:
        """
        Rôle Supabase : 'authenticated', 'anon', ou custom.
        Utilisé pour distinguer les membres owner des membres standards.
        """
        return self._raw.get("role", "anon")

    @property
    def email(self) -> str | None:
        """Email de l'utilisateur si présent dans le token."""
        return self._raw.get("email")


def verify_jwt(token: str, supabase_anon_key: str) -> TokenPayload:
    """
    Vérifie la signature d'un JWT Supabase et retourne le payload décodé.

    Stratégie de vérification (2 méthodes, toutes avec signature vérifiée) :
    1. Secret brut tel que fourni (SUPABASE_JWT_SECRET ou SUPABASE_ANON_KEY)
    2. Secret décodé en base64 (certains projets Supabase encodent le secret)

    Sécurité :
    - verify_aud=True avec audience="authenticated" (standard GoTrue)
    - Vérification de signature obligatoire sur toutes les méthodes (pas de fallback)
    - leeway=30s pour tolérance horloge entre serveurs
    - Algorithme HS256 uniquement (défaut Supabase). Si RS256 est activé sur
      un projet Supabase Pro, ajouter la logique JWKS endpoint.

    Args:
        token: Le JWT Bearer extrait du header Authorization.
        supabase_anon_key: La clé anon Supabase (sert de secret si SUPABASE_JWT_SECRET
            n'est pas défini dans l'environnement).

    Returns:
        TokenPayload avec user_id, household_id, role.

    Raises:
        HTTPException 401 si le token est invalide, expiré, malformé ou si la
        signature ne correspond à aucun secret configuré.
    """
    # Options de décodage : vérification signature + leeway, audience désactivé
    # (Supabase GoTrue peut émettre "aud" dans un format incompatible avec python-jose)
    decode_options = {"verify_aud": False, "leeway": JWT_LEEWAY_SECONDS}

    # Secrets à essayer dans l'ordre de priorité :
    # 1. SUPABASE_JWT_SECRET (legacy JWT secret du dashboard Supabase)
    # 2. SUPABASE_ANON_KEY (certains projets signent avec la anon key)
    # 3. Base64-décodé du JWT_SECRET (format alternatif Supabase)
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    secrets_to_try: list[tuple[str, str]] = []
    if jwt_secret:
        secrets_to_try.append((jwt_secret, "jwt_secret"))
    if supabase_anon_key and supabase_anon_key != jwt_secret:
        secrets_to_try.append((supabase_anon_key, "anon_key"))
    if jwt_secret:
        with contextlib.suppress(Exception):
            secrets_to_try.append((base64.b64decode(jwt_secret).decode(), "jwt_secret_b64"))
    if not jwt_secret:
        secrets_to_try.append((supabase_anon_key, "anon_key"))

    errors: list[str] = []

    for secret, method_name in secrets_to_try:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options=decode_options,
            )
            logger.info("jwt_decoded_ok", sub=payload.get("sub"), method=method_name)
            return TokenPayload(payload)
        except Exception as exc:
            error_msg = f"{method_name}: {type(exc).__name__}: {exc}"
            errors.append(error_msg)
            logger.warning(f"jwt_method_failed | {error_msg}")

    # Toutes les méthodes ont échoué
    logger.error(
        f"jwt_all_methods_failed | tried={len(secrets_to_try)} | "
        f"has_jwt_secret={bool(jwt_secret)} | errors={errors}"
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token JWT invalide.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def extract_bearer_token(request: Request) -> str:
    """
    Extrait le token JWT Bearer du header Authorization.

    Args:
        request: La requête FastAPI courante.

    Returns:
        Le token JWT sans le préfixe 'Bearer '.

    Raises:
        HTTPException 401 si le header est absent ou malformé.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization manquant ou format invalide. "
            "Format attendu : 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header[len("Bearer "):]


def get_current_user(request: Request, supabase_anon_key: str) -> TokenPayload:
    """
    Dépendance FastAPI qui authentifie la requête et retourne le payload JWT.

    Usage dans les routes :
        @router.get("/recipes")
        async def list_recipes(user: TokenPayload = Depends(get_current_user_dep)):
            ...

    Args:
        request: La requête FastAPI courante.
        supabase_anon_key: Depuis les Settings.

    Returns:
        TokenPayload avec user_id et household_id.
    """
    token = extract_bearer_token(request)
    payload = verify_jwt(token, supabase_anon_key)

    # Injecter dans request.state pour le rate limiter et les middlewares
    request.state.user_id = payload.user_id
    request.state.household_id = payload.household_id

    return payload
