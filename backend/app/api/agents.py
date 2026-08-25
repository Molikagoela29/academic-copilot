from fastapi import APIRouter

from app.models.schemas import (
    SummaryRequest,
    SummaryResponse,
    QuizRequest,
    QuizResponse,
    QuizQuestion,
    FlashcardRequest,
    FlashcardResponse,
    Flashcard,
)
from app.agents.summary_agent import SummaryAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.flashcard_agent import FlashcardAgent

router = APIRouter(prefix="/agents", tags=["agents"])

_summary_agent = SummaryAgent()
_quiz_agent = QuizAgent()
_flashcard_agent = FlashcardAgent()


@router.post("/summarize", response_model=SummaryResponse)
def summarize(request: SummaryRequest = SummaryRequest()):
    """Generate a structured summary of the uploaded document(s)."""
    result = _summary_agent.run(doc_id=request.doc_id)
    return SummaryResponse(summary=result["summary"])


@router.post("/quiz", response_model=QuizResponse)
def generate_quiz(request: QuizRequest):
    """Generate open-ended conceptual quiz questions from the uploaded document(s)."""
    result = _quiz_agent.run(num_questions=request.num_questions, doc_id=request.doc_id)

    questions = [
        QuizQuestion(
            question=q.get("question", ""),
            answer=q.get("answer", ""),
        )
        for q in result.get("questions", [])
        if q.get("question") and q.get("answer")
    ]

    return QuizResponse(questions=questions)


@router.post("/flashcards", response_model=FlashcardResponse)
def generate_flashcards(request: FlashcardRequest):
    """Generate term/definition flashcard pairs from the uploaded document(s)."""
    result = _flashcard_agent.run(num_cards=request.num_cards, doc_id=request.doc_id)

    flashcards = [
        Flashcard(
            term=f.get("term", ""),
            definition=f.get("definition", ""),
        )
        for f in result.get("flashcards", [])
        if f.get("term") and f.get("definition")
    ]

    return FlashcardResponse(flashcards=flashcards)
