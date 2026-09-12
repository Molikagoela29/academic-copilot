from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import DocumentNotFound
from app.db import repository
from app.models.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentMeta,
)
from app.services import ingestion_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    """List every document with its indexing status."""
    documents = [
        DocumentMeta(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            pages=doc["pages"],
            chunks_count=doc["chunks_count"],
            status=doc["status"],
            error=doc["error"],
            upload_time=doc["upload_time"],
        )
        for doc in repository.list_documents()
    ]
    return DocumentListResponse(documents=documents)


@router.get("/{doc_id}", response_model=DocumentMeta)
def get_document(doc_id: str) -> DocumentMeta:
    document = repository.get_document(doc_id)
    if not document:
        raise DocumentNotFound()
    return DocumentMeta(
        doc_id=document["doc_id"],
        filename=document["filename"],
        pages=document["pages"],
        chunks_count=document["chunks_count"],
        status=document["status"],
        error=document["error"],
        upload_time=document["upload_time"],
    )


@router.get("/{doc_id}/file")
def get_document_file(doc_id: str) -> FileResponse:
    """
    Serve the original PDF so the client can open a cited page directly.

    Rendered inline rather than as an attachment so the browser's built-in
    viewer can jump to `#page=N`.
    """
    document = repository.get_document(doc_id)
    if not document:
        raise DocumentNotFound()

    path = ingestion_service.file_path_for(doc_id)
    if path is None:
        raise DocumentNotFound("The original PDF for this document is no longer available.")

    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{document["filename"]}"'},
    )


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document(doc_id: str) -> DocumentDeleteResponse:
    """Delete a document, its vector index, its PDF and its saved study sets."""
    if not ingestion_service.remove_document(doc_id):
        raise DocumentNotFound()
    return DocumentDeleteResponse(
        success=True, message="Document deleted successfully."
    )
