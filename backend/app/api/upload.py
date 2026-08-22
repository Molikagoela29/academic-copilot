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

# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")


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
    # 3. Read PDF
    # -----------------------------
    reader = PdfReader(str(file_path))

    # -----------------------------
    # 4. Create text splitter
    # -----------------------------
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=30
    )

    # This will contain:
    # text + filename + page number
    chunks_with_metadata = []

    # -----------------------------
    # 5. Extract and chunk page-wise
    # -----------------------------
    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if not text or not text.strip():
            continue

        page_chunks = text_splitter.split_text(text)

        for chunk in page_chunks:
            chunks_with_metadata.append({
                "text": chunk,
                "filename": file.filename,
                "page": page_number
            })

    # -----------------------------
    # 6. Check extracted content
    # -----------------------------
    if not chunks_with_metadata:
        return {"error": "No readable text found in PDF"}

    # -----------------------------
    # 7. Get only text for embeddings
    # -----------------------------
    chunk_texts = [
        chunk["text"]
        for chunk in chunks_with_metadata
    ]

    # -----------------------------
    # 8. Create embeddings
    # -----------------------------
    embeddings = model.encode(chunk_texts)

    embeddings = np.array(
        embeddings
    ).astype("float32")

    # -----------------------------
    # 9. Create FAISS index
    # -----------------------------
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    # -----------------------------
    # 10. Store for query endpoint
    # -----------------------------
    from app.api.query import stored_chunks, stored_index

    stored_chunks.clear()
    stored_chunks.extend(chunks_with_metadata)

    stored_index.clear()
    stored_index.append(index)

    print(
        f"✅ Processed {len(chunks_with_metadata)} chunks "
        f"from {file.filename}"
    )

    # -----------------------------
    # 11. Response
    # -----------------------------
    return {
        "filename": file.filename,
        "pages_processed": len(reader.pages),
        "chunks_created": len(chunks_with_metadata),
        "message": "File processed successfully 🚀"
    }