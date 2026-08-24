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

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / unique_filename

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # 3. Parse and chunk
    chunks = pdf_parser.extract_chunks(file_path, file.filename)

    if not chunks:
        return {"error": "No readable text found in PDF"}

    # 4. Build FAISS index and store
    index = faiss_retriever.build_index(chunks)

    faiss_retriever.stored_chunks.clear()
    faiss_retriever.stored_chunks.extend(chunks)

    faiss_retriever.stored_index.clear()
    faiss_retriever.stored_index.append(index)

    total_pages = pdf_parser.page_count(file_path)

    print(f"✅ Processed {len(chunks)} chunks from {file.filename}")

    return UploadResponse(
        filename=file.filename,
        pages_processed=total_pages,
        chunks_created=len(chunks),
        message="File processed successfully 🚀",
    )