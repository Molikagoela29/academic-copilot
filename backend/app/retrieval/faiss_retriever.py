import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import faiss
from app.embeddings import embedder

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Document registry: doc_id -> { "doc_id": str, "filename": str, "pages": int, "upload_time": str, "chunks": list[dict], "index": faiss.IndexFlatIP }
registry: Dict[str, Dict[str, Any]] = {}


def build_and_register_index(
    doc_id: str,
    filename: str,
    pages: int,
    chunks: List[dict],
) -> faiss.IndexFlatIP:
    """
    Build a cosine similarity FAISS index (IndexFlatIP with L2 normalized vectors)
    for the given chunks, and register it under doc_id.
    """
    # Ensure each chunk includes doc_id
    for chunk in chunks:
        chunk["doc_id"] = doc_id
        chunk["filename"] = filename

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode(texts, normalize=True)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    registry[doc_id] = {
        "doc_id": doc_id,
        "filename": filename,
        "pages": pages,
        "upload_time": datetime.utcnow().isoformat(),
        "chunks": chunks,
        "index": index,
    }

    save_document(doc_id)
    return index


def save_document(doc_id: str) -> None:
    """Persist index, chunks, and metadata for a document to disk."""
    if doc_id not in registry:
        return

    doc_data = registry[doc_id]
    doc_dir = STORAGE_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save FAISS index
    faiss.write_index(doc_data["index"], str(doc_dir / "index.faiss"))

    # 2. Save chunks
    with open(doc_dir / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(doc_data["chunks"], f, ensure_ascii=False, indent=2)

    # 3. Save metadata
    meta = {
        "doc_id": doc_data["doc_id"],
        "filename": doc_data["filename"],
        "pages": doc_data["pages"],
        "chunks_count": len(doc_data["chunks"]),
        "upload_time": doc_data["upload_time"],
    }
    with open(doc_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_all() -> int:
    """
    Scan storage directory and load all persisted indices and metadata into registry.
    Returns the number of documents loaded.
    """
    if not STORAGE_DIR.exists():
        return 0

    loaded_count = 0
    for doc_dir in STORAGE_DIR.iterdir():
        if not doc_dir.is_dir():
            continue

        index_file = doc_dir / "index.faiss"
        chunks_file = doc_dir / "chunks.json"
        meta_file = doc_dir / "meta.json"

        if index_file.exists() and chunks_file.exists() and meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)

                index = faiss.read_index(str(index_file))

                doc_id = meta["doc_id"]
                registry[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta["filename"],
                    "pages": meta.get("pages", 1),
                    "upload_time": meta.get("upload_time", datetime.utcnow().isoformat()),
                    "chunks": chunks,
                    "index": index,
                }
                loaded_count += 1
            except Exception as e:
                print(f"⚠️ Error loading document from {doc_dir}: {e}")

    print(f"📦 Loaded {loaded_count} document(s) from persistent storage.")
    return loaded_count


def delete_document(doc_id: str) -> bool:
    """Delete a document from in-memory registry and disk storage."""
    deleted = False
    if doc_id in registry:
        del registry[doc_id]
        deleted = True

    doc_dir = STORAGE_DIR / doc_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir, ignore_errors=True)
        deleted = True

    return deleted


def list_documents() -> List[Dict[str, Any]]:
    """List all loaded documents with metadata."""
    docs = []
    for doc_id, data in registry.items():
        docs.append({
            "doc_id": doc_id,
            "filename": data["filename"],
            "pages": data["pages"],
            "chunks_count": len(data["chunks"]),
            "upload_time": data["upload_time"],
        })
    return docs


def has_documents() -> bool:
    """Check if any documents are currently loaded."""
    return len(registry) > 0


def get_chunks(doc_id: Optional[str] = None) -> List[dict]:
    """
    Get all chunks for a specific doc_id, or for all documents if doc_id is None.
    """
    if doc_id:
        doc = registry.get(doc_id)
        return doc["chunks"] if doc else []

    all_chunks = []
    for doc in registry.values():
        all_chunks.extend(doc["chunks"])
    return all_chunks


def retrieve(
    question: str,
    doc_id: Optional[str] = None,
    k: int = 3,
    min_similarity: float = 0.35,
) -> List[dict]:
    """
    Retrieve the top-k most relevant chunks using cosine similarity.
    If doc_id is provided, searches only that document.
    If doc_id is None, searches across all indexed documents and re-ranks top results.
    """
    if not registry:
        return []

    target_docs = [registry[doc_id]] if doc_id and doc_id in registry else list(registry.values())
    if not target_docs:
        return []

    query_embedding = embedder.encode([question], normalize=True)

    candidates = []

    for doc in target_docs:
        index = doc["index"]
        chunks = doc["chunks"]
        
        # Search index
        num_search = min(k * 2, len(chunks))
        if num_search <= 0:
            continue

        similarities, indices = index.search(query_embedding, num_search)

        for sim, idx in zip(similarities[0], indices[0]):
            if 0 <= idx < len(chunks) and sim >= min_similarity:
                candidates.append((float(sim), chunks[idx]))

    # Sort all candidates across documents by cosine similarity descending
    candidates.sort(key=lambda item: item[0], reverse=True)

    # Return top k chunk dicts
    return [chunk for _, chunk in candidates[:k]]


# ─── Backward compatibility helpers ──────────────────────────────────────────

@property
def stored_chunks():
    return get_chunks()

@property
def stored_index():
    return [doc["index"] for doc in registry.values()]
