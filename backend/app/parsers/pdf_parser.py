from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_chunks(file_path: Path, filename: str) -> list[dict]:
    """
    Read a PDF and return a list of text chunks with metadata.

    Each chunk is a dict with keys:
        - text     : the chunk content
        - filename : original PDF filename
        - page     : 1-based page number
    """
    reader = PdfReader(str(file_path))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30,
    )

    chunks_with_metadata = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        if not text or not text.strip():
            continue

        page_chunks = text_splitter.split_text(text)

        for chunk in page_chunks:
            chunks_with_metadata.append(
                {
                    "text": chunk,
                    "filename": filename,
                    "page": page_number,
                }
            )

    return chunks_with_metadata


def page_count(file_path: Path) -> int:
    """Return the total number of pages in a PDF."""
    reader = PdfReader(str(file_path))
    return len(reader.pages)
