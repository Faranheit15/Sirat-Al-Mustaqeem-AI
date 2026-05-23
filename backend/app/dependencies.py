from typing import Annotated

from fastapi import Depends

from app.middleware.auth import AuthenticatedUser, UserContext, get_current_user
from app.services.supabase import SupabaseClient, get_supabase_client

SupabaseDependency = Annotated[SupabaseClient, Depends(get_supabase_client)]

__all__ = ["AuthenticatedUser", "SupabaseDependency", "UserContext", "get_current_user"]
