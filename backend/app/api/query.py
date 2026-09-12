import json
import logging
from typing import Iterator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.errors import CopilotError
from app.db import repository
from app.models.schemas import QueryRequest, QueryResponse
from app.services import qa_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])

TITLE_MAX_CHARS = 60


def _ensure_conversation(request: QueryRequest) -> int:
    """Return the conversation to append to, creating one on first message."""
    if request.conversation_id and repository.get_conversation(request.conversation_id):
        return request.conversation_id

    title = request.question[:TITLE_MAX_CHARS]
    if len(request.question) > TITLE_MAX_CHARS:
        title += "…"
    return repository.create_conversation(title=title, doc_id=request.doc_id)["id"]


@router.post("/query", response_model=QueryResponse)
def query_ai(request: QueryRequest) -> QueryResponse:
    """Answer a question against the indexed material and persist the exchange."""
    conversation_id = _ensure_conversation(request)
    repository.add_message(conversation_id, "user", request.question)

    result = qa_service.get_answer(request.question, doc_id=request.doc_id)

    repository.add_message(
        conversation_id, "assistant", result["answer"], result["sources"]
    )

    return QueryResponse(
        question=request.question,
        answer=result["answer"],
        sources=result["sources"],
        conversation_id=conversation_id,
    )


@router.post("/query/stream")
def query_ai_stream(request: QueryRequest) -> StreamingResponse:
    """
    Stream an answer as server-sent events.

    Event sequence:
      `meta`  once, with the conversation id and resolved sources
      `token` repeatedly, with each generated fragment
      `done`  once, when the answer is complete and persisted
      `error` if generation failed part-way through
    """
    conversation_id = _ensure_conversation(request)
    repository.add_message(conversation_id, "user", request.question)

    def event_stream() -> Iterator[str]:
        collected: list[str] = []
        sources: list[dict] = []
        try:
            tokens, sources = qa_service.stream_answer(
                request.question, doc_id=request.doc_id
            )
            yield _sse("meta", {"conversation_id": conversation_id, "sources": sources})

            for token in tokens:
                collected.append(token)
                yield _sse("token", {"text": token})

            answer = "".join(collected).strip()
            if answer.lower().startswith("not found"):
                answer, sources = qa_service.NOT_FOUND, []

            repository.add_message(conversation_id, "assistant", answer, sources)
            yield _sse("done", {"answer": answer, "sources": sources})

        except CopilotError as exc:
            logger.warning("Streaming query failed: %s", exc.message)
            yield _sse("error", {"detail": exc.message})
        except Exception as exc:  # noqa: BLE001 - the stream must close cleanly
            logger.exception("Unexpected failure while streaming an answer")
            yield _sse("error", {"detail": f"Unexpected error: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: Optional[dict] = None) -> str:
    return f"event: {event}\ndata: {json.dumps(data or {})}\n\n"
