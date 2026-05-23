from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.logging import get_logger
from app.dependencies import get_current_user
from app.middleware.auth import AuthenticatedUser
from app.models.schemas import ApiEnvelope

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


@router.get("/status", response_model=ApiEnvelope)
async def admin_status(current_user: CurrentUser) -> ApiEnvelope:
    logger.info("admin_status | user_id=%s", current_user.user_id)
    return ApiEnvelope(data={"status": "placeholder"}, error=None, message="Admin routes pending.")
