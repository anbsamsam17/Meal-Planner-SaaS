"""
Helpers de sécurité JWT pour l'authentification Supabase.

Supabase Auth (GoTrue) émet des JWT signés. L'algorithme dépend de la
configuration du projet Supabase :
- ES256 (ECDSA P-256) : projets récents — vérification via clé publique JWKS
- HS256 (HMAC-SHA256) : projets legacy — vérification via JWT secret symétrique

Ce module détecte automatiquement l'algorithme du token et utilise la bonne
stratégie de vérification.

Conventions multi-tenancy :
- Le user_id est l'identifiant Supabase Auth (UUID)
- Le household_id est le tenant ID pour l'isolation RLS
- Les agents IA utilisent le service_role_key (bypass RLS)
"""

import os
import time
from typing import Any

import httpx
from fastapi import HTTPException, Request, status
from jose import jwt
from loguru import logger

# Tolérance d'horloge entre serveurs (30s)
JWT_LEEWAY_SECONDS = 30

# Algorithmes autorisés — HMAC (symétrique) et ECDSA (asymétrique via JWKS)
ALLOWED_ALGORITHMS = {"HS256", "HS384", "HS512", "ES256", "ES384", "ES512"}

# Cache JWKS en mémoire (TTL 5 min) — évite un appel HTTP par requête
_jwks_cache: dict[str, Any] = {}
_JWKS_CACHE_TTL = 300


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


def _fetch_jwks(supabase_url: str) -> list[dict[str, Any]]:
    """Récupère les clés publiques JWKS depuis Supabase, avec cache TTL 5 min."""
    now = time.monotonic()
    cached = _jwks_cache.get(supabase_url)
    if cached and (now - cached["ts"]) < _JWKS_CACHE_TTL:
        return cached["keys"]

    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    logger.info(f"jwks_fetch | url={jwks_url}")
    resp = httpx.get(jwks_url, timeout=5)
    resp.raise_for_status()
    keys = resp.json().get("keys", [])
    _jwks_cache[supabase_url] = {"keys": keys, "ts": now}
    logger.info(f"jwks_cached | keys_count={len(keys)}")
    return keys


def _verify_es256(token: str, header: dict[str, Any], decode_options: dict) -> TokenPayload:
    """Vérifie un JWT signé ES256 via la clé publique JWKS de Supabase."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    if not supabase_url:
        logger.error("jwks_no_supabase_url | SUPABASE_URL non configuré")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Configuration serveur incomplète (SUPABASE_URL manquant).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    keys = _fetch_jwks(supabase_url)
    kid = header.get("kid")
    token_alg = header.get("alg", "ES256")

    # Trouver la clé publique correspondant au kid du token
    matching_key = None
    for key in keys:
        if key.get("kid") == kid:
            matching_key = key
            break

    if not matching_key:
        # kid inconnu — invalider le cache et réessayer (rotation de clé possible)
        _jwks_cache.pop(supabase_url, None)
        keys = _fetch_jwks(supabase_url)
        for key in keys:
            if key.get("kid") == kid:
                matching_key = key
                break

    if not matching_key:
        logger.error(f"jwks_kid_not_found | kid={kid} | available={[k.get('kid') for k in keys]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé publique introuvable pour ce token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = jwt.decode(
        token,
        matching_key,
        algorithms=[token_alg],
        options=decode_options,
    )
    logger.info("jwt_decoded_ok", sub=payload.get("sub"), method="jwks_es256")
    return TokenPayload(payload)


def verify_jwt(token: str, supabase_anon_key: str) -> TokenPayload:
    """
    Vérifie la signature d'un JWT Supabase et retourne le payload décodé.

    Détecte automatiquement l'algorithme du token :
    - ES256/ES384/ES512 (asymétrique) : vérifie via JWKS public key de Supabase
    - HS256/HS384/HS512 (symétrique) : vérifie via SUPABASE_JWT_SECRET ou anon key

    Args:
        token: Le JWT Bearer extrait du header Authorization.
        supabase_anon_key: La clé anon Supabase (fallback pour HS* uniquement).

    Returns:
        TokenPayload avec user_id, household_id, role.

    Raises:
        HTTPException 401 si le token est invalide, expiré, ou signature incorrecte.
    """
    decode_options = {"verify_aud": False, "leeway": JWT_LEEWAY_SECONDS}

    # Lire l'en-tête JWT pour détecter l'algorithme
    try:
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg", "HS256")
        logger.info(f"jwt_header | alg={token_alg} | kid={header.get('kid', 'none')}")
    except Exception as exc:
        logger.error(f"jwt_header_unreadable | {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT malformé.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if token_alg not in ALLOWED_ALGORITHMS:
        logger.error(f"jwt_unsupported_alg | alg={token_alg}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Algorithme JWT non supporté : {token_alg}.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ES256/ES384/ES512 → vérification asymétrique via JWKS
    if token_alg.startswith("ES"):
        return _verify_es256(token, header, decode_options)

    # HS256/HS384/HS512 → vérification symétrique via secret
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    secrets_to_try: list[tuple[str, str]] = []
    if jwt_secret:
        secrets_to_try.append((jwt_secret, "jwt_secret"))
    if supabase_anon_key and supabase_anon_key != jwt_secret:
        secrets_to_try.append((supabase_anon_key, "anon_key"))
    if not jwt_secret:
        secrets_to_try.append((supabase_anon_key, "anon_key"))

    errors: list[str] = []
    for secret, method_name in secrets_to_try:
        try:
            payload = jwt.decode(
                token, secret, algorithms=[token_alg], options=decode_options,
            )
            logger.info("jwt_decoded_ok", sub=payload.get("sub"), method=method_name)
            return TokenPayload(payload)
        except Exception as exc:
            error_msg = f"{method_name}: {type(exc).__name__}: {exc}"
            errors.append(error_msg)
            logger.warning(f"jwt_method_failed | {error_msg}")

    logger.error(f"jwt_all_methods_failed | alg={token_alg} | errors={errors}")
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
