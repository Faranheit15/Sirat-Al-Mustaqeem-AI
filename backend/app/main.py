from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import admin, chat, health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    # Initialise logging before anything else.
    setup_logging(log_level=settings.log_level, environment=settings.environment)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )

    # Middleware is evaluated in reverse registration order, so the request
    # logger is registered first and thus wraps CORS and rate limiting.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        protected_prefixes=("/chat",),
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(admin.router)

    logger.info(
        "app_started | service=%s version=%s environment=%s log_level=%s",
        settings.api_title,
        settings.api_version,
        settings.environment,
        settings.log_level,
    )

    return app


app = create_app()

