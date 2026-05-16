from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.auth import AuthContextMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, chat, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Sirat Al Mustaqeem AI API", version="0.1.0", lifespan=lifespan)

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
        protected_paths=("/chat", "/conversations"),
    )
    app.add_middleware(AuthContextMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    return app


app = create_app()
