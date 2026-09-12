from typing import Iterator, Optional

from app.agents.base_agent import BaseAgent
from app.core.errors import NoDocumentsIndexed
from app.services import llm_service
from app.services.context_builder import build_overview_context

MAX_CONTEXT_CHARS = 6000

PROMPT_TEMPLATE = """
You are an Academic Copilot. A student has uploaded their study material and wants a clear, structured summary.

Write a comprehensive summary of the study material below. Your summary should:
- Cover all major topics and concepts
- Be organised under clear Markdown headings, one per topic
- Use plain, student-friendly language
- Highlight key definitions, principles, or formulas in **bold**
- Be detailed enough that a student can revise from it alone

Format your answer in Markdown.

Study Material:
{context}

Summary:
"""


class SummaryAgent(BaseAgent):
    """Summarises the uploaded study material."""

    def _prompt(self, doc_id: Optional[str]) -> str:
        context = build_overview_context(doc_id=doc_id, max_chars=MAX_CONTEXT_CHARS)
        if not context:
            raise NoDocumentsIndexed(
                "No readable content was found for the selected document."
            )
        return PROMPT_TEMPLATE.format(context=context)

    def run(self, doc_id: Optional[str] = None, **kwargs) -> dict:
        """Returns {summary: str}."""
        return {"summary": llm_service.ask_llm(self._prompt(doc_id)).strip()}

    def stream(self, doc_id: Optional[str] = None) -> Iterator[str]:
        """Yield the summary token by token."""
        return llm_service.stream_llm(self._prompt(doc_id))
