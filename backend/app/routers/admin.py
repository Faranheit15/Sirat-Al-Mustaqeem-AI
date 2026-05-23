from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser
from app.models.schemas import ApiEnvelope

router = APIRouter(prefix="/admin", tags=["admin"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


@router.get("/status", response_model=ApiEnvelope)
async def admin_status(_current_user: CurrentUser) -> ApiEnvelope:
    return ApiEnvelope(data={"status": "placeholder"}, error=None, message="Admin routes pending.")
