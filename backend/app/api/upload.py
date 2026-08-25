import uuid
import aiofiles
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from app.parsers import pdf_parser
from app.retrieval import faiss_retriever
from app.models.schemas import UploadResponse

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):

    # 1. Validate file type
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported"}

    # 2. Save file
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    doc_id = str(uuid.uuid4())
    unique_filename = f"{doc_id}_{file.filename}"
    file_path = upload_dir / unique_filename

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # 3. Parse and chunk
    chunks = pdf_parser.extract_chunks(file_path, file.filename)

    if not chunks:
        return {"error": "No readable text found in PDF"}

    total_pages = pdf_parser.page_count(file_path)

    # 4. Build cosine FAISS index and register (persists automatically)
    faiss_retriever.build_and_register_index(
        doc_id=doc_id,
        filename=file.filename,
        pages=total_pages,
        chunks=chunks,
    )

    print(f"✅ Processed and persisted {len(chunks)} chunks for {file.filename} (doc_id={doc_id})")

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        pages_processed=total_pages,
        chunks_created=len(chunks),
        message="File processed and indexed successfully 🚀",
    )