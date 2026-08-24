from app.agents.base_agent import BaseAgent
from app.services import qa_service


class QAAgent(BaseAgent):
    """
    Question-answering agent.
    Delegates to qa_service which runs the full RAG pipeline.
    """

    def run(self, question: str) -> dict:
        """
        Args:
            question: The student's question.

        Returns:
            {answer: str, sources: list[dict]}
        """
        return qa_service.get_answer(question)
