import json

import pytest


@pytest.fixture
def flashcard_set(client, indexed_doc, fake_llm):
    fake_llm.response = json.dumps(
        [
            {"term": "Photosynthesis", "definition": "Light to chemical energy."},
            {"term": "Mitochondria", "definition": "Site of cellular respiration."},
            {"term": "ATP", "definition": "The cell's energy currency."},
        ]
    )
    return client.post("/agents/flashcards", json={"num_cards": 3}).json()["study_set_id"]


def test_study_sets_can_be_listed_and_filtered_by_kind(client, indexed_doc, fake_llm):
    client.post("/agents/summarize", json={})
    fake_llm.response = json.dumps([{"term": "ATP", "definition": "Energy currency."}])
    client.post("/agents/flashcards", json={"num_cards": 1})

    assert len(client.get("/study-sets").json()["study_sets"]) == 2

    summaries = client.get("/study-sets?kind=summary").json()["study_sets"]
    assert len(summaries) == 1
    assert summaries[0]["kind"] == "summary"


def test_study_set_list_reports_item_counts(client, flashcard_set):
    entry = client.get("/study-sets?kind=flashcards").json()["study_sets"][0]
    assert entry["item_count"] == 3


def test_study_sets_can_be_deleted(client, flashcard_set):
    assert client.delete(f"/study-sets/{flashcard_set}").status_code == 204
    assert client.get(f"/study-sets/{flashcard_set}").status_code == 404


def test_all_cards_are_due_before_any_review(client, flashcard_set):
    body = client.get(f"/study-sets/{flashcard_set}/due").json()
    assert body["total_cards"] == 3
    assert len(body["due_cards"]) == 3
    assert body["due_cards"][0]["term"] == "Photosynthesis"


def test_reviewing_a_card_well_removes_it_from_todays_queue(client, flashcard_set):
    response = client.post(
        f"/study-sets/{flashcard_set}/review", json={"card_index": 0, "quality": "good"}
    )

    assert response.status_code == 200
    assert response.json()["next_review_in_days"] == 1

    due = client.get(f"/study-sets/{flashcard_set}/due").json()["due_cards"]
    assert [card["card_index"] for card in due] == [1, 2]


def test_forgetting_a_card_keeps_it_due_today(client, flashcard_set):
    client.post(
        f"/study-sets/{flashcard_set}/review", json={"card_index": 0, "quality": "again"}
    )
    due = client.get(f"/study-sets/{flashcard_set}/due").json()["due_cards"]
    assert 0 in [card["card_index"] for card in due]


def test_repeated_good_reviews_lengthen_the_interval(client, flashcard_set):
    intervals = []
    for _ in range(3):
        response = client.post(
            f"/study-sets/{flashcard_set}/review",
            json={"card_index": 0, "quality": "good"},
        )
        intervals.append(response.json()["next_review_in_days"])

    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


def test_review_state_persists_across_requests(client, flashcard_set):
    client.post(
        f"/study-sets/{flashcard_set}/review", json={"card_index": 1, "quality": "easy"}
    )
    state = client.post(
        f"/study-sets/{flashcard_set}/review", json={"card_index": 1, "quality": "good"}
    ).json()["state"]

    assert state["repetitions"] == 2
    assert state["ease"] > 2.5
    assert state["last_reviewed"] is not None


def test_invalid_review_quality_is_rejected(client, flashcard_set):
    response = client.post(
        f"/study-sets/{flashcard_set}/review",
        json={"card_index": 0, "quality": "brilliant"},
    )
    assert response.status_code == 422


def test_reviewing_a_card_outside_the_deck_returns_404(client, flashcard_set):
    response = client.post(
        f"/study-sets/{flashcard_set}/review", json={"card_index": 99, "quality": "good"}
    )
    assert response.status_code == 404


def test_review_endpoints_reject_non_flashcard_sets(client, indexed_doc, fake_llm):
    summary_id = client.post("/agents/summarize", json={}).json()["study_set_id"]

    assert client.get(f"/study-sets/{summary_id}/due").status_code == 400
    assert (
        client.post(
            f"/study-sets/{summary_id}/review", json={"card_index": 0, "quality": "good"}
        ).status_code
        == 400
    )
