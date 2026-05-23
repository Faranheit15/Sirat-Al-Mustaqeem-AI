import json
import time
from dataclasses import dataclass
from typing import Annotated, Any, cast

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserContext:
    user_id: str
    email: str | None
    role: str
    claims: dict[str, Any]


AuthenticatedUser = UserContext

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at = 0.0
_role_cache: dict[str, tuple[str, float]] = {}


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


def _role_from_claims(claims: dict[str, Any]) -> str | None:
    for container_name in ("app_metadata", "user_metadata"):
        container = claims.get(container_name)
        if isinstance(container, dict):
            role = container.get("role")
            if isinstance(role, str) and role:
                return role

    role = claims.get("role")
    if isinstance(role, str) and role not in {"anon", "authenticated"}:
        return role
    return None


async def _fetch_profile_role(user_id: str) -> str | None:
    settings = get_settings()
    if settings.supabase_service_role_key is None or settings.supabase_url is None:
        return None

    now = time.monotonic()
    cached = _role_cache.get(user_id)
    if cached is not None and now < cached[1]:
        return cached[0]

    key = settings.supabase_service_role_key.get_secret_value()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        for column in ("user_id", "id"):
            response = await client.get(
                f"{settings.supabase_rest_url}/profiles",
                params={"select": "role", column: f"eq.{user_id}", "limit": "1"},
                headers=headers,
            )
            if response.status_code >= 400:
                logger.debug(
                    "profile_role_lookup_failed | user_id=%s column=%s status=%s",
                    user_id,
                    column,
                    response.status_code,
                )
                continue

            rows = response.json()
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                role = rows[0].get("role")
                if isinstance(role, str) and role:
                    _role_cache[user_id] = (role, now + 300)
                    return role

    return None


async def verify_supabase_jwt(token: str) -> UserContext:
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
    role = _role_from_claims(claims) or await _fetch_profile_role(subject) or "user"
    return UserContext(
        user_id=subject,
        email=email if isinstance(email, str) else None,
        role=role,
        claims=claims,
    )


async def get_current_user_from_authorization(
    authorization: str | None = Header(default=None),
) -> UserContext:
    settings = get_settings()
    if authorization is None:
        if settings.local_auth_bypass_enabled:
            logger.info(
                "auth_bypassed | user_id=%s reason=local_dev",
                settings.local_dev_user_id,
            )
            return UserContext(
                user_id=settings.local_dev_user_id,
                email=settings.local_dev_user_email,
                role="local_dev",
                claims={
                    "sub": settings.local_dev_user_id,
                    "email": settings.local_dev_user_email,
                    "role": "local_dev",
                    "auth_bypassed": True,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be a bearer token.",
        )

    try:
        return await verify_supabase_jwt(token.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_user(credentials: BearerCredentials) -> UserContext:
    authorization = None
    if credentials is not None:
        authorization = f"{credentials.scheme} {credentials.credentials}"
    return await get_current_user_from_authorization(authorization)
