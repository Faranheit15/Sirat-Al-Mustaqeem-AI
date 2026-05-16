import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import httpx
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings


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
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(settings.supabase_jwks_url)
        response.raise_for_status()
        jwks = cast(dict[str, Any], response.json())

    _jwks_cache = jwks
    _jwks_cache_expires_at = now + settings.jwks_cache_ttl_seconds
    return jwks


async def verify_supabase_jwt(token: str) -> AuthenticatedUser:
    settings = get_settings()

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid bearer token header.") from exc

    kid = header.get("kid")
    if not isinstance(kid, str):
        raise ValueError("Bearer token is missing a key id.")

    jwks = await get_supabase_jwks()
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise ValueError("Supabase JWKS response is malformed.")

    jwk = next((key for key in keys if isinstance(key, dict) and key.get("kid") == kid), None)
    if jwk is None:
        raise ValueError("Bearer token key id is not trusted.")

    token_algorithm = header.get("alg")
    if token_algorithm not in {"RS256", "ES256"}:
        raise ValueError("Bearer token algorithm is not supported.")

    try:
        public_key = cast(Any, jwt.PyJWK.from_json(json.dumps(jwk)).key)
    except jwt.PyJWTError as exc:
        raise ValueError("Bearer token key could not be parsed.") from exc

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.supabase_jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Bearer token could not be verified.") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Bearer token is missing a subject.")

    email = claims.get("email")
    return AuthenticatedUser(
        user_id=subject,
        email=email if isinstance(email, str) else None,
        claims=claims,
    )


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                request.state.user = await verify_supabase_jwt(token)
            except ValueError:
                request.state.user = None

        response = await call_next(request)
        return response
