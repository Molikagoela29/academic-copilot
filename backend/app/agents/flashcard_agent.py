from typing import Optional

from app.agents.base_agent import BaseAgent
from app.core.errors import LLMBadOutput, NoDocumentsIndexed
from app.services import llm_service
from app.services.context_builder import build_overview_context

MAX_CONTEXT_CHARS = 5000

PROMPT_TEMPLATE = """
You are an Academic Copilot creating revision flashcards from a student's study material.

Generate exactly {num_cards} flashcard pairs based on the study material below.

Rules:
- Each flashcard has a concise TERM and a clear, complete DEFINITION.
- Terms can be concepts, processes, principles, formulas, or important names.
- Definitions should be plain, student-friendly, and explain the term in 1-3 sentences.
- Cover a wide variety of topics from across the material.
- Do not repeat the same term twice.

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


class FlashcardAgent(BaseAgent):
    """Generates term/definition flashcard pairs from the uploaded document(s)."""

    def run(self, num_cards: int = 10, doc_id: Optional[str] = None) -> dict:
        """Returns {flashcards: list[{term, definition}]}."""
        context = build_overview_context(doc_id=doc_id, max_chars=MAX_CONTEXT_CHARS)
        if not context:
            raise NoDocumentsIndexed(
                "No readable content was found for the selected document."
            )

        prompt = PROMPT_TEMPLATE.format(num_cards=num_cards, context=context)
        parsed = llm_service.ask_llm_json(prompt)

        if not isinstance(parsed, list):
            raise LLMBadOutput("The model did not return a list of flashcards.")

        flashcards = []
        seen_terms = set()
        for item in parsed:
            if not isinstance(item, dict):
                continue
            term = item.get("term")
            definition = item.get("definition")
            if not isinstance(term, str) or not isinstance(definition, str):
                continue
            term, definition = term.strip(), definition.strip()
            if not term or not definition or term.lower() in seen_terms:
                continue
            seen_terms.add(term.lower())
            flashcards.append({"term": term, "definition": definition})

        if not flashcards:
            raise LLMBadOutput(
                "The model did not produce any usable flashcards. Please try again."
            )

        return {"flashcards": flashcards}
