from typing import Optional

from app.agents.base_agent import BaseAgent
from app.services import qa_service


class QAAgent(BaseAgent):
    """
    Question-answering agent. Delegates to qa_service, which runs the full
    retrieve → prompt → generate → cite pipeline.
    """

    def run(self, question: str, doc_id: Optional[str] = None) -> dict:
        """Returns {answer: str, sources: list[dict]}."""
        return qa_service.get_answer(question, doc_id=doc_id)
