import json
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.retrieval import faiss_retriever
from app.services.qa_service import ask_llm
from app.utils.llm_parser import extract_json

MAX_CONTEXT_CHARS = 5000


def _build_context(doc_id: Optional[str] = None, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    chunks = faiss_retriever.get_chunks(doc_id=doc_id)
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


class QuizAgent(BaseAgent):
    """
    Generates open-ended quiz questions from the uploaded document(s).
    Each question comes with a rich conceptual answer that explains
    the surrounding idea so the student truly understands.
    """

    def run(self, num_questions: int = 5, doc_id: Optional[str] = None) -> dict:
        """
        Args:
            num_questions: How many questions to generate.
            doc_id: Optional document ID to scope questions to.

        Returns:
            {questions: list[{question: str, answer: str}]}
        """
        if not faiss_retriever.has_documents():
            return {"questions": []}

        context = _build_context(doc_id=doc_id)
        if not context:
            return {"questions": []}

        prompt = f"""
You are an Academic Copilot creating a quiz to help a student deeply understand their study material.

Generate exactly {num_questions} open-ended quiz questions based on the study material below.

Rules:
- Each question should test understanding of a key concept, NOT just recall of a fact.
- The answer must be thorough and conceptual — explain the idea, why it matters, and any related context so the student truly understands it.
- Do NOT generate multiple-choice questions.
- Vary the questions across different topics covered in the material.

Respond ONLY with a valid JSON array. No extra text before or after. Format:
[
  {{
    "question": "...",
    "answer": "..."
  }}
]

Study Material:
{context}

JSON:
"""

        raw = ask_llm(prompt).strip()

        try:
            questions = extract_json(raw)
            if not isinstance(questions, list):
                questions = []
        except (ValueError, json.JSONDecodeError):
            questions = []

        return {"questions": questions}
