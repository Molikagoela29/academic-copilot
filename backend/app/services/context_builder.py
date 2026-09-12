"""Builds the study-material context block that gets embedded into prompts."""

from typing import List, Optional

from app.retrieval import faiss_retriever

DEFAULT_MAX_CHARS = 6000


def build_overview_context(
    doc_id: Optional[str] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """
    Sample chunks evenly across the document so the model sees the whole
    document's shape rather than only its opening pages.

    Unlike a naive truncation this skips over-long chunks instead of stopping at
    the first one, so a single dense chunk cannot starve the rest of the sample.
    """
    chunks = faiss_retriever.get_chunks(doc_id=doc_id)
    if not chunks:
        return ""

    total = len(chunks)
    # Aim for ~80 evenly spaced samples across the document.
    step = max(1, total // 80)

    collected: List[str] = []
    char_count = 0

    for idx in range(0, total, step):
        text = chunks[idx]["text"]
        if char_count + len(text) > max_chars:
            if char_count >= max_chars * 0.9:
                break
            continue
        collected.append(text)
        char_count += len(text)

    return "\n\n".join(collected)


def build_retrieved_context(chunks: List[dict]) -> str:
    """Format retrieved chunks with page citations so the model can attribute."""
    blocks = []
    for chunk in chunks:
        header = f"[{chunk['filename']} — page {chunk['page']}]"
        blocks.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(blocks)
