from typing import Any

from fastapi import APIRouter, Request

from app.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import DbHealthData, DbHealthResponse, HealthData, HealthResponse
from app.services.supabase import SupabaseClient

logger = get_logger(__name__)

router = APIRouter(tags=["health"])
SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "x-api-key", "apikey"}


def build_client_details(request: Request) -> dict[str, Any]:
    client = request.client
    headers = {
        key: "[redacted]" if key.lower() in SENSITIVE_HEADER_NAMES else value
        for key, value in request.headers.items()
    }

    return {
        "request": {
            "method": request.method,
            "url": str(request.url),
            "base_url": str(request.base_url),
            "path": request.url.path,
            "query": str(request.url.query),
            "query_params": dict(request.query_params),
            "scheme": request.url.scheme,
        },
        "connection": {
            "host": client.host if client else None,
            "port": client.port if client else None,
            "server": request.scope.get("server"),
            "http_version": request.scope.get("http_version"),
        },
        "headers": headers,
        "proxy": {
            "x_forwarded_for": request.headers.get("x-forwarded-for"),
            "x_forwarded_host": request.headers.get("x-forwarded-host"),
            "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
            "forwarded": request.headers.get("forwarded"),
        },
    }


@router.get("/health/db", response_model=DbHealthResponse)
async def db_health_check() -> DbHealthResponse:
    settings = get_settings()
    logger.debug("db_health_check")
    supabase = SupabaseClient(settings=settings)
    is_healthy, tables, error = await supabase.check_db()
    return DbHealthResponse(
        data=DbHealthData(
            status="ok" if is_healthy else "error",
            tables=tables,
            error=error,
        ),
        error=error,
        message="Database is reachable." if is_healthy else "Database check failed.",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    settings = get_settings()
    logger.debug("health_check | environment=%s", settings.environment)
    return HealthResponse(
        data=HealthData(
            status="ok",
            service="sirat-backend",
            version=settings.api_version,
            environment=settings.environment,
            auth_required=settings.should_require_auth,
            client=build_client_details(request),
        ),
        error=None,
        message="Backend is healthy.",
    )
