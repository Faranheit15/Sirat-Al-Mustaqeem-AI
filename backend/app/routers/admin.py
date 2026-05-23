from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.core.logging import get_logger
from app.dependencies import SupabaseDependency, get_current_user
from app.middleware.auth import UserContext
from app.models.schemas import (
    ApiEnvelope,
    Document,
    DocumentDetailData,
    DocumentDetailResponse,
    DocumentListData,
    DocumentListResponse,
    DocumentUploadData,
    DocumentUploadResponse,
    IngestionJob,
    IngestionJobListData,
    IngestionJobListResponse,
    IngestionJobResponse,
)
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.supabase import SupabaseClient

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

CurrentUser = Annotated[UserContext, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

_ALLOWED_TYPES = {"pdf", "docx", "doc", "txt"}
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
}


def _require_admin(current_user: CurrentUser) -> UserContext:
    if current_user.role not in {"admin", "local_dev"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return current_user


AdminUser = Annotated[UserContext, Depends(_require_admin)]


async def _run_pipeline(
    document_id: str,
    job_id: str,
    file_bytes: bytes,
    file_type: str,
    settings: Settings,
) -> None:
    supabase = SupabaseClient(settings=settings)
    pipeline = IngestionPipeline(supabase=supabase, settings=settings)
    await pipeline.run(
        document_id=document_id,
        job_id=job_id,
        file_bytes=file_bytes,
        file_type=file_type,
    )


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    current_user: AdminUser,
    supabase: SupabaseDependency,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    file: UploadFile,
    title: str | None = Form(default=None),
) -> DocumentUploadResponse:
    logger.info("admin_upload | user_id=%s filename=%s", current_user.user_id, file.filename)

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {ext!r} not supported. Allowed: {sorted(_ALLOWED_TYPES)}.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 50 MB limit.",
        )
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    doc_title = title or filename
    storage_path = f"{current_user.user_id}/{filename}"

    await supabase.upload_file(
        path=storage_path,
        content=file_bytes,
        content_type=_CONTENT_TYPES.get(ext, "application/octet-stream"),
    )

    doc_row = await supabase.create_document(
        title=doc_title,
        file_type=ext,
        file_size=len(file_bytes),
        file_path=storage_path,
    )
    job_row = await supabase.create_ingestion_job(document_id=doc_row["id"])

    background_tasks.add_task(
        _run_pipeline,
        document_id=doc_row["id"],
        job_id=job_row["id"],
        file_bytes=file_bytes,
        file_type=ext,
        settings=settings,
    )

    logger.info("admin_upload_queued | document_id=%s job_id=%s", doc_row["id"], job_row["id"])
    return DocumentUploadResponse(
        data=DocumentUploadData(
            document=Document(**doc_row),
            job=IngestionJob(**job_row),
        ),
        message="File uploaded. Ingestion running in the background.",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: AdminUser,
    supabase: SupabaseDependency,
    limit: int = 20,
    offset: int = 0,
) -> DocumentListResponse:
    logger.info("admin_list_documents | user_id=%s", current_user.user_id)
    rows = await supabase.list_documents(limit=limit, offset=offset)
    total = await supabase.count_documents()
    return DocumentListResponse(
        data=DocumentListData(
            documents=[Document(**r) for r in rows],
            total=total,
        )
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    current_user: AdminUser,
    supabase: SupabaseDependency,
) -> DocumentDetailResponse:
    logger.info(
        "admin_get_document | user_id=%s document_id=%s",
        current_user.user_id,
        document_id,
    )
    row = await supabase.get_document(document_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentDetailResponse(data=DocumentDetailData(document=Document(**row)))


@router.delete("/documents/{document_id}", response_model=ApiEnvelope)
async def delete_document(
    document_id: str,
    current_user: AdminUser,
    supabase: SupabaseDependency,
) -> ApiEnvelope:
    logger.info(
        "admin_delete_document | user_id=%s document_id=%s",
        current_user.user_id,
        document_id,
    )
    row = await supabase.get_document(document_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if row.get("file_path"):
        try:
            await supabase.delete_file(str(row["file_path"]))
        except Exception as exc:
            logger.warning("storage_delete_failed | document_id=%s error=%s", document_id, exc)

    await supabase.delete_chunks(document_id)
    await supabase.delete_document(document_id)
    return ApiEnvelope(message="Document deleted.")


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_document(
    document_id: str,
    current_user: AdminUser,
    supabase: SupabaseDependency,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
) -> IngestionJobResponse:
    logger.info(
        "admin_reprocess | user_id=%s document_id=%s",
        current_user.user_id,
        document_id,
    )
    row = await supabase.get_document(document_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not row.get("file_path"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document has no stored file to reprocess.",
        )

    # Fetch raw file from storage
    bucket = settings.supabase_storage_bucket
    if settings.supabase_service_role_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage credentials not configured.",
        )
    import httpx as _httpx

    key = settings.supabase_service_role_key.get_secret_value()
    storage_url = f"{settings.supabase_storage_url}/object/{bucket}/{row['file_path']}"
    async with _httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            storage_url,
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        resp.raise_for_status()
        file_bytes = resp.content

    await supabase.delete_chunks(document_id)
    await supabase.update_document(document_id, {"status": "pending", "chunk_count": 0})
    job_row = await supabase.create_ingestion_job(document_id=document_id)

    background_tasks.add_task(
        _run_pipeline,
        document_id=document_id,
        job_id=job_row["id"],
        file_bytes=file_bytes,
        file_type=str(row.get("file_type", "txt")),
        settings=settings,
    )

    return IngestionJobResponse(
        data=IngestionJob(**job_row),
        message="Reprocessing started.",
    )


@router.get("/ingestion-jobs", response_model=IngestionJobListResponse)
async def list_ingestion_jobs(
    current_user: AdminUser,
    supabase: SupabaseDependency,
    limit: int = 20,
    offset: int = 0,
) -> IngestionJobListResponse:
    logger.info("admin_list_jobs | user_id=%s", current_user.user_id)
    rows = await supabase.list_ingestion_jobs(limit=limit, offset=offset)
    return IngestionJobListResponse(
        data=IngestionJobListData(
            jobs=[IngestionJob(**r) for r in rows],
            total=len(rows),
        )
    )


@router.get("/status", response_model=ApiEnvelope)
async def admin_status(current_user: AdminUser) -> ApiEnvelope:
    logger.info("admin_status | user_id=%s", current_user.user_id)
    return ApiEnvelope(
        data={"status": "ok", "role": current_user.role},
        message="Admin is operational.",
    )
