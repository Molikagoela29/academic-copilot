import logging

from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from app.db import repository
from app.models.schemas import UploadResponse
from app.services import ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """
    Accept a PDF and queue it for indexing.

    Returns immediately with status "processing"; poll `GET /documents` for the
    document to become "ready". Parsing and embedding a large PDF takes far
    longer than a request should block for.
    """
    file_path, doc_id, file_hash = await ingestion_service.save_upload(file)
    filename = file.filename or "document.pdf"

    existing = repository.get_document_by_hash(file_hash)
    if existing and existing["status"] != "failed":
        file_path.unlink(missing_ok=True)
        return UploadResponse(
            doc_id=existing["doc_id"],
            filename=existing["filename"],
            status=existing["status"],
            duplicate=True,
            message=f"'{existing['filename']}' is already in your library.",
        )

    if existing:
        # A previous attempt at this same file failed; clear it and retry.
        ingestion_service.remove_document(existing["doc_id"])

    repository.create_document(
        doc_id=doc_id,
        filename=filename,
        stored_filename=file_path.name,
        file_hash=file_hash,
    )

    background_tasks.add_task(ingestion_service.ingest, doc_id, file_path, filename)

    return UploadResponse(
        doc_id=doc_id,
        filename=filename,
        status="processing",
        message="Upload received. Indexing has started.",
    )

