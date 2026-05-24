import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import admin, chat, health
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.supabase import SupabaseClient

logger = get_logger(__name__)


async def _recover_and_run(
    document_id: str,
    job_id: str,
    file_path: str,
    file_type: str,
    settings: Settings,
) -> None:
    supabase = SupabaseClient(settings=settings)
    try:
        if settings.supabase_service_role_key is None:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
        key = settings.supabase_service_role_key.get_secret_value()
        bucket = settings.supabase_storage_bucket
        storage_url = f"{settings.supabase_storage_url}/object/{bucket}/{file_path}"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(
                storage_url,
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            resp.raise_for_status()
            file_bytes = resp.content
    except Exception as exc:
        logger.error(
            "startup_recovery_download_failed | document_id=%s job_id=%s error=%s",
            document_id,
            job_id,
            exc,
        )
        await supabase.update_ingestion_job(
            job_id,
            status="failed",
            progress=0,
            error_log=f"Startup recovery: download failed: {exc}",
            completed_at=datetime.now(UTC).isoformat(),
        )
        await supabase.update_document(document_id, {"status": "failed"})
        return

    await supabase.update_ingestion_job(job_id, status="pending", progress=0)
    await supabase.update_document(document_id, {"status": "pending"})

    pipeline = IngestionPipeline(supabase=supabase, settings=settings)
    await pipeline.run(
        document_id=document_id,
        job_id=job_id,
        file_bytes=file_bytes,
        file_type=file_type,
    )


async def _startup_recover_stuck_jobs(settings: Settings) -> None:
    supabase = SupabaseClient(settings=settings)
    try:
        stuck = await supabase.list_stuck_ingestion_jobs()
    except Exception as exc:
        logger.warning("startup_recovery_query_failed | error=%s", exc)
        return

    if not stuck:
        logger.info("startup_recovery | no stuck jobs found")
        return

    logger.info("startup_recovery | found=%d stuck job(s) — requeuing", len(stuck))
    for job in stuck:
        job_id: str = job["id"]
        document_id: str = job["document_id"]
        doc = await supabase.get_document(document_id)
        if doc is None or not doc.get("file_path"):
            logger.warning("startup_recovery_skip | job_id=%s reason=missing_file_path", job_id)
            await supabase.update_ingestion_job(
                job_id,
                status="failed",
                progress=0,
                error_log="Recovery: document or file_path missing",
                completed_at=datetime.now(UTC).isoformat(),
            )
            continue
        asyncio.create_task(
            _recover_and_run(
                document_id=document_id,
                job_id=job_id,
                file_path=str(doc["file_path"]),
                file_type=str(doc.get("file_type", "txt")),
                settings=settings,
            )
        )
        logger.info("startup_recovery_queued | document_id=%s job_id=%s", document_id, job_id)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    await _startup_recover_stuck_jobs(settings)
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
