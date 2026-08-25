from typing import Optional
from app.agents.base_agent import BaseAgent
from app.retrieval import faiss_retriever
from app.services.qa_service import ask_llm

MAX_CONTEXT_CHARS = 6000


def _build_context(doc_id: Optional[str] = None, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Sample chunks evenly from the selected document (or all documents) up to max_chars.
    """
    chunks = faiss_retriever.get_chunks(doc_id=doc_id)
    if not chunks:
        return ""

    total = len(chunks)
    step = max(1, total // 100)
    indices = list(range(0, total, step))

    collected = []
    char_count = 0

    for idx in indices:
        text = chunks[idx]["text"]
        if char_count + len(text) > max_chars:
            break
        collected.append(text)
        char_count += len(text)

    return "\n\n".join(collected)


class SummaryAgent(BaseAgent):
    """
    Summarizes the uploaded study material using all available chunks.
    """

    def run(self, doc_id: Optional[str] = None, **kwargs) -> dict:
        """
        Returns:
            {summary: str}
        """
        if not faiss_retriever.has_documents():
            return {"summary": "No document uploaded."}

        context = _build_context(doc_id=doc_id)

        if not context:
            return {"summary": "No readable content found for the selected document."}

        prompt = f"""
You are an Academic Copilot. A student has uploaded their study material and wants a clear, structured summary.

Write a comprehensive summary of the study material below. Your summary should:
- Cover all major topics and concepts
- Be organized with clear sections or paragraphs per topic
- Use plain, student-friendly language
- Highlight key definitions, principles, or formulas if present
- Be detailed enough that a student can use it for revision

Study Material:
{context}

Summary:
"""

        summary = ask_llm(prompt).strip()
        return {"summary": summary}
