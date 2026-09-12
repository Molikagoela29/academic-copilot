from typing import Optional

from fastapi import APIRouter, Query

from app.core.errors import CopilotError
from app.db import repository
from app.models.schemas import (
    CardState,
    DueCard,
    DueCardsResponse,
    ReviewRequest,
    ReviewResponse,
    StudySetDetail,
    StudySetListResponse,
    StudySetMeta,
)
from app.services import scheduler

router = APIRouter(prefix="/study-sets", tags=["study sets"])


class StudySetNotFound(CopilotError):
    status_code = 404
    default_message = "Study set not found."


class NotAFlashcardSet(CopilotError):
    status_code = 400
    default_message = "This study set does not contain flashcards."


def _item_count(study_set: dict) -> int:
    payload = study_set.get("payload")
    if isinstance(payload, list):
        return len(payload)
    return 1 if payload else 0


def _load(study_set_id: int) -> dict:
    study_set = repository.get_study_set(study_set_id)
    if not study_set:
        raise StudySetNotFound()
    return study_set


@router.get("", response_model=StudySetListResponse)
def list_study_sets(
    kind: Optional[str] = Query(default=None, pattern="^(summary|quiz|flashcards)$"),
    doc_id: Optional[str] = None,
) -> StudySetListResponse:
    """Every saved summary, quiz and flashcard deck, newest first."""
    study_sets = [
        StudySetMeta(
            id=study_set["id"],
            kind=study_set["kind"],
            doc_id=study_set["doc_id"],
            scope_label=study_set["scope_label"],
            item_count=_item_count(study_set),
            created_at=study_set["created_at"],
        )
        for study_set in repository.list_study_sets(kind=kind, doc_id=doc_id)
    ]
    return StudySetListResponse(study_sets=study_sets)


@router.get("/{study_set_id}", response_model=StudySetDetail)
def get_study_set(study_set_id: int) -> StudySetDetail:
    study_set = _load(study_set_id)
    return StudySetDetail(
        id=study_set["id"],
        kind=study_set["kind"],
        doc_id=study_set["doc_id"],
        scope_label=study_set["scope_label"],
        payload=study_set["payload"],
        created_at=study_set["created_at"],
    )


@router.delete("/{study_set_id}", status_code=204)
def delete_study_set(study_set_id: int) -> None:
    if not repository.delete_study_set(study_set_id):
        raise StudySetNotFound()


# ─── Spaced repetition ────────────────────────────────────────────────────────

def _card_state(study_set_id: int, card_index: int) -> CardState:
    stored = repository.get_card_review(study_set_id, card_index)
    if not stored:
        fresh = scheduler.new_card_state()
        return CardState(card_index=card_index, **fresh, last_reviewed=None, due_now=True)

    return CardState(
        card_index=card_index,
        repetitions=stored["repetitions"],
        interval_days=stored["interval_days"],
        ease=stored["ease"],
        due_date=stored["due_date"],
        last_reviewed=stored["last_reviewed"],
        due_now=scheduler.is_due(stored["due_date"]),
    )


@router.get("/{study_set_id}/due", response_model=DueCardsResponse)
def get_due_cards(study_set_id: int) -> DueCardsResponse:
    """
    The cards from a deck that are scheduled for review today.

    Cards never reviewed before are due immediately.
    """
    study_set = _load(study_set_id)
    if study_set["kind"] != "flashcards":
        raise NotAFlashcardSet()

    cards = study_set["payload"] or []
    due_cards = []
    for index, card in enumerate(cards):
        state = _card_state(study_set_id, index)
        if state.due_now:
            due_cards.append(
                DueCard(
                    card_index=index,
                    term=card["term"],
                    definition=card["definition"],
                    state=state,
                )
            )

    return DueCardsResponse(
        study_set_id=study_set_id,
        scope_label=study_set["scope_label"],
        total_cards=len(cards),
        due_cards=due_cards,
    )


@router.post("/{study_set_id}/review", response_model=ReviewResponse)
def review_card(study_set_id: int, request: ReviewRequest) -> ReviewResponse:
    """Record a review outcome and reschedule the card with SM-2."""
    study_set = _load(study_set_id)
    if study_set["kind"] != "flashcards":
        raise NotAFlashcardSet()

    cards = study_set["payload"] or []
    if request.card_index >= len(cards):
        raise StudySetNotFound(f"Card {request.card_index} is not in this deck.")

    stored = repository.get_card_review(study_set_id, request.card_index)
    current = stored or scheduler.new_card_state()

    updated = scheduler.review(
        quality=request.quality,
        repetitions=current["repetitions"],
        interval_days=current["interval_days"],
        ease=current["ease"],
    )

    repository.upsert_card_review(
        study_set_id=study_set_id,
        card_index=request.card_index,
        **updated,
    )

    return ReviewResponse(
        state=_card_state(study_set_id, request.card_index),
        next_review_in_days=updated["interval_days"],
    )
