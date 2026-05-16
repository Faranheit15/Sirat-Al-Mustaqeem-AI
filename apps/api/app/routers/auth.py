from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser
from app.models.schemas import AuthCallbackRequest, AuthCallbackResponse
from app.services.supabase import SupabaseService, get_supabase_service

router = APIRouter(prefix="/auth", tags=["auth"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
SupabaseDependency = Annotated[SupabaseService, Depends(get_supabase_service)]


@router.post(
    "/callback",
    response_model=AuthCallbackResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def auth_callback(
    payload: AuthCallbackRequest,
    current_user: CurrentUser,
    supabase: SupabaseDependency,
) -> AuthCallbackResponse:
    await supabase.upsert_user_profile(
        user_id=current_user.user_id,
        email=payload.email or current_user.email,
        metadata=payload.metadata,
    )
    return AuthCallbackResponse(status="accepted", user_id=current_user.user_id)
