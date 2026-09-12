from datetime import date, timedelta

import pytest

from app.services import scheduler

TODAY = date(2026, 1, 1)


def test_first_successful_review_schedules_one_day_out():
    state = scheduler.review("good", today=TODAY)
    assert state["repetitions"] == 1
    assert state["interval_days"] == 1
    assert state["due_date"] == (TODAY + timedelta(days=1)).isoformat()


def test_second_successful_review_jumps_to_six_days():
    state = scheduler.review("good", repetitions=1, interval_days=1, today=TODAY)
    assert state["repetitions"] == 2
    assert state["interval_days"] == 6


def test_third_review_multiplies_by_ease():
    state = scheduler.review(
        "good", repetitions=2, interval_days=6, ease=2.5, today=TODAY
    )
    assert state["interval_days"] == 15  # round(6 * 2.5)


def test_forgetting_resets_the_interval_but_keeps_ease_above_floor():
    state = scheduler.review(
        "again", repetitions=5, interval_days=40, ease=2.5, today=TODAY
    )
    assert state["repetitions"] == 0
    assert state["interval_days"] == 0
    assert state["due_date"] == TODAY.isoformat()
    assert state["ease"] >= scheduler.MIN_EASE


def test_easy_raises_ease_and_hard_lowers_it():
    easy = scheduler.review("easy", repetitions=1, interval_days=1, ease=2.5, today=TODAY)
    hard = scheduler.review("hard", repetitions=1, interval_days=1, ease=2.5, today=TODAY)
    assert easy["ease"] > 2.5
    assert hard["ease"] < 2.5


def test_ease_never_falls_below_the_floor():
    ease = 2.5
    for _ in range(20):
        ease = scheduler.review("again", ease=ease, today=TODAY)["ease"]
    assert ease == scheduler.MIN_EASE


def test_unknown_quality_is_rejected():
    with pytest.raises(ValueError):
        scheduler.review("brilliant", today=TODAY)


def test_is_due_compares_against_today():
    assert scheduler.is_due((TODAY - timedelta(days=1)).isoformat(), today=TODAY)
    assert scheduler.is_due(TODAY.isoformat(), today=TODAY)
    assert not scheduler.is_due((TODAY + timedelta(days=1)).isoformat(), today=TODAY)


def test_malformed_due_date_is_treated_as_due():
    assert scheduler.is_due("not-a-date", today=TODAY)
