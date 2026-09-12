import logging
from pathlib import Path
from typing import Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings
from app.core.errors import InvalidUpload

logger = logging.getLogger(__name__)


def parse(file_path: Path, filename: str) -> Tuple[list[dict], int]:
    """
    Read a PDF once and return (chunks, page_count).

    Each chunk is a dict with `text`, `filename` and a 1-based `page`.
    Raises InvalidUpload for encrypted, corrupt, oversized or text-free PDFs.
    """
    try:
        reader = PdfReader(str(file_path))
    except PdfReadError as exc:
        raise InvalidUpload(f"This file is not a readable PDF: {exc}") from exc

    if reader.is_encrypted:
        # Many PDFs are encrypted with an empty owner password and decrypt fine.
        try:
            if reader.decrypt("") == 0:
                raise InvalidUpload(
                    "This PDF is password protected. Remove the password and try again."
                )
        except (NotImplementedError, PdfReadError) as exc:
            raise InvalidUpload(
                "This PDF uses an unsupported encryption scheme."
            ) from exc

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise InvalidUpload("This PDF has no pages.")
    if total_pages > settings.max_pages:
        raise InvalidUpload(
            f"This PDF has {total_pages} pages; the limit is {settings.max_pages}."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[dict] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
        except Exception as exc:  # noqa: BLE001 - a single bad page must not fail the upload
            logger.warning("Could not extract page %s of %s: %s", page_number, filename, exc)
            continue

        if not text or not text.strip():
            continue

        for chunk_text in splitter.split_text(text):
            chunks.append(
                {"text": chunk_text, "filename": filename, "page": page_number}
            )

    if not chunks:
        raise InvalidUpload(
            "No readable text was found in this PDF. Scanned documents need OCR "
            "before they can be indexed."
        )

    return chunks, total_pages
