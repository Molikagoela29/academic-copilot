import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BATCH_SIZE = 64

# Load once, shared across upload and query
_model = SentenceTransformer("all-MiniLM-L6-v2")


def encode(
    texts: list[str],
    batch_size: int = BATCH_SIZE,
    normalize: bool = True,
) -> np.ndarray:
    """
    Encode a list of strings into float32 embeddings with batching and optional L2 normalization.
    
    L2 normalization ensures inner product (IP) is equivalent to cosine similarity.
    """
    if not texts:
        return np.empty((0, _model.get_sentence_embedding_dimension()), dtype="float32")

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = _model.encode(batch, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)

    embeddings = np.vstack(all_embeddings).astype("float32")

    if normalize:
        faiss.normalize_L2(embeddings)

    return embeddings
