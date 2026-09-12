import logging
import threading
from typing import Any, List, Optional

import faiss
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: Optional[Any] = None
_model_lock = threading.Lock()


def get_model() -> Any:
    """
    Load the sentence-transformer on first use rather than at import time.

    Importing sentence_transformers pulls in the whole torch stack and a
    first run downloads model weights; neither belongs in application startup
    or in a test run that never embeds anything.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model '%s'…", settings.embedding_model)
                _model = SentenceTransformer(settings.embedding_model)
                logger.info("Embedding model ready")
    return _model


def dimension() -> int:
    return get_model().get_sentence_embedding_dimension()


def encode(texts: List[str], normalize: bool = True) -> np.ndarray:
    """
    Encode strings into float32 embeddings.

    L2 normalisation makes inner product equivalent to cosine similarity, which
    is what the IndexFlatIP indexes in the retriever rely on.
    """
    if not texts:
        return np.empty((0, dimension()), dtype="float32")

    embeddings = get_model().encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")

    if normalize:
        faiss.normalize_L2(embeddings)

    return embeddings
