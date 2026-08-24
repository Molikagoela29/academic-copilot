import json
from app.agents.base_agent import BaseAgent
from app.retrieval import faiss_retriever
from app.services.qa_service import ask_llm
from app.utils.llm_parser import extract_json

MAX_CONTEXT_CHARS = 5000


def _build_context(max_chars: int = MAX_CONTEXT_CHARS) -> str:
    chunks = faiss_retriever.stored_chunks
    if not chunks:
        return ""

    total = len(chunks)
    step = max(1, total // 80)
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


class FlashcardAgent(BaseAgent):
    """
    Generates term/definition flashcard pairs from the uploaded document.
    """

    def run(self, num_cards: int = 10) -> dict:
        """
        Args:
            num_cards: How many flashcard pairs to generate.

        Returns:
            {flashcards: list[{term: str, definition: str}]}
        """
        if not faiss_retriever.stored_index:
            return {"flashcards": []}

        context = _build_context()

        prompt = f"""
You are an Academic Copilot creating revision flashcards from a student's study material.

Generate exactly {num_cards} flashcard pairs based on the study material below.

Rules:
- Each flashcard should have a concise TERM and a clear, complete DEFINITION.
- Terms can be: concepts, processes, principles, formulas, or important names.
- Definitions should be plain, student-friendly, and explain the term clearly in 1-3 sentences.
- Cover a wide variety of topics from across the material.

Respond ONLY with a valid JSON array. No extra text before or after. Format:
[
  {{
    "term": "...",
    "definition": "..."
  }}
]

Study Material:
{context}

JSON:
"""

        raw = ask_llm(prompt).strip()

        try:
            flashcards = extract_json(raw)
            if not isinstance(flashcards, list):
                flashcards = []
        except (ValueError, json.JSONDecodeError):
            flashcards = []

        return {"flashcards": flashcards}
