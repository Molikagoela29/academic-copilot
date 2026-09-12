import json
import logging
from typing import Iterator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents import FlashcardAgent, QuizAgent, SummaryAgent
from app.core.errors import CopilotError, NoDocumentsIndexed
from app.db import repository
from app.models.schemas import (
    Flashcard,
    FlashcardRequest,
    FlashcardResponse,
    QuizGradeRequest,
    QuizGradeResponse,
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    SummaryRequest,
    SummaryResponse,
)
from app.retrieval import faiss_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

_summary_agent = SummaryAgent()
_quiz_agent = QuizAgent()
_flashcard_agent = FlashcardAgent()


def _scope_label(doc_id: Optional[str]) -> str:
    """Human-readable description of what a generated set was built from."""
    if doc_id is None:
        count = len(faiss_retriever.indexed_ids())
        return f"All documents ({count})"

    document = repository.get_document(doc_id)
    return document.get("filename", doc_id) if document else doc_id


def _require_documents() -> None:
    if not faiss_retriever.has_documents():
        raise NoDocumentsIndexed()


@router.post("/summarize", response_model=SummaryResponse)
def summarize(request: SummaryRequest) -> SummaryResponse:
    """Generate a structured Markdown summary of the selected document(s)."""
    _require_documents()
    summary = _summary_agent.run(doc_id=request.doc_id)["summary"]

    study_set_id = None
    if request.save:
        study_set_id = repository.create_study_set(
            kind="summary",
            doc_id=request.doc_id,
            scope_label=_scope_label(request.doc_id),
            payload={"summary": summary},
        )["id"]

    return SummaryResponse(summary=summary, study_set_id=study_set_id)


@router.post("/summarize/stream")
def summarize_stream(request: SummaryRequest) -> StreamingResponse:
    """Stream the summary as server-sent events so it renders progressively."""
    _require_documents()

    def event_stream() -> Iterator[str]:
        collected: list[str] = []
        try:
            for token in _summary_agent.stream(doc_id=request.doc_id):
                collected.append(token)
                yield _sse("token", {"text": token})

            summary = "".join(collected).strip()
            study_set_id = None
            if request.save and summary:
                study_set_id = repository.create_study_set(
                    kind="summary",
                    doc_id=request.doc_id,
                    scope_label=_scope_label(request.doc_id),
                    payload={"summary": summary},
                )["id"]

            yield _sse("done", {"summary": summary, "study_set_id": study_set_id})
        except CopilotError as exc:
            yield _sse("error", {"detail": exc.message})
        except Exception as exc:  # noqa: BLE001 - the stream must close cleanly
            logger.exception("Unexpected failure while streaming a summary")
            yield _sse("error", {"detail": f"Unexpected error: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/quiz", response_model=QuizResponse)
def generate_quiz(request: QuizRequest) -> QuizResponse:
    """Generate open-ended conceptual quiz questions from the document(s)."""
    _require_documents()
    questions = _quiz_agent.run(
        num_questions=request.num_questions, doc_id=request.doc_id
    )["questions"]

    study_set_id = None
    if request.save:
        study_set_id = repository.create_study_set(
            kind="quiz",
            doc_id=request.doc_id,
            scope_label=_scope_label(request.doc_id),
            payload=questions,
        )["id"]

    return QuizResponse(
        questions=[QuizQuestion(**question) for question in questions],
        study_set_id=study_set_id,
    )


@router.post("/quiz/grade", response_model=QuizGradeResponse)
def grade_quiz_answer(request: QuizGradeRequest) -> QuizGradeResponse:
    """Score a student's written answer against the model answer."""
    result = _quiz_agent.grade(
        question=request.question,
        expected_answer=request.expected_answer,
        student_answer=request.student_answer,
    )
    return QuizGradeResponse(**result)


@router.post("/flashcards", response_model=FlashcardResponse)
def generate_flashcards(request: FlashcardRequest) -> FlashcardResponse:
    """Generate term/definition flashcard pairs from the document(s)."""
    _require_documents()
    flashcards = _flashcard_agent.run(
        num_cards=request.num_cards, doc_id=request.doc_id
    )["flashcards"]

    study_set_id = None
    if request.save:
        study_set_id = repository.create_study_set(
            kind="flashcards",
            doc_id=request.doc_id,
            scope_label=_scope_label(request.doc_id),
            payload=flashcards,
        )["id"]

    return FlashcardResponse(
        flashcards=[Flashcard(**card) for card in flashcards],
        study_set_id=study_set_id,
    )


def _sse(event: str, data: Optional[dict] = None) -> str:
    return f"event: {event}\ndata: {json.dumps(data or {})}\n\n"
