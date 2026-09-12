"""
SM-2 spaced repetition scheduling.

Implements the classic SuperMemo-2 algorithm: a card's ease factor drifts with
recall quality, and the interval grows multiplicatively for cards recalled well
while resetting to a same-day review for cards that were forgotten.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

# Quality ratings the UI exposes, mapped to the SM-2 0-5 scale.
QUALITY_MAP: Dict[str, int] = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
}

MIN_EASE = 1.3


def review(
    quality: str,
    repetitions: int = 0,
    interval_days: int = 0,
    ease: float = 2.5,
    today: Optional[date] = None,
) -> dict:
    """
    Apply one review to a card's scheduling state.

    Returns the new {repetitions, interval_days, ease, due_date}.
    """
    if quality not in QUALITY_MAP:
        raise ValueError(f"Unknown review quality '{quality}'")

    score = QUALITY_MAP[quality]
    today = today or datetime.now(timezone.utc).date()

    if score < 3:
        # Forgotten: restart the interval, but keep the accumulated ease.
        new_repetitions = 0
        new_interval = 0
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = max(1, round(interval_days * ease))

    # Standard SM-2 ease adjustment, floored so cards never spiral to daily.
    new_ease = ease + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
    new_ease = max(MIN_EASE, round(new_ease, 4))

    return {
        "repetitions": new_repetitions,
        "interval_days": new_interval,
        "ease": new_ease,
        "due_date": (today + timedelta(days=new_interval)).isoformat(),
    }


def is_due(due_date: str, today: Optional[date] = None) -> bool:
    today = today or datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(due_date) <= today
    except (TypeError, ValueError):
        return True


def new_card_state(today: Optional[date] = None) -> dict:
    """Scheduling state for a card that has never been reviewed."""
    today = today or datetime.now(timezone.utc).date()
    return {
        "repetitions": 0,
        "interval_days": 0,
        "ease": 2.5,
        "due_date": today.isoformat(),
    }
