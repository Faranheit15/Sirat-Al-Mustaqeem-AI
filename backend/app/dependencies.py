from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.logging import get_logger
from app.middleware.auth import AuthenticatedUser, verify_supabase_jwt
from app.services.supabase import SupabaseClient, get_supabase_client

logger = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_user(credentials: BearerCredentials) -> AuthenticatedUser:
    settings = get_settings()
    if credentials is None:
        if settings.local_auth_bypass_enabled:
            logger.info(
                "auth_bypassed | user_id=%s reason=local_dev",
                settings.local_dev_user_id,
            )
            return AuthenticatedUser(
                user_id=settings.local_dev_user_id,
                email=settings.local_dev_user_email,
                claims={
                    "sub": settings.local_dev_user_id,
                    "email": settings.local_dev_user_email,
                    "role": "local_dev",
                    "auth_bypassed": True,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        return await verify_supabase_jwt(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


SupabaseDependency = Annotated[SupabaseClient, Depends(get_supabase_client)]
