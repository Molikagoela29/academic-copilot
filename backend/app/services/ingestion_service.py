"""Upload handling and background PDF ingestion."""

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.errors import InvalidUpload
from app.db import repository
from app.parsers import pdf_parser
from app.retrieval import faiss_retriever

logger = logging.getLogger(__name__)

CHUNK_READ_SIZE = 1024 * 1024  # 1 MB
PDF_MAGIC = b"%PDF-"


def safe_stored_name(doc_id: str, filename: str) -> str:
    """
    Build the on-disk filename.

    `Path(...).name` strips any directory components, so a crafted filename such
    as `../../etc/passwd` cannot escape the upload directory.
    """
    base = Path(filename).name.strip() or "document.pdf"
    return f"{doc_id}_{base}"


async def save_upload(upload_file) -> tuple[Path, str, str]:
    """
    Stream an uploaded file to disk while enforcing the size limit and hashing
    it for duplicate detection.

    Returns (file_path, doc_id, file_hash).
    """
    raw_name = upload_file.filename or ""
    if not raw_name.lower().endswith(".pdf"):
        raise InvalidUpload("Only PDF files are supported.")

    settings.ensure_dirs()

    doc_id = str(uuid.uuid4())
    stored_name = safe_stored_name(doc_id, raw_name)
    file_path = settings.upload_dir / stored_name

    hasher = hashlib.sha256()
    total_bytes = 0
    first_block = True

    try:
        with open(file_path, "wb") as out_file:
            while True:
                block = await upload_file.read(CHUNK_READ_SIZE)
                if not block:
                    break

                if first_block:
                    if not block.startswith(PDF_MAGIC):
                        raise InvalidUpload(
                            "This file is not a valid PDF (bad file signature)."
                        )
                    first_block = False

                total_bytes += len(block)
                if total_bytes > settings.max_upload_bytes:
                    limit_mb = settings.max_upload_bytes // (1024 * 1024)
                    raise InvalidUpload(f"File is too large. The limit is {limit_mb} MB.")

                hasher.update(block)
                out_file.write(block)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    if total_bytes == 0:
        file_path.unlink(missing_ok=True)
        raise InvalidUpload("The uploaded file is empty.")

    return file_path, doc_id, hasher.hexdigest()


def ingest(doc_id: str, file_path: Path, filename: str) -> None:
    """
    Parse, chunk, embed and index a PDF. Runs in a background task, so every
    failure is recorded on the document row rather than raised to a caller.
    """
    try:
        logger.info("Ingesting %s (doc_id=%s)", filename, doc_id)
        chunks, total_pages = pdf_parser.parse(file_path, filename)
        chunk_count = faiss_retriever.build_and_register_index(
            doc_id=doc_id, filename=filename, chunks=chunks
        )
        repository.update_document(
            doc_id,
            pages=total_pages,
            chunks_count=chunk_count,
            status="ready",
            error=None,
        )
        logger.info(
            "Indexed %s chunks across %s pages for %s", chunk_count, total_pages, filename
        )
    except InvalidUpload as exc:
        logger.warning("Rejected %s: %s", filename, exc.message)
        _fail(doc_id, file_path, exc.message)
    except Exception as exc:  # noqa: BLE001 - background task must never escape
        logger.exception("Failed to ingest %s", filename)
        _fail(doc_id, file_path, f"Unexpected error while processing: {exc}")


def _fail(doc_id: str, file_path: Path, message: str) -> None:
    repository.update_document(doc_id, status="failed", error=message)
    file_path.unlink(missing_ok=True)


def remove_document(doc_id: str) -> bool:
    """Delete a document's database row, vector index and original PDF."""
    document = repository.get_document(doc_id)
    if not document:
        return False

    faiss_retriever.drop_document(doc_id)
    repository.delete_study_sets_for_document(doc_id)

    stored_filename = document.get("stored_filename")
    if stored_filename:
        (settings.upload_dir / stored_filename).unlink(missing_ok=True)

    repository.delete_document(doc_id)
    logger.info("Deleted document %s (%s)", doc_id, document.get("filename"))
    return True


def reconcile() -> None:
    """
    On startup, align the database with what is actually on disk.

    Documents left mid-ingestion by a crash are marked failed, and rows whose
    vector index has vanished are removed so the UI never offers a dead document.
    """
    indexed = set(faiss_retriever.indexed_ids())

    for document in repository.list_documents():
        doc_id = document["doc_id"]
        status = document["status"]

        if status == "ready" and doc_id not in indexed:
            logger.warning("Index missing for %s; removing stale row", doc_id)
            remove_document(doc_id)
        elif status == "processing":
            repository.update_document(
                doc_id,
                status="failed",
                error="Processing was interrupted by a server restart. Please re-upload.",
            )


def file_path_for(doc_id: str) -> Optional[Path]:
    """Absolute path to a document's original PDF, if it still exists."""
    document = repository.get_document(doc_id)
    if not document:
        return None
    path = settings.upload_dir / document["stored_filename"]
    return path if path.exists() else None
