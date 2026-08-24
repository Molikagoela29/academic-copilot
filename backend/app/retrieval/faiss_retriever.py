import faiss
from app.embeddings import embedder

# In-memory store shared between upload and query
stored_chunks: list[dict] = []
stored_index: list[faiss.Index] = []


def build_index(chunks: list[dict]) -> faiss.Index:
    """
    Build a FAISS flat-L2 index from a list of chunk dicts.
    Each chunk must have a 'text' key.
    """
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode(texts)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index


def retrieve(question: str, k: int = 3, distance_threshold: float = 1.2) -> list[dict]:
    """
    Retrieve the top-k most relevant chunks for a question.
    Returns an empty list if no document is loaded or nothing is close enough.
    """
    if not stored_index:
        return []

    index = stored_index[0]

    query_embedding = embedder.encode([question])
    distances, indices = index.search(query_embedding, k)

    results = []
    for distance, idx in zip(distances[0], indices[0]):
        if 0 <= idx < len(stored_chunks) and distance <= distance_threshold:
            results.append(stored_chunks[idx])

    return results
