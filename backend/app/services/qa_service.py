"""The retrieval-augmented question answering pipeline."""

import logging
from typing import Iterator, List, Optional, Tuple

from app.core.errors import NoDocumentsIndexed
from app.retrieval import faiss_retriever
from app.services import llm_service
from app.services.context_builder import build_retrieved_context

logger = logging.getLogger(__name__)

NOT_FOUND = "Not found."

PROMPT_TEMPLATE = """
You are an Academic Copilot helping a student understand their study material.

Use the provided study material as your primary source.

You may:
- explain concepts in simpler language
- provide helpful examples
- compare related concepts
- explain step-by-step
- summarise the material
- rephrase difficult concepts for a beginner

Do not answer unrelated questions using outside knowledge.

If the answer cannot reasonably be found or explained from the provided
study material, respond with exactly:

Not found.

Format your answer in Markdown. Use headings, bullet lists and **bold** where
they make the explanation clearer.

Study Material:
{context}

Student Question:
{question}

Answer:
"""


def _prepare(question: str, doc_id: Optional[str]) -> Tuple[Optional[str], List[dict]]:
    """
    Retrieve context for a question.

    Returns (prompt, retrieved_chunks). A None prompt means nothing relevant was
    retrieved and the caller should short-circuit to a "not found" response.
    """
    if not faiss_retriever.has_documents():
        raise NoDocumentsIndexed()

    chunks = faiss_retriever.retrieve(question, doc_id=doc_id)
    if not chunks:
        return None, []

    prompt = PROMPT_TEMPLATE.format(
        context=build_retrieved_context(chunks), question=question
    )
    return prompt, chunks


def build_sources(chunks: List[dict]) -> List[dict]:
    """Deduplicate retrieved chunks down to distinct filename/page citations."""
    sources: List[dict] = []
    for chunk in chunks:
        source = {
            "filename": chunk["filename"],
            "page": chunk["page"],
            "doc_id": chunk.get("doc_id"),
        }
        if source not in sources:
            sources.append(source)
    return sources


def get_answer(question: str, doc_id: Optional[str] = None) -> dict:
    """Run the full pipeline and return {answer, sources}."""
    prompt, chunks = _prepare(question, doc_id)
    if prompt is None:
        return {"answer": NOT_FOUND, "sources": []}

    answer = llm_service.ask_llm(prompt).strip()

    if answer.lower().startswith("not found"):
        return {"answer": NOT_FOUND, "sources": []}

    return {"answer": answer, "sources": build_sources(chunks)}


def stream_answer(
    question: str, doc_id: Optional[str] = None
) -> Tuple[Iterator[str], List[dict]]:
    """
    Return (token_iterator, sources).

    Sources are resolved up front from retrieval, so the caller can show
    citations while the answer is still streaming in.
    """
    prompt, chunks = _prepare(question, doc_id)
    if prompt is None:
        return iter([NOT_FOUND]), []

    return llm_service.stream_llm(prompt), build_sources(chunks)
