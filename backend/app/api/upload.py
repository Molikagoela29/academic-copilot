from fastapi import APIRouter, UploadFile, File
import aiofiles
from pathlib import Path
import uuid

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

router = APIRouter()

# 🔥 Load embedding model once
model = SentenceTransformer('all-MiniLM-L6-v2')


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    # -----------------------------
    # 1. Validate file type
    # -----------------------------
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported"}

    # -----------------------------
    # 2. Save file
    # -----------------------------
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / unique_filename

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # -----------------------------
    # 3. Extract text (LIMITED PAGES)
    # -----------------------------
    reader = PdfReader(str(file_path))
    extracted_text = ""

    max_pages = 20  # ✅ YOUR LIMIT ADDED HERE

    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break

        text = page.extract_text()
        if text:
            extracted_text += text

    if not extracted_text.strip():
        return {"error": "No readable text found in PDF"}

    # -----------------------------
    # 4. Chunking
    # -----------------------------
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30
    )

    chunks = text_splitter.split_text(extracted_text)

    if not chunks:
        return {"error": "Chunking failed"}

    # -----------------------------
    # 5. Embeddings
    # -----------------------------
    embeddings = model.encode(chunks)

    # -----------------------------
    # 6. FAISS Index
    # -----------------------------
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))

    # -----------------------------
    # 7. Store globally for query
    # -----------------------------
    from app.api.query import stored_chunks, stored_index

    stored_chunks.clear()
    stored_chunks.extend(chunks)

    stored_index.clear()
    stored_index.append(index)

    print(f"✅ Processed {len(chunks)} chunks from {file.filename}")

    return {
        "filename": file.filename,
        "chunks_created": len(chunks),
        "message": "File processed successfully 🚀"
    }