import json
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx
import jwt

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    claims: dict[str, Any]


_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at = 0.0


async def get_supabase_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_cache_expires_at
    settings = get_settings()
    now = time.monotonic()
    if _jwks_cache is not None and now < _jwks_cache_expires_at:
        logger.debug("jwks_cache_hit")
        return _jwks_cache

    logger.debug("jwks_cache_miss | fetching from %s", settings.supabase_jwks_url)
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.get(settings.supabase_jwks_url)
        response.raise_for_status()
        jwks = cast(dict[str, Any], response.json())

    _jwks_cache = jwks
    _jwks_cache_expires_at = now + settings.jwks_cache_ttl_seconds
    logger.debug("jwks_cache_refreshed | ttl=%ss", settings.jwks_cache_ttl_seconds)
    return jwks


async def verify_supabase_jwt(token: str) -> AuthenticatedUser:
    settings = get_settings()

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        logger.warning("jwt_invalid_header | error=%s", exc)
        raise ValueError("Invalid bearer token header.") from exc

    kid = header.get("kid")
    if not isinstance(kid, str):
        logger.warning("jwt_missing_kid")
        raise ValueError("Bearer token is missing a key id.")

    algorithm = header.get("alg")
    if algorithm not in {"RS256", "ES256"}:
        logger.warning("jwt_unsupported_alg | alg=%s", algorithm)
        raise ValueError("Bearer token algorithm is not supported.")

    jwks = await get_supabase_jwks()
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise ValueError("Supabase JWKS response is malformed.")

    jwk = next((key for key in keys if isinstance(key, dict) and key.get("kid") == kid), None)
    if jwk is None:
        logger.warning("jwt_untrusted_kid | kid=%s", kid)
        raise ValueError("Bearer token key id is not trusted.")

    try:
        public_key = cast(Any, jwt.PyJWK.from_json(json.dumps(jwk)).key)
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        logger.warning("jwt_verification_failed | error=%s", exc)
        raise ValueError("Bearer token could not be verified.") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        logger.warning("jwt_missing_subject")
        raise ValueError("Bearer token is missing a subject.")

    logger.info("jwt_authenticated | user_id=%s", subject)
    email = claims.get("email")
    return AuthenticatedUser(
        user_id=subject,
        email=email if isinstance(email, str) else None,
        claims=claims,
    )
