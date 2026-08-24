from app.agents.base_agent import BaseAgent
from app.retrieval import faiss_retriever
from app.services.qa_service import ask_llm

# Max chars of context to send to the LLM (~6000 chars ≈ safe for Llama3 8K window)
MAX_CONTEXT_CHARS = 6000


def _build_context(max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Sample chunks evenly from the entire document up to max_chars.
    Even sampling ensures coverage across all pages rather than
    only the first N chunks.
    """
    chunks = faiss_retriever.stored_chunks
    if not chunks:
        return ""

    total = len(chunks)

    # Figure out how many chunks we can include before hitting the char limit
    collected = []
    char_count = 0

    # Walk evenly spaced indices
    step = max(1, total // 100)  # at most ~100 sample points
    indices = list(range(0, total, step))

    for idx in indices:
        text = chunks[idx]["text"]
        if char_count + len(text) > max_chars:
            break
        collected.append(text)
        char_count += len(text)

    return "\n\n".join(collected)


class SummaryAgent(BaseAgent):
    """
    Summarizes the entire uploaded document using all available chunks.
    """

    def run(self, **kwargs) -> dict:
        """
        Returns:
            {summary: str}
        """
        if not faiss_retriever.stored_index:
            return {"summary": "No document uploaded."}

        context = _build_context()

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
