import numpy as np
from sentence_transformers import SentenceTransformer

# Load once, shared across upload and query
_model = SentenceTransformer("all-MiniLM-L6-v2")


def encode(texts: list[str]) -> np.ndarray:
    """Encode a list of strings into float32 embeddings."""
    embeddings = _model.encode(texts)
    return np.array(embeddings).astype("float32")
