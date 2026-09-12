"""
In-memory FAISS index registry with durable on-disk persistence.

Each document owns a cosine-similarity index (IndexFlatIP over L2-normalised
vectors). Metadata lives in SQLite; the vectors and chunk text live on disk
under `data/storage/<doc_id>/`.
"""

import json
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss

from app.core.config import settings
from app.core.errors import DocumentNotFound
from app.embeddings import embedder

logger = logging.getLogger(__name__)

# doc_id -> {"doc_id", "filename", "chunks": list[dict], "index": faiss.Index}
_registry: Dict[str, Dict[str, Any]] = {}

# Guards _registry and the FAISS indexes it holds. FAISS indexes are not safe
# for concurrent mutation, and FastAPI runs sync endpoints in a threadpool.
_lock = threading.RLock()


def _doc_dir(doc_id: str) -> Path:
    return settings.storage_dir / doc_id


def _atomic_write(path: Path, write_fn) -> None:
    """Write via a temporary file + rename so a crash cannot corrupt the target."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    write_fn(tmp_path)
    os.replace(tmp_path, path)


# ─── Building & persistence ───────────────────────────────────────────────────

def build_and_register_index(
    doc_id: str,
    filename: str,
    chunks: List[dict],
) -> int:
    """Embed the chunks, build a cosine index, register it and persist to disk."""
    for chunk in chunks:
        chunk["doc_id"] = doc_id
        chunk["filename"] = filename

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode(texts, normalize=True)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    with _lock:
        _registry[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "chunks": chunks,
            "index": index,
        }
        _persist(doc_id)

    return len(chunks)


def _persist(doc_id: str) -> None:
    """Write the index and chunks for a document. Caller must hold the lock."""
    doc_data = _registry.get(doc_id)
    if doc_data is None:
        return

    doc_dir = _doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)

    _atomic_write(
        doc_dir / "index.faiss",
        lambda tmp: faiss.write_index(doc_data["index"], str(tmp)),
    )

    def _write_chunks(tmp: Path) -> None:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(doc_data["chunks"], handle, ensure_ascii=False)

    _atomic_write(doc_dir / "chunks.json", _write_chunks)


def load_all() -> int:
    """Restore every persisted index into memory. Returns the count loaded."""
    if not settings.storage_dir.exists():
        return 0

    loaded = 0
    with _lock:
        for doc_dir in sorted(settings.storage_dir.iterdir()):
            if not doc_dir.is_dir():
                continue

            index_file = doc_dir / "index.faiss"
            chunks_file = doc_dir / "chunks.json"
            if not (index_file.exists() and chunks_file.exists()):
                logger.warning("Removing incomplete document directory %s", doc_dir.name)
                shutil.rmtree(doc_dir, ignore_errors=True)
                continue

            try:
                with open(chunks_file, "r", encoding="utf-8") as handle:
                    chunks = json.load(handle)
                index = faiss.read_index(str(index_file))
            except Exception as exc:  # noqa: BLE001 - one bad doc must not block startup
                logger.error("Could not load document %s: %s", doc_dir.name, exc)
                continue

            doc_id = doc_dir.name
            _registry[doc_id] = {
                "doc_id": doc_id,
                "filename": chunks[0]["filename"] if chunks else doc_id,
                "chunks": chunks,
                "index": index,
            }
            loaded += 1

    logger.info("Loaded %s document index(es) from disk", loaded)
    return loaded


def drop_document(doc_id: str) -> bool:
    """Remove a document from memory and delete its on-disk index."""
    with _lock:
        existed = _registry.pop(doc_id, None) is not None

    doc_dir = _doc_dir(doc_id)
    if doc_dir.exists():
        shutil.rmtree(doc_dir, ignore_errors=True)
        existed = True

    return existed


# ─── Queries ──────────────────────────────────────────────────────────────────

def is_indexed(doc_id: str) -> bool:
    with _lock:
        return doc_id in _registry


def has_documents() -> bool:
    with _lock:
        return bool(_registry)


def indexed_ids() -> List[str]:
    with _lock:
        return list(_registry)


def chunk_count(doc_id: str) -> int:
    with _lock:
        doc = _registry.get(doc_id)
        return len(doc["chunks"]) if doc else 0


def get_chunks(doc_id: Optional[str] = None) -> List[dict]:
    """
    All chunks for one document, or for every document when doc_id is None.

    Raises DocumentNotFound if a specific doc_id was requested but is unknown,
    so a stale selection surfaces as a 404 instead of silently widening scope.
    """
    with _lock:
        if doc_id is not None:
            doc = _registry.get(doc_id)
            if doc is None:
                raise DocumentNotFound(f"Document '{doc_id}' is not indexed.")
            return list(doc["chunks"])

        all_chunks: List[dict] = []
        for doc in _registry.values():
            all_chunks.extend(doc["chunks"])
        return all_chunks


def retrieve(
    question: str,
    doc_id: Optional[str] = None,
    k: Optional[int] = None,
    min_similarity: Optional[float] = None,
) -> List[dict]:
    """
    Return the top-k most relevant chunks by cosine similarity.

    With a doc_id, only that document is searched; without one, results from
    every document are merged and re-ranked on a common similarity scale.
    """
    k = k or settings.retrieval_k
    threshold = settings.min_similarity if min_similarity is None else min_similarity

    with _lock:
        if doc_id is not None:
            if doc_id not in _registry:
                raise DocumentNotFound(f"Document '{doc_id}' is not indexed.")
            targets = [_registry[doc_id]]
        else:
            targets = list(_registry.values())

        if not targets:
            return []

        query_embedding = embedder.encode([question], normalize=True)

        candidates: List[tuple[float, dict]] = []
        for doc in targets:
            chunks = doc["chunks"]
            num_search = min(k * 2, len(chunks))
            if num_search <= 0:
                continue

            similarities, indices = doc["index"].search(query_embedding, num_search)
            for similarity, idx in zip(similarities[0], indices[0]):
                if 0 <= idx < len(chunks) and similarity >= threshold:
                    candidates.append((float(similarity), chunks[idx]))

    candidates.sort(key=lambda item: item[0], reverse=True)

    results = []
    for similarity, chunk in candidates[:k]:
        enriched = dict(chunk)
        enriched["score"] = round(similarity, 4)
        results.append(enriched)
    return results


def reset() -> None:
    """Clear the in-memory registry. Used by the test suite."""
    with _lock:
        _registry.clear()
